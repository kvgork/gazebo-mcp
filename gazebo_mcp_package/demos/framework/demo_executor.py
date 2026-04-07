"""Base demo executor with step management and error handling."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Callable, Optional, Dict, Any
import asyncio
import time
from enum import Enum


class StepStatus(Enum):
    """Status of a demo step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class DemoStep:
    """Represents a single demo step."""
    name: str
    active_name: str  # Present tense for display
    execute: Callable
    validate: Optional[Callable] = None
    timeout: float = 30.0
    critical: bool = True
    status: StepStatus = StepStatus.PENDING
    error: Optional[str] = None
    duration: float = 0.0


@dataclass
class StepResult:
    """Result of executing a demo step."""
    success: bool
    step_name: str
    duration: float
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@dataclass
class DemoResult:
    """Result of executing entire demo."""
    success: bool
    total_duration: float
    steps_completed: int
    steps_failed: int
    step_results: List[StepResult] = field(default_factory=list)
    error: Optional[str] = None


class DemoExecutor(ABC):
    """Base class for all demo implementations."""

    def __init__(self, name: str, description: str):
        """Initialize demo executor.

        Args:
            name: Demo name
            description: Demo description
        """
        self.name = name
        self.description = description
        self.steps: List[DemoStep] = []
        self.current_step_index: int = 0

    def register_step(
        self,
        name: str,
        active_name: str,
        execute: Callable,
        validate: Optional[Callable] = None,
        timeout: float = 30.0,
        critical: bool = True
    ) -> None:
        """Register a demo step.

        Args:
            name: Step name (imperative form, e.g., "Spawn robot")
            active_name: Present continuous form (e.g., "Spawning robot")
            execute: Async function to execute step
            validate: Optional async function to validate step result
            timeout: Maximum execution time in seconds
            critical: If True, failure stops demo; if False, continues
        """
        step = DemoStep(
            name=name,
            active_name=active_name,
            execute=execute,
            validate=validate,
            timeout=timeout,
            critical=critical
        )
        self.steps.append(step)

    async def execute_step(self, step: DemoStep) -> StepResult:
        """Execute a single demo step with timeout and validation.

        Args:
            step: Step to execute

        Returns:
            StepResult with execution details
        """
        step.status = StepStatus.IN_PROGRESS
        start_time = time.time()

        try:
            # Execute with timeout
            result_data = await asyncio.wait_for(
                step.execute(),
                timeout=step.timeout
            )

            # Validate if validator provided
            if step.validate:
                validation_result = await step.validate(result_data)
                if not validation_result:
                    raise ValueError(f"Validation failed for step: {step.name}")

            # Success
            duration = time.time() - start_time
            step.status = StepStatus.COMPLETED
            step.duration = duration

            return StepResult(
                success=True,
                step_name=step.name,
                duration=duration,
                data=result_data if isinstance(result_data, dict) else None
            )

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            step.status = StepStatus.FAILED
            step.duration = duration
            error_msg = f"Step timed out after {step.timeout}s"
            step.error = error_msg

            return StepResult(
                success=False,
                step_name=step.name,
                duration=duration,
                error=error_msg
            )

        except Exception as e:
            duration = time.time() - start_time
            step.status = StepStatus.FAILED
            step.duration = duration
            error_msg = str(e)
            step.error = error_msg

            return StepResult(
                success=False,
                step_name=step.name,
                duration=duration,
                error=error_msg
            )

    async def run(self) -> DemoResult:
        """Execute all demo steps in sequence.

        Returns:
            DemoResult with overall demo execution details
        """
        print("=" * 70)
        print(f"  {self.name}")
        print("=" * 70)
        print(f"{self.description}\n")

        start_time = time.time()
        step_results: List[StepResult] = []
        steps_completed = 0
        steps_failed = 0

        for i, step in enumerate(self.steps):
            self.current_step_index = i

            # Print step header
            print(f"[Step {i+1}/{len(self.steps)}] {step.active_name}...")

            # Execute step
            result = await self.execute_step(step)
            step_results.append(result)

            if result.success:
                steps_completed += 1
                print(f"  ✅ {step.name} (completed in {result.duration:.2f}s)")
            else:
                steps_failed += 1
                print(f"  ❌ {step.name} (failed after {result.duration:.2f}s)")
                print(f"     Error: {result.error}")

                # Stop if critical step failed
                if step.critical:
                    print(f"\n⚠️  Critical step failed. Stopping demo.\n")
                    break
                else:
                    print(f"  ⏭️  Non-critical step, continuing...\n")
                    step.status = StepStatus.SKIPPED

            print()

        # Calculate totals
        total_duration = time.time() - start_time
        overall_success = steps_failed == 0

        # Print summary
        print("=" * 70)
        print("  Demo Summary")
        print("=" * 70)
        print(f"Total Duration:    {total_duration:.2f}s")
        print(f"Steps Completed:   {steps_completed}/{len(self.steps)} ✅")
        print(f"Steps Failed:      {steps_failed}/{len(self.steps)} ❌")

        if overall_success:
            print("\n🎉 Demo completed successfully!")
        else:
            print(f"\n⚠️  Demo completed with {steps_failed} failure(s).")

        print("=" * 70)

        return DemoResult(
            success=overall_success,
            total_duration=total_duration,
            steps_completed=steps_completed,
            steps_failed=steps_failed,
            step_results=step_results
        )

    @abstractmethod
    async def setup(self) -> None:
        """Setup demo environment (must be implemented by subclass)."""
        pass

    @abstractmethod
    async def teardown(self) -> None:
        """Cleanup demo environment (must be implemented by subclass)."""
        pass

    async def run_full_demo(self) -> DemoResult:
        """Run complete demo lifecycle: setup -> run -> teardown.

        Returns:
            DemoResult from main demo execution
        """
        try:
            print("\n🔧 Setting up demo environment...\n")
            await self.setup()

            print("🚀 Starting demo execution...\n")
            result = await self.run()

            return result

        finally:
            print("\n🧹 Cleaning up demo environment...\n")
            try:
                await self.teardown()
                print("✅ Cleanup completed\n")
            except Exception as e:
                print(f"⚠️  Warning: Cleanup failed: {e}\n")
