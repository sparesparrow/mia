"""
Messages MCP Server
Provides multi-channel messaging tools (SMS/MMS/Email) using the Python MCP framework.
"""

import asyncio
import os
import uuid
import logging
from typing import Dict, Any, List, Optional

import websockets

from modules.mcp_framework import (
    MCPServer,
    WebSocketTransport,
    create_tool,
)

from .service import MessagingService, MessageQueue, MessageRecord


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessagingMCPServer(MCPServer):
    def __init__(self):
        super().__init__("messages-mcp", "0.1.0")
        self.service = MessagingService()
        self.queue = MessageQueue()
        self._queue_worker_started = False
        self._setup_tools()

    def _start_queue_worker(self):
        if not self._queue_worker_started:
            asyncio.create_task(self.queue.worker(self.service))
            self._queue_worker_started = True

    def _setup_tools(self):
        self.add_tool(create_tool(
            name="send_sms",
            description="Send an SMS message",
            schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient phone number"},
                    "body": {"type": "string", "description": "Message text"}
                },
                "required": ["to", "body"]
            },
            handler=self.handle_send_sms
        ))

        self.add_tool(create_tool(
            name="send_mms",
            description="Send an MMS message",
            schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "body": {"type": "string"},
                    "media_urls": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["to", "body"]
            },
            handler=self.handle_send_mms
        ))

        self.add_tool(create_tool(
            name="send_email",
            description="Send an email via SMTP",
            schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"}
                },
                "required": ["to", "subject", "body"]
            },
            handler=self.handle_send_email
        ))

        self.add_tool(create_tool(
            name="receive_email",
            description="Fetch recent emails via IMAP",
            schema={
                "type": "object",
                "properties": {
                    "mailbox": {"type": "string", "default": "INBOX"},
                    "limit": {"type": "integer", "default": 10}
                }
            },
            handler=self.handle_receive_email
        ))

        self.add_tool(create_tool(
            name="queue_message",
            description="Queue a message for delivery",
            schema={
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "enum": ["sms", "mms", "email"]},
                    "to": {"type": "string"},
                    "body": {"type": "string"},
                    "subject": {"type": "string"},
                    "media_urls": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["channel", "to", "body"]
            },
            handler=self.handle_queue_message
        ))

        self.add_tool(create_tool(
            name="delivery_status",
            description="Get status of a queued message",
            schema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string"}
                },
                "required": ["message_id"]
            },
            handler=self.handle_delivery_status
        ))

    async def handle_send_sms(self, to: str, body: str) -> Dict[str, Any]:
        return await self.service.send_sms(to, body)

    async def handle_send_mms(self, to: str, body: str, media_urls: Optional[List[str]] = None) -> Dict[str, Any]:
        return await self.service.send_mms(to, body, media_urls)

    async def handle_send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        return await self.service.send_email(to, subject, body)

    async def handle_receive_email(self, mailbox: str = "INBOX", limit: int = 10) -> Dict[str, Any]:
        messages = await self.service.receive_email(mailbox, limit)
        return {"messages": messages, "count": len(messages)}

    async def handle_queue_message(self, channel: str, to: str, body: str,
                                   subject: Optional[str] = None,
                                   media_urls: Optional[List[str]] = None) -> Dict[str, Any]:
        message_id = str(uuid.uuid4())
        record = MessageRecord(
            message_id=message_id,
            channel=channel,
            to=to,
            subject=subject,
            body=body,
            media_urls=media_urls or [],
        )
        await self.queue.enqueue(record)
        self._start_queue_worker()
        return {"message_id": message_id, "status": record.status}

    async def handle_delivery_status(self, message_id: str) -> Dict[str, Any]:
        record = self.queue.get_status(message_id)
        if not record:
            return {"error": "not_found"}
        return {
            "message_id": record.message_id,
            "status": record.status,
            "provider_id": record.provider_id,
            "error": record.error,
        }


async def main():
    logger.info("Starting Messages MCP Server")
    server = MessagingMCPServer()

    async def handle_websocket(websocket, path):
        logger.info("New WebSocket client connected")
        transport = WebSocketTransport(websocket)
        await server.serve(transport)

    port = int(os.getenv("MESSAGES_PORT", 8091))
    start_server = websockets.serve(handle_websocket, "0.0.0.0", port)
    logger.info(f"Messages MCP Server listening on port {port}")
    try:
        await start_server
        await asyncio.Future()
    except KeyboardInterrupt:
        logger.info("Shutting down Messages MCP Server")


if __name__ == "__main__":
    asyncio.run(main())

