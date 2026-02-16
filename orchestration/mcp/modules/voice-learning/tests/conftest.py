"""
Pytest configuration for Voice Learning tests
"""

import pytest
import sys
import os

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging between tests"""
    import logging

    logging.getLogger().handlers.clear()
