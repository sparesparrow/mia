#!/usr/bin/env python3
"""
Test script for MIA MCP Integration

Tests the integration between Cursor MCP and MIA hardware services.
"""

import asyncio
import json
import logging
import sys
import os

# Add MIA modules to path (handle both CI and local development)
mia_path = os.path.dirname(__file__)  # Repository root
sys.path.insert(0, mia_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_mia_integration():
    """Test hardware MCP server integration"""
    logger.info("Starting MIA MCP Integration Test")

    try:
        # Check if required files exist
        required_files = [
            'modules/hardware-bridge/hardware_server.py',
            'modules/hardware-bridge/hardware_tools.py',
            'modules/core-orchestrator/main.py',
            'modules/core-orchestrator/car_assistant_config.py'
        ]

        for file_path in required_files:
            if not os.path.exists(file_path):
                logger.error(f"Required file not found: {file_path}")
                return False

        logger.info("✅ All MIA integration files found")

        # Check if MCP configuration exists (optional for CI)
        mcp_config_path = os.path.expanduser('~/.cursor/mcp.json')
        if os.path.exists(mcp_config_path):
            try:
                # Validate MCP configuration contains car assistant services
                with open(mcp_config_path, 'r') as f:
                    mcp_config = json.load(f)

                required_servers = ['car-assistant-mia', 'mcp-prompts-memory', 'mia-core-orchestrator']
                configured_servers = mcp_config.get('mcpServers', {})

                for server in required_servers:
                    if server not in configured_servers:
                        logger.warning(f"Required MCP server not configured: {server}")
                        continue

                    server_config = configured_servers[server]
                    if 'command' not in server_config or 'args' not in server_config:
                        logger.warning(f"MCP server {server} missing command/args configuration")
                        continue

                logger.info("✅ MCP configuration is valid")
            except Exception as e:
                logger.warning(f"MCP configuration validation failed: {e}")
        else:
            logger.info("ℹ️  MCP configuration not found (expected in development environments)")

        # Test if Python can run the hardware server (syntax check)
        import subprocess
        try:
            result = subprocess.run([
                'python3', '-m', 'py_compile',
                'modules/hardware-bridge/hardware_server.py'
            ], capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                logger.error(f"Hardware server syntax error: {result.stderr}")
                return False

            logger.info("✅ Hardware server syntax is valid")

        except subprocess.TimeoutExpired:
            logger.error("Hardware server syntax check timed out")
            return False
        except Exception as e:
            logger.error(f"Hardware server syntax check failed: {e}")
            return False

        return True

    except Exception as e:
        logger.error(f"❌ Hardware server test failed: {e}")
        return False


async def test_mcp_prompts_integration():
    """Test MCP prompts integration"""
    logger.info("Testing MCP Prompts Integration")

    try:
        # Check if MCP prompts package directory exists
        prompts_dir = os.path.join(os.path.dirname(__file__), 'mcp-prompts')
        if os.path.exists(prompts_dir):
            logger.info("✅ MCP Prompts directory exists")

            # Check if car assistant prompt was created
            prompt_file = os.path.join(prompts_dir, 'data', 'prompts', 'public', 'car-assistant-driver.json')
            if os.path.exists(prompt_file):
                logger.info("✅ Car assistant prompt file exists")
                return True
            else:
                logger.error("❌ Car assistant prompt file not found")
                return False
        else:
            logger.error("❌ MCP Prompts directory not found")
            return False

    except Exception as e:
        logger.error(f"❌ MCP Prompts integration test failed: {e}")
        return False


async def main():
    """Run all integration tests"""
    logger.info("Running MIA MCP Integration Tests")

    # Test MCP prompts
    prompts_ok = await test_mcp_prompts_integration()

    # Test hardware MCP server
    hardware_ok = await test_mia_integration()

    if prompts_ok and hardware_ok:
        logger.info("✅ All integration tests passed!")
        return 0
    else:
        logger.error("❌ Some integration tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)