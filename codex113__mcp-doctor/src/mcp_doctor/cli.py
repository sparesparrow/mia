"""Compatibility wrapper for the bundled MCP Doctor CLI."""

from src.mcp_doctor.cli import build_parser, main

__all__ = ["build_parser", "main"]
