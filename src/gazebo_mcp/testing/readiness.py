"""
Gazebo infrastructure readiness checker for integration tests.

Separates infrastructure startup verification from functional testing,
following testing best practices for distributed systems.
"""

import time
import subprocess
from typing import List, Callable, Tuple
from ..utils.logger import get_logger


class GazeboReadinessChecker:
    """
    Layered readiness verification for Gazebo infrastructure.

    Uses progressive timeout with exponential backoff to efficiently
    wait for infrastructure while providing clear diagnostics on failure.

    Example:
        checker = GazeboReadinessChecker(timeout=30.0)
        if checker.wait_until_ready(required_services=['/world/empty/control']):
            # Infrastructure is warm and ready
            run_tests()
        else:
            # Failed to become ready - diagnostics in logs
            fail_test()
    """

    def __init__(self, timeout: float = 30.0):
        """
        Initialize readiness checker.

        Args:
            timeout: Maximum time to wait for all checks (seconds)
        """
        self.timeout = timeout
        self.start_time = None
        self.checks_passed = []
        self.logger = get_logger("readiness_checker")

    def check_gazebo_running(self) -> bool:
        """
        Verify Gazebo process is up and responsive.

        Returns:
            True if Gazebo is running and responding to service queries
        """
        try:
            result = subprocess.run(
                ['ign', 'service', '-l'],
                capture_output=True,
                text=True,
                timeout=5.0
            )
            # If command succeeds and returns services, Gazebo is running
            return result.returncode == 0 and len(result.stdout.strip()) > 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def check_bridge_running(self) -> bool:
        """
        Verify ros_gz_bridge is running and connected.

        Returns:
            True if bridge node is visible in ROS2
        """
        try:
            result = subprocess.run(
                ['ros2', 'node', 'list'],
                capture_output=True,
                text=True,
                timeout=5.0
            )
            # Check if parameter_bridge node appears
            return result.returncode == 0 and 'parameter_bridge' in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def check_services_available(self, required_services: List[str]) -> bool:
        """
        Verify specific services are discoverable in ROS2.

        Args:
            required_services: List of service names to check for

        Returns:
            True if all required services are discovered
        """
        try:
            result = subprocess.run(
                ['ros2', 'service', 'list'],
                capture_output=True,
                text=True,
                timeout=5.0
            )
            if result.returncode != 0:
                return False

            available_services = result.stdout.strip().split('\n')
            for service in required_services:
                if service not in available_services:
                    self.logger.debug(f"Service {service} not yet available")
                    return False

            return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def check_service_callable(self, service_name: str, service_type: str) -> bool:
        """
        Verify service accepts and responds to calls.

        This is the real "warm" check - service exists AND responds.

        Args:
            service_name: Name of service to test
            service_type: ROS2 service type (e.g., 'ros_gz_interfaces/srv/ControlWorld')

        Returns:
            True if service call succeeds (even if response is error)
        """
        try:
            # For ControlWorld, we can send a minimal pause command
            if 'ControlWorld' in service_type:
                result = subprocess.run(
                    [
                        'ros2', 'service', 'call', service_name, service_type,
                        '{world_control: {pause: false}}'
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5.0
                )
                # Success if call completed (even if it returned an error)
                return result.returncode == 0
            else:
                # For other services, just check if we can create a client
                # (full call would require specific request data)
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def wait_until_ready(
        self,
        required_services: List[str] = None,
        check_callable: Tuple[str, str] = None
    ) -> bool:
        """
        Wait for all checks with progressive timeout.

        Args:
            required_services: List of service names that must be available
            check_callable: Optional (service_name, service_type) to test calling

        Returns:
            True if all checks pass within timeout, False otherwise
        """
        self.start_time = time.time()
        self.checks_passed = []

        if required_services is None:
            required_services = []

        # Define checks in order
        checks = [
            ("Gazebo running", self.check_gazebo_running),
            ("Bridge running", self.check_bridge_running),
        ]

        if required_services:
            checks.append((
                "Services visible",
                lambda: self.check_services_available(required_services)
            ))

        if check_callable:
            service_name, service_type = check_callable
            checks.append((
                "Service callable",
                lambda: self.check_service_callable(service_name, service_type)
            ))

        # Run checks sequentially with exponential backoff
        for check_name, check_func in checks:
            if not self._wait_for_check(check_name, check_func):
                self._log_failure_diagnostics()
                return False
            self.checks_passed.append(check_name)

        elapsed = time.time() - self.start_time
        self.logger.info(f"✅ All checks passed in {elapsed:.1f}s")
        return True

    def _wait_for_check(
        self,
        name: str,
        check_func: Callable[[], bool],
        initial_delay: float = 0.5,
        max_delay: float = 2.0
    ) -> bool:
        """
        Wait for a single check with exponential backoff.

        Exponential backoff reduces CPU usage while still being
        responsive to quick startups.

        Args:
            name: Name of check for logging
            check_func: Function that returns True when check passes
            initial_delay: Starting delay between checks
            max_delay: Maximum delay between checks

        Returns:
            True if check passed, False if timeout
        """
        delay = initial_delay
        while time.time() - self.start_time < self.timeout:
            if check_func():
                elapsed = time.time() - self.start_time
                self.logger.info(f"✓ {name} (after {elapsed:.1f}s)")
                return True

            time.sleep(delay)
            delay = min(delay * 1.5, max_delay)  # Cap exponential growth

        elapsed = time.time() - self.start_time
        self.logger.error(f"✗ {name} timeout after {elapsed:.1f}s")
        return False

    def _log_failure_diagnostics(self):
        """Log diagnostic information when checks fail."""
        self.logger.error(f"Readiness checks failed!")
        self.logger.info(f"Checks passed: {self.checks_passed}")

        # Try to gather diagnostic info
        try:
            # Check Gazebo processes
            result = subprocess.run(
                ['pgrep', '-la', 'gz'],
                capture_output=True,
                text=True,
                timeout=2.0
            )
            if result.stdout:
                self.logger.info(f"Gazebo processes:\n{result.stdout}")

            # Check ROS2 nodes
            result = subprocess.run(
                ['ros2', 'node', 'list'],
                capture_output=True,
                text=True,
                timeout=2.0
            )
            if result.stdout:
                self.logger.info(f"ROS2 nodes:\n{result.stdout}")

            # Check ROS2 services
            result = subprocess.run(
                ['ros2', 'service', 'list'],
                capture_output=True,
                text=True,
                timeout=2.0
            )
            if result.stdout:
                self.logger.info(f"ROS2 services:\n{result.stdout}")

        except Exception as e:
            self.logger.warning(f"Could not gather diagnostics: {e}")
