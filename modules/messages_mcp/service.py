import os
import asyncio
import smtplib
import imaplib
import email
from email.message import EmailMessage
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

try:
    from twilio.rest import Client as TwilioClient  # type: ignore
except Exception:  # pragma: no cover
    TwilioClient = None  # Fallback if twilio is not installed


@dataclass
class MessageRecord:
    message_id: str
    channel: str  # "sms" | "mms" | "email"
    to: str
    subject: Optional[str] = None
    body: str = ""
    media_urls: List[str] = field(default_factory=list)
    status: str = "queued"  # queued | sending | sent | failed
    provider_id: Optional[str] = None
    error: Optional[str] = None


class MessagingService:
    def __init__(self) -> None:
        # Twilio configuration
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.twilio_from = os.getenv("TWILIO_FROM", "")

        # SMTP configuration
        self.smtp_host = os.getenv("SMTP_HOST", "localhost")
        self.smtp_port = int(os.getenv("SMTP_PORT", "25"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

        # IMAP configuration
        self.imap_host = os.getenv("IMAP_HOST", "localhost")
        self.imap_port = int(os.getenv("IMAP_PORT", "993"))
        self.imap_user = os.getenv("IMAP_USER", "")
        self.imap_password = os.getenv("IMAP_PASSWORD", "")
        self.imap_use_ssl = os.getenv("IMAP_USE_SSL", "true").lower() == "true"

        self._twilio_client = None
        if self.twilio_sid and self.twilio_token and TwilioClient:
            self._twilio_client = TwilioClient(self.twilio_sid, self.twilio_token)

    async def send_sms(self, to: str, body: str) -> Dict[str, Any]:
        if self._twilio_client and self.twilio_from:
            try:
                msg = self._twilio_client.messages.create(
                    to=to, from_=self.twilio_from, body=body
                )
                return {"status": "sent", "provider_id": msg.sid}
            except Exception as e:  # pragma: no cover
                return {"status": "failed", "error": str(e)}
        # Stub fallback
        return {"status": "sent", "provider_id": "stub-sms-123"}

    async def send_mms(self, to: str, body: str, media_urls: Optional[List[str]] = None) -> Dict[str, Any]:
        media_urls = media_urls or []
        if self._twilio_client and self.twilio_from:
            try:
                msg = self._twilio_client.messages.create(
                    to=to, from_=self.twilio_from, body=body, media_url=media_urls
                )
                return {"status": "sent", "provider_id": msg.sid}
            except Exception as e:  # pragma: no cover
                return {"status": "failed", "error": str(e)}
        # Stub fallback
        return {"status": "sent", "provider_id": "stub-mms-123"}

    async def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        msg = EmailMessage()
        msg["From"] = self.smtp_user or "noreply@example.com"
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)

        try:
            if self.smtp_use_tls:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                    server.starttls()
                    if self.smtp_user and self.smtp_password:
                        server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                    if self.smtp_user and self.smtp_password:
                        server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
        except Exception as e:  # pragma: no cover
            return {"status": "failed", "error": str(e)}

        return {"status": "sent", "provider_id": "smtp-accepted"}

    async def receive_email(self, mailbox: str = "INBOX", limit: int = 10) -> List[Dict[str, Any]]:
        def _sync_fetch() -> List[Dict[str, Any]]:
            messages: List[Dict[str, Any]] = []
            if self.imap_use_ssl:
                imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            else:
                imap = imaplib.IMAP4(self.imap_host, self.imap_port)
            try:
                if self.imap_user and self.imap_password:
                    imap.login(self.imap_user, self.imap_password)
                imap.select(mailbox)
                typ, data = imap.search(None, 'ALL')
                if typ != 'OK':
                    return messages
                ids = data[0].split()
                for msg_id in ids[-limit:]:
                    typ, msg_data = imap.fetch(msg_id, '(RFC822)')
                    if typ != 'OK':
                        continue
                    raw_email = msg_data[0][1]
                    parsed = email.message_from_bytes(raw_email)
                    messages.append({
                        "from": parsed.get("From"),
                        "to": parsed.get("To"),
                        "subject": parsed.get("Subject"),
                        "date": parsed.get("Date"),
                    })
                return messages
            finally:
                try:
                    imap.logout()
                except Exception:
                    pass

        return await asyncio.to_thread(_sync_fetch)


class MessageQueue:
    def __init__(self):
        self.queue: asyncio.Queue[MessageRecord] = asyncio.Queue()
        self.records: Dict[str, MessageRecord] = {}

    async def enqueue(self, record: MessageRecord) -> None:
        self.records[record.message_id] = record
        await self.queue.put(record)

    def get_status(self, message_id: str) -> Optional[MessageRecord]:
        return self.records.get(message_id)

    async def worker(self, service: MessagingService) -> None:
        while True:
            record = await self.queue.get()
            record.status = "sending"
            try:
                if record.channel == "sms":
                    res = await service.send_sms(record.to, record.body)
                elif record.channel == "mms":
                    res = await service.send_mms(record.to, record.body, record.media_urls)
                elif record.channel == "email":
                    res = await service.send_email(record.to, record.subject or "", record.body)
                else:
                    res = {"status": "failed", "error": f"Unknown channel {record.channel}"}

                record.status = res.get("status", "failed")
                record.provider_id = res.get("provider_id")
                record.error = res.get("error")
            except Exception as e:  # pragma: no cover
                record.status = "failed"
                record.error = str(e)
            finally:
                self.queue.task_done()

