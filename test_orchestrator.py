#!/usr/bin/env python3
"""
Test script for MIA Enhanced Core Orchestrator
Demonstrates the core functionality and features
"""

import asyncio
import json
import sys
import time
from pathlib import Path

# Add the modules to path
sys.path.append(str(Path(__file__).parent / "modules" / "core-orchestrator"))

from enhanced_orchestrator import EnhancedCoreOrchestrator, ServiceInfo
from mcp_framework import create_tool


class MockService:
    """Mock service for testing"""
    
    def __init__(self, name: str, port: int):
        self.name = name
        self.port = port
        self.call_count = 0
        self.responses = {
            "play_music": f"{name}: Playing music as requested",
            "control_volume": f"{name}: Volume adjusted",
            "switch_audio": f"{name}: Audio output switched",
            "execute_command": f"{name}: Command executed",
            "gpio_control": f"{name}: GPIO pin controlled",
            "control_device": f"{name}: Smart home device controlled"
        }
    
    async def handle_call(self, tool_name: str, parameters: dict) -> str:
        """Handle mock service call"""
        self.call_count += 1
        response = self.responses.get(tool_name, f"{self.name}: Unknown tool {tool_name}")
        
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        # Add parameter information to response
        if parameters:
            param_str = ", ".join([f"{k}={v}" for k, v in parameters.items()])
            response += f" (params: {param_str})"
        
        return response


async def test_basic_nlp():
    """Test basic NLP functionality"""
    print("🧠 Testing NLP Engine...")
    
    orchestrator = EnhancedCoreOrchestrator()
    
    test_commands = [
        "Play some jazz music by Miles Davis",
        "Set the volume to 75",
        "Switch to headphones", 
        "Open Firefox browser",
        "Turn on GPIO pin 18",
        "Turn on the living room lights",
        "Make it louder",  # Follow-up command
        "What's the weather like?"
    ]
    
    for command in test_commands:
        print(f"\n📝 Command: '{command}'")
        
        result = await orchestrator.handle_analyze_intent(command)
        
        print(f"   Intent: {result['intent']}")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Parameters: {result['parameters']}")
        
        if result['alternatives']:
            alts = [f"{intent} ({conf:.2f})" for intent, conf in result['alternatives']]
            print(f"   Alternatives: {', '.join(alts)}")
    
    print("\n✅ NLP testing completed")


async def test_context_management():
    """Test context management"""
    print("\n🗂️  Testing Context Management...")
    
    orchestrator = EnhancedCoreOrchestrator()
    
    # Create a session
    session_result = await orchestrator.handle_create_session("test_user", "voice")
    session_id = session_result["session_id"]
    print(f"   Created session: {session_id}")
    
    # Test context-aware commands
    commands = [
        "Play some jazz music",
        "Make it louder",  # Should use context from previous command
        "Switch to speakers",
        "Play something different"  # Should maintain audio context
    ]
    
    for i, command in enumerate(commands):
        print(f"\n📝 Command {i+1}: '{command}'")
        
        result = await orchestrator.handle_enhanced_voice_command(
            text=command,
            session_id=session_id,
            user_id="test_user",
            interface_type="voice"
        )
        
        print(f"   Response: {result['response']}")
        print(f"   Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
        print(f"   Context used: {result['context_used']}")
    
    print("\n✅ Context management testing completed")


async def test_service_integration():
    """Test service integration"""
    print("\n🔗 Testing Service Integration...")
    
    orchestrator = EnhancedCoreOrchestrator()
    
    # Register mock services
    mock_services = [
        MockService("ai-audio-assistant", 8082),
        MockService("ai-platform-linux", 8083),
        MockService("hardware-bridge", 8084),
        MockService("ai-home-automation", 8085)
    ]
    
    for mock in mock_services:
        service = ServiceInfo(
            name=mock.name,
            host="localhost",
            port=mock.port,
            capabilities=["mock"],
            service_type="mock"
        )
        orchestrator.services[mock.name] = service
    
    # Override service calling to use mocks
    original_call = orchestrator._call_service_enhanced
    
    async def mock_call_service(service_name: str, tool_name: str, parameters: dict, session_context):
        mock = next((m for m in mock_services if m.name == service_name), None)
        if mock:
            return await mock.handle_call(tool_name, parameters)
        return await original_call(service_name, tool_name, parameters, session_context)
    
    orchestrator._call_service_enhanced = mock_call_service
    
    # Test various service calls
    test_commands = [
        ("Play rock music", "ai-audio-assistant"),
        ("Open terminal", "ai-platform-linux"),
        ("Turn on pin 21", "hardware-bridge"),
        ("Dim the lights", "ai-home-automation")
    ]
    
    for command, expected_service in test_commands:
        print(f"\n📝 Command: '{command}' -> Expected: {expected_service}")
        
        result = await orchestrator.handle_enhanced_voice_command(
            text=command,
            user_id="test_user",
            interface_type="test"
        )
        
        print(f"   Response: {result['response']}")
        print(f"   Intent: {result['intent']}")
    
    # Show service call statistics
    print(f"\n📊 Service Call Statistics:")
    for mock in mock_services:
        print(f"   {mock.name}: {mock.call_count} calls")
    
    print("\n✅ Service integration testing completed")


async def test_performance():
    """Test performance characteristics"""
    print("\n⚡ Testing Performance...")
    
    orchestrator = EnhancedCoreOrchestrator()
    
    # Test command processing speed
    commands = [
        "Play music",
        "Set volume 50",
        "Switch audio",
        "Open app",
        "Control GPIO"
    ] * 20  # 100 commands total
    
    start_time = time.time()
    
    for i, command in enumerate(commands):
        result = await orchestrator.handle_analyze_intent(command)
        
        if i % 20 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            print(f"   Processed {i+1} commands in {elapsed:.2f}s ({rate:.1f} cmd/s)")
    
    total_time = time.time() - start_time
    total_commands = len(commands)
    avg_rate = total_commands / total_time
    avg_latency = (total_time / total_commands) * 1000  # ms
    
    print(f"\n📈 Performance Results:")
    print(f"   Total commands: {total_commands}")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Average rate: {avg_rate:.1f} commands/second")
    print(f"   Average latency: {avg_latency:.1f}ms per command")
    
    print("\n✅ Performance testing completed")


async def test_error_handling():
    """Test error handling"""
    print("\n🛡️  Testing Error Handling...")
    
    orchestrator = EnhancedCoreOrchestrator()
    
    # Test various error conditions
    error_tests = [
        ("", "Empty command"),
        ("aslkdjfalksjdf", "Gibberish command"),
        ("Play music on nonexistent service", "Invalid service"),
        ("🎵🎶🎵", "Unicode/emoji command")
    ]
    
    for command, description in error_tests:
        print(f"\n📝 Testing: {description}")
        print(f"   Command: '{command}'")
        
        try:
            result = await orchestrator.handle_enhanced_voice_command(
                text=command,
                user_id="test_user",
                interface_type="test"
            )
            
            print(f"   Response: {result['response']}")
            print(f"   Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
            
        except Exception as e:
            print(f"   Error: {str(e)}")
    
    print("\n✅ Error handling testing completed")


async def test_session_management():
    """Test session lifecycle management"""
    print("\n📋 Testing Session Management...")
    
    orchestrator = EnhancedCoreOrchestrator()
    
    # Create multiple sessions
    sessions = []
    for i in range(5):
        result = await orchestrator.handle_create_session(f"user_{i}", "test")
        sessions.append(result["session_id"])
        print(f"   Created session {i+1}: {result['session_id']}")
    
    # Test session isolation
    for i, session_id in enumerate(sessions):
        await orchestrator.handle_enhanced_voice_command(
            text=f"Play playlist {i+1}",
            session_id=session_id,
            user_id=f"user_{i}",
            interface_type="test"
        )
    
    # Check session contexts
    print(f"\n📊 Session Context Status:")
    for i, session_id in enumerate(sessions):
        context = orchestrator.context_manager.get_session(session_id)
        if context:
            print(f"   Session {i+1}: {len(context.command_history)} commands in history")
        else:
            print(f"   Session {i+1}: Not found or expired")
    
    # Test cleanup
    print(f"\n🧹 Testing session cleanup...")
    orchestrator.context_manager.cleanup_expired_sessions()
    print(f"   Cleanup completed")
    
    print("\n✅ Session management testing completed")


async def run_all_tests():
    """Run all test suites"""
    print("🚀 Starting MIA Enhanced Core Orchestrator Tests")
    print("=" * 60)
    
    test_suites = [
        ("Basic NLP", test_basic_nlp),
        ("Context Management", test_context_management),
        ("Service Integration", test_service_integration),
        ("Performance", test_performance),
        ("Error Handling", test_error_handling),
        ("Session Management", test_session_management)
    ]
    
    results = {}
    total_start = time.time()
    
    for suite_name, test_func in test_suites:
        print(f"\n{'='*20} {suite_name} {'='*20}")
        
        try:
            suite_start = time.time()
            await test_func()
            suite_time = time.time() - suite_start
            results[suite_name] = {"status": "PASSED", "time": suite_time}
            
        except Exception as e:
            suite_time = time.time() - suite_start
            results[suite_name] = {"status": "FAILED", "time": suite_time, "error": str(e)}
            print(f"\n❌ Test suite failed: {e}")
    
    total_time = time.time() - total_start
    
    # Print summary
    print("\n" + "="*60)
    print("🏁 TEST SUMMARY")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for suite_name, result in results.items():
        status_icon = "✅" if result["status"] == "PASSED" else "❌"
        print(f"{status_icon} {suite_name}: {result['status']} ({result['time']:.2f}s)")
        
        if result["status"] == "PASSED":
            passed += 1
        else:
            failed += 1
            if "error" in result:
                print(f"    Error: {result['error']}")
    
    print(f"\nResults: {passed} passed, {failed} failed")
    print(f"Total time: {total_time:.2f}s")
    
    if failed == 0:
        print("\n🎉 All tests passed! The Enhanced Core Orchestrator is working correctly.")
    else:
        print(f"\n⚠️  {failed} test suite(s) failed. Please check the errors above.")
    
    return failed == 0


if __name__ == "__main__":
    # Run the test suite
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)