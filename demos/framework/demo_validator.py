"""Environment validation utilities for demos."""
import os
import subprocess
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of an environment validation check."""
    passed: bool
    component: str
    message: str
    details: Optional[str] = None


class DemoValidator:
    """Validates demo environment setup and dependencies."""

    @staticmethod
    def check_command_exists(command: str) -> ValidationResult:
        """Check if a command is available in PATH.

        Args:
            command: Command to check

        Returns:
            ValidationResult indicating if command exists
        """
        try:
            result = subprocess.run(
                ["which", command],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                path = result.stdout.strip()
                return ValidationResult(
                    passed=True,
                    component=command,
                    message=f"Found {command}",
                    details=f"Path: {path}"
                )
            else:
                return ValidationResult(
                    passed=False,
                    component=command,
                    message=f"{command} not found in PATH",
                    details="Please install required package"
                )

        except Exception as e:
            return ValidationResult(
                passed=False,
                component=command,
                message=f"Failed to check {command}",
                details=str(e)
            )

    @staticmethod
    def check_ros2_package(package_name: str) -> ValidationResult:
        """Check if a ROS2 package is installed.

        Args:
            package_name: ROS2 package name

        Returns:
            ValidationResult indicating if package is available
        """
        try:
            result = subprocess.run(
                ["ros2", "pkg", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                packages = result.stdout.split('\n')
                if package_name in packages:
                    return ValidationResult(
                        passed=True,
                        component=package_name,
                        message=f"ROS2 package {package_name} found"
                    )
                else:
                    return ValidationResult(
                        passed=False,
                        component=package_name,
                        message=f"ROS2 package {package_name} not found",
                        details="Please install with: sudo apt install ros-humble-<package>"
                    )
            else:
                return ValidationResult(
                    passed=False,
                    component="ros2",
                    message="Failed to list ROS2 packages",
                    details=result.stderr
                )

        except Exception as e:
            return ValidationResult(
                passed=False,
                component=package_name,
                message=f"Failed to check ROS2 package {package_name}",
                details=str(e)
            )

    @staticmethod
    def check_file_exists(file_path: str, description: str = "") -> ValidationResult:
        """Check if a file exists.

        Args:
            file_path: Path to file
            description: Human-readable description

        Returns:
            ValidationResult indicating if file exists
        """
        display_name = description if description else file_path

        if os.path.isfile(file_path):
            return ValidationResult(
                passed=True,
                component=display_name,
                message=f"Found {display_name}",
                details=f"Path: {file_path}"
            )
        else:
            return ValidationResult(
                passed=False,
                component=display_name,
                message=f"{display_name} not found",
                details=f"Expected path: {file_path}"
            )

    @staticmethod
    def check_directory_exists(dir_path: str, description: str = "") -> ValidationResult:
        """Check if a directory exists.

        Args:
            dir_path: Path to directory
            description: Human-readable description

        Returns:
            ValidationResult indicating if directory exists
        """
        display_name = description if description else dir_path

        if os.path.isdir(dir_path):
            return ValidationResult(
                passed=True,
                component=display_name,
                message=f"Found {display_name}",
                details=f"Path: {dir_path}"
            )
        else:
            return ValidationResult(
                passed=False,
                component=display_name,
                message=f"{display_name} not found",
                details=f"Expected path: {dir_path}"
            )

    @staticmethod
    def check_environment_variable(var_name: str, expected_value: Optional[str] = None) -> ValidationResult:
        """Check if an environment variable is set.

        Args:
            var_name: Environment variable name
            expected_value: Optional expected value

        Returns:
            ValidationResult indicating if variable is set correctly
        """
        value = os.environ.get(var_name)

        if value is None:
            return ValidationResult(
                passed=False,
                component=var_name,
                message=f"Environment variable {var_name} not set",
                details=f"Please export {var_name}"
            )

        if expected_value is not None and value != expected_value:
            return ValidationResult(
                passed=False,
                component=var_name,
                message=f"Environment variable {var_name} has wrong value",
                details=f"Expected: {expected_value}, Got: {value}"
            )

        return ValidationResult(
            passed=True,
            component=var_name,
            message=f"Environment variable {var_name} is set",
            details=f"Value: {value}"
        )

    @staticmethod
    def check_gazebo_process() -> ValidationResult:
        """Check if Gazebo is running.

        Returns:
            ValidationResult indicating if Gazebo process is active
        """
        try:
            # Check for Modern Gazebo (ign gazebo or gz sim)
            result = subprocess.run(
                ["pgrep", "-f", "gz sim|ign gazebo"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                return ValidationResult(
                    passed=True,
                    component="Gazebo",
                    message="Gazebo is running",
                    details=f"PIDs: {', '.join(pids)}"
                )
            else:
                return ValidationResult(
                    passed=False,
                    component="Gazebo",
                    message="Gazebo is not running",
                    details="Please start Gazebo: gz sim <world.sdf>"
                )

        except Exception as e:
            return ValidationResult(
                passed=False,
                component="Gazebo",
                message="Failed to check Gazebo process",
                details=str(e)
            )

    @staticmethod
    def validate_demo_environment(checks: List[Tuple[str, callable]]) -> Tuple[bool, List[ValidationResult]]:
        """Run multiple validation checks.

        Args:
            checks: List of (description, check_function) tuples

        Returns:
            Tuple of (all_passed, results_list)
        """
        results: List[ValidationResult] = []
        all_passed = True

        print("=" * 70)
        print("  Environment Validation")
        print("=" * 70)
        print()

        for description, check_func in checks:
            result = check_func()
            results.append(result)

            status = "✅" if result.passed else "❌"
            print(f"{status} {result.component}: {result.message}")
            if result.details:
                print(f"   └─ {result.details}")

            if not result.passed:
                all_passed = False

        print()
        print("=" * 70)

        if all_passed:
            print("✅ All validation checks passed!")
        else:
            print("❌ Some validation checks failed. Please fix issues above.")

        print("=" * 70)
        print()

        return all_passed, results
