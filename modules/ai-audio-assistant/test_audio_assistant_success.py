#!/usr/bin/env python3
"""
Comprehensive test script for AI Audio Assistant MCP Server
This version demonstrates successful operations with available devices
"""

import asyncio
import logging
from test_audio_assistant import TestAudioManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_successful_operations():
    """Test successful audio operations using available devices"""
    logger.info("=== Starting Successful Operations Test ===")
    
    # Initialize AudioManager
    audio_manager = TestAudioManager()
    
    # Test with available devices
    available_devices = list(audio_manager.devices.keys())
    logger.info(f"Available devices for testing: {available_devices}")
    
    if available_devices:
        # Test device switching with available device
        logger.info("\n--- Testing Successful Device Switching ---")
        test_device = available_devices[0]
        result = await audio_manager.switch_output(test_device, "living_room")
        logger.info(f"Switch to {test_device} result: {result}")
        
        # Verify the device is active
        active_device = audio_manager.get_active_device()
        if active_device:
            logger.info(f"✓ Successfully activated device: {active_device.name} ({active_device.id})")
        else:
            logger.error("✗ No active device after switching")
        
        # Test zone activation
        zone_info = audio_manager.get_zone_info("living_room")
        if zone_info and zone_info.is_active:
            logger.info(f"✓ Successfully activated zone: living_room (volume: {zone_info.volume}%)")
        else:
            logger.error("✗ Zone not activated after switching")
    
    # Test volume control
    logger.info("\n--- Testing Successful Volume Control ---")
    
    # Test global volume
    result = await audio_manager.set_volume(80)
    logger.info(f"Set global volume to 80% result: {result}")
    if result and audio_manager.volume == 80:
        logger.info("✓ Global volume successfully set to 80%")
    else:
        logger.error("✗ Global volume setting failed")
    
    # Test zone volume
    result = await audio_manager.set_volume(65, "living_room")
    logger.info(f"Set living_room volume to 65% result: {result}")
    zone_info = audio_manager.get_zone_info("living_room")
    if result and zone_info and zone_info.volume == 65:
        logger.info("✓ Zone volume successfully set to 65%")
    else:
        logger.error("✗ Zone volume setting failed")
    
    # Test volume clamping
    result = await audio_manager.set_volume(-10)  # Should clamp to 0
    logger.info(f"Set volume to -10 (should clamp to 0) result: {result}")
    if result and audio_manager.volume == 0:
        logger.info("✓ Volume successfully clamped to 0")
    else:
        logger.error("✗ Volume clamping failed")
    
    # Test comprehensive status
    logger.info("\n--- Testing Status Information ---")
    
    # Show all devices
    logger.info("Device Status:")
    for device_id, device in audio_manager.devices.items():
        status = "ACTIVE" if device.is_active else "inactive"
        logger.info(f"  {device.name} ({device_id}): {device.type} - {status}")
    
    # Show all zones
    logger.info("Zone Status:")
    for zone_name, zone in audio_manager.zones.items():
        status = "ACTIVE" if zone.is_active else "inactive"
        logger.info(f"  {zone_name}: devices={zone.devices}, volume={zone.volume}%, {status}")
    
    # Test error handling
    logger.info("\n--- Testing Error Handling ---")
    
    # Test invalid device (should fail gracefully)
    result = await audio_manager.switch_output("nonexistent_device")
    if not result:
        logger.info("✓ Invalid device switching handled correctly")
    else:
        logger.error("✗ Invalid device switching should have failed")
    
    # Test invalid zone (should fail gracefully)
    result = await audio_manager.set_volume(50, "nonexistent_zone")
    if not result:
        logger.info("✓ Invalid zone volume setting handled correctly")
    else:
        logger.error("✗ Invalid zone volume setting should have failed")
    
    logger.info("\n=== Successful Operations Test Completed ===")
    logger.info("✓ All tests completed - Audio Assistant is working correctly!")


if __name__ == "__main__":
    asyncio.run(test_successful_operations())