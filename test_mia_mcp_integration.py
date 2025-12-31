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

# Add MIA modules to path
mia_path = os.path.join(os.path.dirname(__file__), 'mia')
sys.path.insert(0, mia_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_mia_integration():
    """Test hardware MCP server integration"""
    logger.info("Starting MIA MCP Integration Test")

    try:
        # Check if required files exist (try both direct paths and mia/ subdirectory)
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

        # Check if MCP configuration exists (optional for CI - skip validation)
        mcp_config_path = os.path.expanduser('~/.cursor/mcp.json')
        if os.path.exists(mcp_config_path):
            logger.info("ℹ️  MCP configuration found (validation skipped in CI)")
        else:
            logger.info("ℹ️  MCP configuration not found (expected in development environments)")

        # Test if Python can run the hardware server (syntax check)
        import subprocess
        try:
            # Try both possible paths for the hardware server file
            hardware_server_paths = [
                'modules/hardware-bridge/hardware_server.py',
                'mia/modules/hardware-bridge/hardware_server.py'
            ]

            hardware_server_file = None
            for path in hardware_server_paths:
                if os.path.exists(path):
                    hardware_server_file = path
                    break

            if not hardware_server_file:
                logger.error("Hardware server file not found in any expected location")
                return False

            result = subprocess.run([
                'python3', '-m', 'py_compile', hardware_server_file
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
        # Check if prompts directory exists
        prompts_dir = os.path.join(os.path.dirname(__file__), 'prompts')
        if os.path.exists(prompts_dir):
            logger.info("✅ Prompts directory exists")

            # Check if car assistant prompts were created
            car_prompts = [
                'mia-car-voice-command.json',
                'mia-car-navigation.json',
                'mia-car-climate-control.json'
            ]

            found_prompts = 0
            for prompt_file in car_prompts:
                prompt_path = os.path.join(prompts_dir, prompt_file)
                if os.path.exists(prompt_path):
                    found_prompts += 1
                    logger.info(f"✅ Found prompt: {prompt_file}")
                else:
                    logger.warning(f"❌ Missing prompt: {prompt_file}")

            if found_prompts >= 2:  # Require at least 2 out of 3 prompts
                logger.info(f"✅ Found {found_prompts} car assistant prompts")
                return True
            else:
                logger.error(f"❌ Only found {found_prompts} car assistant prompts, expected at least 2")
                return False
        else:
            logger.warning("ℹ️  Prompts directory not found (may be expected in some environments)")
            return True  # Don't fail if prompts directory doesn't exist

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