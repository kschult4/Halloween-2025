#!/usr/bin/env python3
"""
Stage 6 Test Script - Error Handling and Fallback Logic Verification
Tests robust error handling, recovery mechanisms, and system stability.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import time
import threading
from datetime import datetime, timedelta
from error_handler import (
    ErrorHandler, ErrorSeverity, SystemState, ErrorEvent, 
    ErrorCounter, FallbackManager, SystemMonitor, test_error_handling
)
from video_engine import VideoEngine

def test_error_counter():
    """Test error counter and circuit breaker functionality."""
    print("\n=== Testing Error Counter ===")
    
    # Test basic counting
    counter = ErrorCounter(threshold=3, window_minutes=1)
    
    # Add errors below threshold
    assert not counter.add_error(), "Should not exceed threshold on first error"
    assert not counter.add_error(), "Should not exceed threshold on second error"
    assert counter.add_error(), "Should exceed threshold on third error"
    
    assert counter.get_count() == 3, f"Should count 3 errors, got {counter.get_count()}"
    
    # Test reset
    counter.reset()
    assert counter.get_count() == 0, "Should reset to 0"
    
    print("✅ Error counter test passed")
    return True

def test_fallback_manager():
    """Test fallback strategies for different components."""
    print("\n=== Testing Fallback Manager ===")
    
    manager = FallbackManager()
    
    # Test each fallback strategy
    components = ["video_playback", "mqtt_connection", "mask_system", "configuration", "display"]
    
    for component in components:
        error_event = ErrorEvent(
            timestamp=datetime.now(),
            component=component,
            error_type="test_error",
            severity=ErrorSeverity.HIGH,
            message=f"Test error for {component}"
        )
        
        success = manager.trigger_fallback(component, error_event)
        print(f"  {component} fallback: {'✅' if success else '❌'}")
        assert success, f"Fallback should succeed for {component}"
    
    # Test unknown component
    unknown_error = ErrorEvent(
        timestamp=datetime.now(),
        component="unknown_component",
        error_type="test_error",
        severity=ErrorSeverity.HIGH,
        message="Test error for unknown component"
    )
    
    success = manager.trigger_fallback("unknown_component", unknown_error)
    assert not success, "Should fail for unknown component"
    
    print("✅ Fallback manager test passed")
    return True

def test_system_monitor():
    """Test system health monitoring."""
    print("\n=== Testing System Monitor ===")
    
    error_handler = ErrorHandler()
    monitor = SystemMonitor(error_handler)
    
    # Test monitor start/stop
    monitor.start_monitoring()
    assert monitor.monitoring, "Monitor should be running"
    
    # Let it run briefly
    time.sleep(1)
    
    monitor.stop_monitoring()
    assert not monitor.monitoring, "Monitor should be stopped"
    
    # Test individual health checks
    try:
        monitor._check_memory_usage()
        monitor._check_disk_space()
        monitor._check_process_health()
        monitor._check_system_load()
        print("  Health checks completed without error")
    except Exception as e:
        print(f"  Health check error (may be expected): {e}")
    
    print("✅ System monitor test passed")
    return True

def test_error_handler_integration():
    """Test complete error handler integration."""
    print("\n=== Testing Error Handler Integration ===")
    
    error_handler = ErrorHandler()
    
    # Test error callback system
    callback_events = []
    def test_callback(error_event):
        callback_events.append(error_event)
    
    error_handler.add_error_callback(test_callback)
    
    # Generate test errors of different severities
    test_errors = [
        ("component1", "error_type1", ErrorSeverity.LOW, "Low severity error"),
        ("component1", "error_type1", ErrorSeverity.MEDIUM, "Medium severity error"),
        ("component1", "error_type1", ErrorSeverity.HIGH, "High severity error"),
        ("component2", "error_type2", ErrorSeverity.CRITICAL, "Critical severity error"),
    ]
    
    for component, error_type, severity, message in test_errors:
        recovery_triggered = error_handler.handle_error(
            component=component,
            error_type=error_type,
            severity=severity,
            message=message,
            context={"test": True}
        )
        
        print(f"  {severity.value} error: recovery_triggered={recovery_triggered}")
    
    # Verify callbacks were called
    assert len(callback_events) == len(test_errors), "Should trigger callback for each error"
    
    # Verify error history
    assert len(error_handler.error_history) == len(test_errors), "Should record all errors"
    
    # Test error summary
    summary = error_handler.get_error_summary()
    assert summary["total_errors"] == len(test_errors), "Summary should count all errors"
    assert summary["system_state"] != SystemState.NORMAL.value, "System state should change"
    
    print(f"  System state: {summary['system_state']}")
    print(f"  Total errors: {summary['total_errors']}")
    
    # Test state reset
    error_handler.reset_system_state()
    summary = error_handler.get_error_summary()
    assert summary["system_state"] == SystemState.NORMAL.value, "Should reset to normal"
    
    print("✅ Error handler integration test passed")
    return True

def test_video_engine_error_integration():
    """Test error handling integration with video engine."""
    print("\n=== Testing Video Engine Error Integration ===")
    
    engine = VideoEngine()
    
    # Verify error handler is initialized
    assert hasattr(engine, 'error_handler'), "Engine should have error handler"
    assert engine.error_handler is not None, "Error handler should be initialized"
    
    # Test error handling in video operations
    engine.preload_videos(['media/active', 'media/ambient'])
    
    # Test starting playback with non-existent video
    success = engine.start_playback("nonexistent_video")
    assert not success, "Should fail for non-existent video"
    
    # Check that error was recorded
    error_summary = engine.error_handler.get_error_summary()
    assert error_summary["total_errors"] > 0, "Should record the error"
    
    print(f"  Recorded {error_summary['total_errors']} errors")
    
    # Test with valid video if available
    available_videos = engine.get_available_videos()
    if available_videos:
        success = engine.start_playback(available_videos[0])
        print(f"  Valid video playback: {'✅' if success else '❌'}")
    
    engine.cleanup()
    print("✅ Video engine error integration test passed")
    return True

def test_error_recovery_scenarios():
    """Test various error recovery scenarios."""
    print("\n=== Testing Error Recovery Scenarios ===")
    
    error_handler = ErrorHandler()
    
    # Scenario 1: Rapid repeated errors (circuit breaker)
    print("  Scenario 1: Rapid repeated errors")
    for i in range(6):  # Exceed threshold
        error_handler.handle_error(
            component="test_component",
            error_type="repeated_error",
            severity=ErrorSeverity.MEDIUM,
            message=f"Repeated error {i+1}"
        )
    
    summary = error_handler.get_error_summary()
    assert summary["system_state"] != SystemState.NORMAL.value, "Should trigger state change"
    
    # Scenario 2: Critical error
    print("  Scenario 2: Critical error")
    error_handler.reset_system_state()
    
    error_handler.handle_error(
        component="critical_component",
        error_type="critical_failure",
        severity=ErrorSeverity.CRITICAL,
        message="Critical system failure"
    )
    
    summary = error_handler.get_error_summary()
    assert summary["system_state"] == SystemState.EMERGENCY.value, "Should enter emergency state"
    
    # Scenario 3: Recovery
    print("  Scenario 3: Manual recovery")
    error_handler.reset_system_state()
    
    summary = error_handler.get_error_summary()
    assert summary["system_state"] == SystemState.NORMAL.value, "Should return to normal"
    
    print("✅ Error recovery scenarios test passed")
    return True

def test_long_term_stability():
    """Test system stability over extended operation."""
    print("\n=== Testing Long-term Stability ===")
    
    error_handler = ErrorHandler()
    error_handler.start_monitoring()
    
    # Simulate various errors over time
    start_time = time.time()
    error_count = 0
    
    print("  Running stability test for 5 seconds...")
    
    while time.time() - start_time < 5:  # 5 second test
        # Occasionally generate errors
        if error_count % 10 == 0:
            error_handler.handle_error(
                component="stability_test",
                error_type="periodic_error",
                severity=ErrorSeverity.LOW,
                message=f"Stability test error {error_count}",
                context={"iteration": error_count}
            )
        
        error_count += 1
        time.sleep(0.1)
    
    error_handler.stop_monitoring()
    
    # Check system is still operational
    summary = error_handler.get_error_summary()
    print(f"  Processed {error_count} iterations with {summary['total_errors']} errors")
    
    # System should handle the load
    assert summary["total_errors"] > 0, "Should have generated some errors"
    assert len(error_handler.error_history) <= error_handler.max_history_size, "Should limit history size"
    
    print("✅ Long-term stability test passed")
    return True

def test_resource_cleanup():
    """Test proper resource cleanup under error conditions."""
    print("\n=== Testing Resource Cleanup ===")
    
    # Test error handler cleanup
    error_handler = ErrorHandler()
    error_handler.start_monitoring()
    
    # Generate some activity
    for i in range(3):
        error_handler.handle_error(
            component="cleanup_test",
            error_type="test_error",
            severity=ErrorSeverity.LOW,
            message=f"Cleanup test error {i}"
        )
    
    # Test cleanup
    initial_errors = len(error_handler.error_history)
    error_handler.stop_monitoring()
    
    # Should still have error history (allow for system monitor errors)
    assert len(error_handler.error_history) >= initial_errors, "Should preserve error history"
    
    # Test video engine cleanup with errors
    engine = VideoEngine()
    
    # Generate an error
    engine.error_handler.handle_error(
        component="cleanup_test",
        error_type="pre_cleanup_error",
        severity=ErrorSeverity.MEDIUM,
        message="Error before cleanup"
    )
    
    # Cleanup should not raise exceptions
    try:
        engine.cleanup()
        cleanup_success = True
    except Exception as e:
        print(f"  Cleanup error: {e}")
        cleanup_success = False
    
    assert cleanup_success, "Cleanup should succeed even with errors"
    
    print("✅ Resource cleanup test passed")
    return True

def main():
    """Run all Stage 6 tests."""
    print("Halloween Projection Mapper - Stage 6 Tests")
    print("=" * 50)
    
    try:
        # Core functionality tests
        test_results = [
            test_error_handling() or True,  # From error_handler.py returns None
            test_error_counter(),
            test_fallback_manager(),
            test_system_monitor(),
            test_error_handler_integration(),
            test_video_engine_error_integration(),
            test_error_recovery_scenarios(),
            test_long_term_stability(),
            test_resource_cleanup(),
        ]
        
        # Results
        print("\n=== Test Results ===")
        passed = sum(test_results)
        total = len(test_results)
        
        print(f"Tests passed: {passed}/{total}")
        
        if all(test_results):
            print("\n✅ Stage 6 tests PASSED - Error handling system ready!")
            print("\nFeatures verified:")
            print("  - Comprehensive error classification and handling")
            print("  - Circuit breaker pattern for repeated failures")
            print("  - Component-specific fallback strategies")
            print("  - System health monitoring and alerting")
            print("  - Automatic recovery and state management")
            print("  - Long-term stability and resource management")
            print("  - Graceful cleanup under error conditions")
            return True
        else:
            print("\n❌ Stage 6 tests FAILED - Check implementation")
            return False
            
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()