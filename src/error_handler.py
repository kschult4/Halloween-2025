"""
Error handling and fallback logic for Halloween Projection Mapper.
Ensures robust operation and graceful degradation under various failure conditions.
"""
import logging
import time
import threading
import traceback
from typing import Optional, Callable, Dict, Any, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"           # Minor issues, continue operation
    MEDIUM = "medium"     # Significant issues, attempt recovery
    HIGH = "high"         # Critical issues, enter safe mode
    CRITICAL = "critical" # System failure, restart required

class SystemState(Enum):
    """System operational states."""
    NORMAL = "normal"           # Full functionality
    DEGRADED = "degraded"       # Limited functionality
    SAFE_MODE = "safe_mode"     # Minimal functionality
    EMERGENCY = "emergency"     # Emergency fallback only

@dataclass
class ErrorEvent:
    """Represents an error event in the system."""
    timestamp: datetime
    component: str
    error_type: str
    severity: ErrorSeverity
    message: str
    exception: Optional[Exception] = None
    context: Optional[Dict[str, Any]] = None
    resolved: bool = False
    resolution_time: Optional[datetime] = None

class ErrorCounter:
    """Tracks error frequency for circuit breaker pattern."""
    
    def __init__(self, threshold: int = 5, window_minutes: int = 5):
        self.threshold = threshold
        self.window = timedelta(minutes=window_minutes)
        self.errors: List[datetime] = []
        self.lock = threading.Lock()
    
    def add_error(self) -> bool:
        """Add an error event. Returns True if threshold exceeded."""
        with self.lock:
            now = datetime.now()
            
            # Remove old errors outside window
            cutoff = now - self.window
            self.errors = [err_time for err_time in self.errors if err_time > cutoff]
            
            # Add new error
            self.errors.append(now)
            
            return len(self.errors) >= self.threshold
    
    def reset(self):
        """Reset error counter."""
        with self.lock:
            self.errors.clear()
    
    def get_count(self) -> int:
        """Get current error count in window."""
        with self.lock:
            now = datetime.now()
            cutoff = now - self.window
            self.errors = [err_time for err_time in self.errors if err_time > cutoff]
            return len(self.errors)

class FallbackManager:
    """Manages fallback behaviors for different system components."""
    
    def __init__(self):
        self.fallback_strategies = {
            "video_playback": self._video_playback_fallback,
            "mqtt_connection": self._mqtt_connection_fallback,
            "mask_system": self._mask_system_fallback,
            "configuration": self._configuration_fallback,
            "display": self._display_fallback,
        }
        
        self.fallback_states = {}
        self.recovery_attempts = {}
    
    def trigger_fallback(self, component: str, error_event: ErrorEvent) -> bool:
        """Trigger fallback for a specific component."""
        try:
            if component in self.fallback_strategies:
                strategy = self.fallback_strategies[component]
                success = strategy(error_event)
                
                if success:
                    self.fallback_states[component] = True
                    logger.info(f"Fallback activated for {component}")
                else:
                    logger.error(f"Fallback failed for {component}")
                
                return success
            else:
                logger.warning(f"No fallback strategy for component: {component}")
                return False
                
        except Exception as e:
            logger.error(f"Fallback strategy failed for {component}: {e}")
            return False
    
    def _video_playback_fallback(self, error_event: ErrorEvent) -> bool:
        """Fallback strategy for video playback failures."""
        logger.info("Implementing video playback fallback")
        
        # Fallback strategies in order of preference:
        # 1. Switch to different video format/codec
        # 2. Reduce resolution/quality
        # 3. Use static image fallback
        # 4. Display error pattern
        
        try:
            # For now, log the strategy - actual implementation would
            # integrate with video engine
            fallback_actions = [
                "Switch to backup ambient video",
                "Reduce playback quality",
                "Display static Halloween pattern",
                "Show system status overlay"
            ]
            
            for action in fallback_actions:
                logger.info(f"Video fallback action planned: {action}")
            logger.info("Video playback fallback not yet implemented; manual intervention required")
            return False
            
        except Exception as e:
            logger.error(f"Video playback fallback failed: {e}")
            return False
    
    def _mqtt_connection_fallback(self, error_event: ErrorEvent) -> bool:
        """Fallback strategy for MQTT connection failures."""
        logger.info("Implementing MQTT connection fallback")
        
        try:
            # MQTT fallback strategies:
            # 1. Retry connection with backoff
            # 2. Switch to local mode with timer-based state changes
            # 3. Use manual control mode
            
            fallback_actions = [
                "Enable local timer-based mode",
                "Activate manual control interface",
                "Use default state cycling",
                "Display connection status"
            ]
            
            for action in fallback_actions:
                logger.info(f"MQTT fallback action planned: {action}")
            logger.info("MQTT fallback not yet implemented; manual intervention required")
            return False
            
        except Exception as e:
            logger.error(f"MQTT fallback failed: {e}")
            return False
    
    def _mask_system_fallback(self, error_event: ErrorEvent) -> bool:
        """Fallback strategy for mask system failures."""
        logger.info("Implementing mask system fallback")
        
        try:
            # Mask system fallback strategies:
            # 1. Use default rectangular masks
            # 2. Disable masking (full frame output)
            # 3. Use simplified single mask
            
            fallback_actions = [
                "Load default rectangular masks",
                "Disable advanced masking features",
                "Use full-frame output mode"
            ]
            
            for action in fallback_actions:
                logger.info(f"Mask fallback action planned: {action}")
            logger.info("Mask fallback not yet implemented; manual intervention required")
            return False
            
        except Exception as e:
            logger.error(f"Mask system fallback failed: {e}")
            return False
    
    def _configuration_fallback(self, error_event: ErrorEvent) -> bool:
        """Fallback strategy for configuration failures."""
        logger.info("Implementing configuration fallback")
        
        try:
            # Configuration fallback strategies:
            # 1. Use built-in defaults
            # 2. Load backup configuration
            # 3. Create minimal working config
            
            fallback_actions = [
                "Load built-in default settings",
                "Create minimal working configuration",
                "Disable advanced features"
            ]
            
            for action in fallback_actions:
                logger.info(f"Configuration fallback action planned: {action}")
            logger.info("Configuration fallback not yet implemented; manual intervention required")
            return False
            
        except Exception as e:
            logger.error(f"Configuration fallback failed: {e}")
            return False
    
    def _display_fallback(self, error_event: ErrorEvent) -> bool:
        """Fallback strategy for display failures."""
        logger.info("Implementing display fallback")
        
        try:
            # Display fallback strategies:
            # 1. Reduce resolution
            # 2. Switch to windowed mode
            # 3. Use software rendering
            
            fallback_actions = [
                "Switch to lower resolution",
                "Enable windowed mode",
                "Use software rendering fallback"
            ]
            
            for action in fallback_actions:
                logger.info(f"Display fallback action planned: {action}")
            logger.info("Display fallback not yet implemented; manual intervention required")
            return False
            
        except Exception as e:
            logger.error(f"Display fallback failed: {e}")
            return False

class SystemMonitor:
    """Monitors system health and triggers recovery actions."""
    
    def __init__(self, error_handler: 'ErrorHandler'):
        self.error_handler = error_handler
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.check_interval = 30  # seconds
        
        # Health check functions
        self.health_checks = {
            "memory_usage": self._check_memory_usage,
            "disk_space": self._check_disk_space,
            "process_health": self._check_process_health,
            "system_load": self._check_system_load,
        }
    
    def start_monitoring(self):
        """Start system health monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("System monitoring started")
    
    def stop_monitoring(self):
        """Stop system health monitoring."""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        logger.info("System monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                # Run health checks
                for check_name, check_func in self.health_checks.items():
                    try:
                        check_func()
                    except Exception as e:
                        self.error_handler.handle_error(
                            component="system_monitor",
                            error_type="health_check_failed",
                            severity=ErrorSeverity.MEDIUM,
                            message=f"Health check failed: {check_name}",
                            exception=e
                        )
                
                # Sleep until next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                time.sleep(self.check_interval)
    
    def _check_memory_usage(self):
        """Check system memory usage."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            
            if memory.percent > 90:
                self.error_handler.handle_error(
                    component="system",
                    error_type="high_memory_usage",
                    severity=ErrorSeverity.HIGH,
                    message=f"Memory usage critical: {memory.percent:.1f}%",
                    context={"memory_percent": memory.percent}
                )
            elif memory.percent > 80:
                self.error_handler.handle_error(
                    component="system",
                    error_type="elevated_memory_usage",
                    severity=ErrorSeverity.MEDIUM,
                    message=f"Memory usage elevated: {memory.percent:.1f}%",
                    context={"memory_percent": memory.percent}
                )
        except ImportError:
            # psutil not available, skip check
            pass
        except Exception as e:
            logger.debug(f"Memory check failed: {e}")
    
    def _check_disk_space(self):
        """Check available disk space."""
        try:
            import shutil
            total, used, free = shutil.disk_usage(".")
            free_percent = (free / total) * 100
            
            if free_percent < 5:
                self.error_handler.handle_error(
                    component="system",
                    error_type="low_disk_space",
                    severity=ErrorSeverity.HIGH,
                    message=f"Disk space critical: {free_percent:.1f}% free",
                    context={"free_percent": free_percent}
                )
        except Exception as e:
            logger.debug(f"Disk space check failed: {e}")
    
    def _check_process_health(self):
        """Check process health indicators."""
        try:
            # Basic process health check
            import threading
            active_threads = threading.active_count()
            
            if active_threads > 50:  # Arbitrary threshold
                self.error_handler.handle_error(
                    component="system",
                    error_type="excessive_threads",
                    severity=ErrorSeverity.MEDIUM,
                    message=f"High thread count: {active_threads}",
                    context={"thread_count": active_threads}
                )
        except Exception as e:
            logger.debug(f"Process health check failed: {e}")
    
    def _check_system_load(self):
        """Check system load average."""
        try:
            import os
            if hasattr(os, 'getloadavg'):
                load1, load5, load15 = os.getloadavg()
                
                if load1 > 4.0:  # High load for single-core Pi
                    self.error_handler.handle_error(
                        component="system",
                        error_type="high_system_load",
                        severity=ErrorSeverity.MEDIUM,
                        message=f"High system load: {load1:.2f}",
                        context={"load_1min": load1}
                    )
        except Exception as e:
            logger.debug(f"System load check failed: {e}")

class ErrorHandler:
    """Central error handling and recovery coordination."""
    
    def __init__(self):
        self.error_history: List[ErrorEvent] = []
        self.error_counters: Dict[str, ErrorCounter] = {}
        self.fallback_manager = FallbackManager()
        self.system_monitor = SystemMonitor(self)
        self.system_state = SystemState.NORMAL
        self.error_callbacks: List[Callable[[ErrorEvent], None]] = []
        
        # Configuration
        self.max_history_size = 1000
        self.auto_recovery_enabled = True
        
        # Lock for thread safety
        self.lock = threading.Lock()
    
    def add_error_callback(self, callback: Callable[[ErrorEvent], None]):
        """Add callback to be called when errors occur."""
        self.error_callbacks.append(callback)
    
    def handle_error(self, component: str, error_type: str, severity: ErrorSeverity,
                    message: str, exception: Optional[Exception] = None,
                    context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle an error event and coordinate recovery."""
        
        # Create error event
        error_event = ErrorEvent(
            timestamp=datetime.now(),
            component=component,
            error_type=error_type,
            severity=severity,
            message=message,
            exception=exception,
            context=context or {}
        )
        
        # Thread-safe error handling
        with self.lock:
            # Add to history
            self.error_history.append(error_event)
            
            # Trim history if needed
            if len(self.error_history) > self.max_history_size:
                self.error_history = self.error_history[-self.max_history_size:]
            
            # Update error counter
            counter_key = f"{component}:{error_type}"
            if counter_key not in self.error_counters:
                self.error_counters[counter_key] = ErrorCounter()
            
            threshold_exceeded = self.error_counters[counter_key].add_error()
        
        # Log error
        log_message = f"Error in {component}: {message}"
        if exception:
            log_message += f" ({type(exception).__name__}: {exception})"
        
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        # Call error callbacks
        for callback in self.error_callbacks:
            try:
                callback(error_event)
            except Exception as e:
                logger.error(f"Error callback failed: {e}")
        
        # Determine if recovery action needed
        recovery_triggered = False
        
        if self.auto_recovery_enabled:
            if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] or threshold_exceeded:
                recovery_triggered = self._trigger_recovery(error_event, threshold_exceeded)
        
        return recovery_triggered
    
    def _trigger_recovery(self, error_event: ErrorEvent, threshold_exceeded: bool) -> bool:
        """Trigger recovery actions for an error."""
        logger.info(f"Triggering recovery for {error_event.component} error")
        
        try:
            # Update system state based on severity
            if error_event.severity == ErrorSeverity.CRITICAL:
                self.system_state = SystemState.EMERGENCY
            elif error_event.severity == ErrorSeverity.HIGH or threshold_exceeded:
                self.system_state = SystemState.SAFE_MODE
            elif self.system_state == SystemState.NORMAL:
                self.system_state = SystemState.DEGRADED
            
            logger.info(f"System state changed to: {self.system_state.value}")
            
            # Trigger component-specific fallback
            fallback_success = self.fallback_manager.trigger_fallback(
                error_event.component, error_event
            )
            
            if fallback_success:
                error_event.resolved = True
                error_event.resolution_time = datetime.now()
                logger.info(f"Recovery successful for {error_event.component}")
            else:
                logger.error(f"Recovery failed for {error_event.component}")
            
            return fallback_success
            
        except Exception as e:
            logger.error(f"Recovery trigger failed: {e}")
            return False
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors and system health."""
        with self.lock:
            recent_errors = [
                err for err in self.error_history
                if err.timestamp > datetime.now() - timedelta(hours=1)
            ]
            
            error_counts = {}
            for error in recent_errors:
                key = f"{error.component}:{error.error_type}"
                error_counts[key] = error_counts.get(key, 0) + 1
            
            return {
                "system_state": self.system_state.value,
                "total_errors": len(self.error_history),
                "recent_errors": len(recent_errors),
                "error_counts": error_counts,
                "fallback_states": self.fallback_manager.fallback_states,
                "last_error": self.error_history[-1].message if self.error_history else None
            }
    
    def reset_system_state(self):
        """Reset system to normal state (manual recovery)."""
        with self.lock:
            self.system_state = SystemState.NORMAL
            self.fallback_manager.fallback_states.clear()
            
            # Reset error counters
            for counter in self.error_counters.values():
                counter.reset()
        
        logger.info("System state reset to normal")
    
    def start_monitoring(self):
        """Start system health monitoring."""
        self.system_monitor.start_monitoring()
    
    def stop_monitoring(self):
        """Stop system health monitoring."""
        self.system_monitor.stop_monitoring()

# Global error handler instance
global_error_handler = ErrorHandler()

def handle_error(component: str, error_type: str, severity: ErrorSeverity,
                message: str, exception: Optional[Exception] = None,
                context: Optional[Dict[str, Any]] = None) -> bool:
    """Convenience function for global error handling."""
    return global_error_handler.handle_error(
        component, error_type, severity, message, exception, context
    )

# Test functions
def test_error_handling():
    """Test error handling functionality."""
    print("Testing Error Handling System...")
    
    # Create test error handler
    error_handler = ErrorHandler()
    
    # Test error counter
    counter = ErrorCounter(threshold=3, window_minutes=1)
    
    # Add errors
    for i in range(5):
        exceeded = counter.add_error()
        print(f"  Error {i+1}: threshold exceeded = {exceeded}")
    
    assert counter.get_count() == 5, "Should count all errors"
    
    # Test error handling
    error_events = []
    def test_callback(error_event):
        error_events.append(error_event)
    
    error_handler.add_error_callback(test_callback)
    
    # Generate test errors
    error_handler.handle_error(
        component="test_component",
        error_type="test_error",
        severity=ErrorSeverity.MEDIUM,
        message="Test error message"
    )
    
    assert len(error_events) == 1, "Should trigger callback"
    assert len(error_handler.error_history) == 1, "Should record error"
    
    # Test error summary
    summary = error_handler.get_error_summary()
    assert summary["total_errors"] == 1, "Should count errors"
    
    print("✅ Error handling tests passed")

if __name__ == "__main__":
    test_error_handling()
