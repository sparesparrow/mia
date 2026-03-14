"""
Session management for multi-client scenarios (Android, Quest, web).
In-memory session store following the same pattern as DeviceRegistry.
"""
import hashlib
import hmac
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ClientSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    client_type: str  # "android" | "quest" | "web"
    client_name: str
    created_at: datetime = Field(default_factory=datetime.now)
    last_active: datetime = Field(default_factory=datetime.now)
    device_subscriptions: List[str] = []
    handoff_token: Optional[str] = None
    handoff_expires: Optional[datetime] = None
    metadata: Dict = {}


class CreateSessionRequest(BaseModel):
    client_type: str
    client_name: str
    metadata: Dict = {}


class UpdateSessionRequest(BaseModel):
    device_subscriptions: Optional[List[str]] = None
    metadata: Optional[Dict] = None


class ResumeSessionRequest(BaseModel):
    handoff_token: str


class SessionManager:
    HANDOFF_TTL = timedelta(minutes=5)

    def __init__(self):
        self._sessions: Dict[str, ClientSession] = {}
        self._secret = os.environ.get("MIA_SESSION_SECRET", uuid4().hex)

    def create(self, req: CreateSessionRequest) -> ClientSession:
        session = ClientSession(
            client_type=req.client_type,
            client_name=req.client_name,
            metadata=req.metadata,
        )
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Optional[ClientSession]:
        session = self._sessions.get(session_id)
        if session:
            session.last_active = datetime.now()
        return session

    def update(self, session_id: str, req: UpdateSessionRequest) -> Optional[ClientSession]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        session.last_active = datetime.now()
        if req.device_subscriptions is not None:
            session.device_subscriptions = req.device_subscriptions
        if req.metadata is not None:
            session.metadata.update(req.metadata)
        return session

    def delete(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None

    def generate_handoff(self, session_id: str) -> Optional[str]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        payload = f"{session_id}:{time.time()}"
        token = hmac.new(
            self._secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()[:32]
        session.handoff_token = token
        session.handoff_expires = datetime.now() + self.HANDOFF_TTL
        return token

    def resume_with_token(self, token: str) -> Optional[ClientSession]:
        for session in self._sessions.values():
            if (
                session.handoff_token == token
                and session.handoff_expires
                and datetime.now() < session.handoff_expires
            ):
                session.handoff_token = None
                session.handoff_expires = None
                session.last_active = datetime.now()
                return session
        return None
