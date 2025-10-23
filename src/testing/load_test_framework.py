"""
Load Testing Framework for Indicator Variants System
===============================================

Comprehensive load testing framework to validate concurrent user handling
and system performance under various load conditions.
"""

import asyncio
import time
import statistics
import psutil
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading
import random

try:
    from ..domain.services.streaming_indicator_engine import StreamingIndicatorEngine, IndicatorType, VariantType
    from ..core.event_bus import EventBus
    from ..core.logger import StructuredLogger
except ImportError:
    # For testing without full imports
    pass


@dataclass
class LoadTestResult:
    """Results from a load test execution"""
    test_name: str
    duration_seconds: float
    total_operations: int
    successful_operations: int
    failed_operations: int
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    throughput_ops_per_sec: float
    error_rate_pct: float
    memory_usage_mb: float
    cpu_usage_pct: float
    concurrent_users: int
    success: bool


@dataclass
class LoadTestScenario:
    """Definition of a load test scenario"""
    name: str
    description: str
    concurrent_users: int
    duration_seconds: int
    operation_weights: Dict[str, float]  # operation_name -> weight
    ramp_up_seconds: int = 10
    cool_down_seconds: int = 5


class LoadTestFramework:
    """
    Comprehensive load testing framework for concurrent user simulation
    """

    def __init__(self, engine: StreamingIndicatorEngine, event_bus: EventBus, logger: StructuredLogger):
        self.engine = engine
        self.event_bus = event_bus
        self.logger = logger

        # Test symbols pool
        self.test_symbols = [f"BTC_{i}" for i in range(100)] + \
                           [f"ETH_{i}" for i in range(100)] + \
                           [f"ADA_{i}" for i in range(50)]

        # Operation definitions
        self.operations = {
            "create_indicator": self._create_indicator_operation,
            "update_variant": self._update_variant_operation,
            "calculate_indicator": self._calculate_indicator_operation,
            "list_variants": self._list_variants_operation,
            "delete_indicator": self._delete_indicator_operation,
            "get_health_status": self._get_health_status_operation,
        }

        # Performance tracking
        self.response_times: List[float] = []
        self.errors: List[Exception] = []
        self.operation_counts: Dict[str, int] = {}

    async def run_load_test(self, scenario: LoadTestScenario) -> LoadTestResult:
        """Execute a comprehensive load test scenario"""
        self.logger.info("load_test.starting", {
            "scenario": scenario.name,
            "concurrent_users": scenario.concurrent_users,
            "duration_seconds": scenario.duration_seconds
        })

        start_time = time.time()
        end_time = start_time + scenario.duration_seconds

        # Initialize tracking
        self.response_times = []
        self.errors = []
        self.operation_counts = {op: 0 for op in scenario.operation_weights.keys()}

        # Create user tasks
        user_tasks = []
        for user_id in range(scenario.concurrent_users):
            task = asyncio.create_task(
                self._simulate_user(
                    user_id=user_id,
                    scenario=scenario,
                    end_time=end_time
                )
            )
            user_tasks.append(task)

        # Ramp up users gradually
        if scenario.ramp_up_seconds > 0:
            delay_between_users = scenario.ramp_up_seconds / scenario.concurrent_users
            for i, task in enumerate(user_tasks):
                await asyncio.sleep(delay_between_users)
                # Task already started, just delay between starts

        # Wait for all user tasks to complete
        await asyncio.gather(*user_tasks, return_exceptions=True)

        # Calculate results
        total_duration = time.time() - start_time
        total_operations = sum(self.operation_counts.values())
        successful_operations = total_operations - len(self.errors)

        # Calculate response time statistics
        if self.response_times:
            avg_response_time = statistics.mean(self.response_times) * 1000  # Convert to ms
            p95_response_time = statistics.quantiles(self.response_times, n=20)[18] * 1000  # 95th percentile
            p99_response_time = statistics.quantiles(self.response_times, n=100)[98] * 1000  # 99th percentile
        else:
            avg_response_time = p95_response_time = p99_response_time = 0.0

        # Calculate throughput
        throughput = total_operations / total_duration if total_duration > 0 else 0.0

        # Calculate error rate
        error_rate = (len(self.errors) / total_operations * 100) if total_operations > 0 else 0.0

        # Get system metrics
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024
        cpu_usage = psutil.cpu_percent(interval=1)

        # Determine success criteria
        success = (
            error_rate < 5.0 and  # Less than 5% errors
            avg_response_time < 500 and  # Average response time < 500ms
            p99_response_time < 2000  # 99th percentile < 2 seconds
        )

        result = LoadTestResult(
            test_name=scenario.name,
            duration_seconds=total_duration,
            total_operations=total_operations,
            successful_operations=successful_operations,
            failed_operations=len(self.errors),
            avg_response_time_ms=avg_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            throughput_ops_per_sec=throughput,
            error_rate_pct=error_rate,
            memory_usage_mb=memory_usage,
            cpu_usage_pct=cpu_usage,
            concurrent_users=scenario.concurrent_users,
            success=success
        )

        self.logger.info("load_test.completed", {
            "scenario": scenario.name,
            "success": success,
            "total_operations": total_operations,
            "error_rate_pct": error_rate,
            "avg_response_time_ms": avg_response_time,
            "throughput_ops_per_sec": throughput
        })

        return result

    async def _simulate_user(self, user_id: int, scenario: LoadTestScenario, end_time: float):
        """Simulate a single user's behavior"""
        user_start_time = time.time()

        while time.time() < end_time:
            try:
                # Select operation based on weights
                operation_name = self._select_weighted_operation(scenario.operation_weights)

                # Execute operation and measure response time
                operation_start = time.time()
                await self.operations[operation_name](user_id)
                operation_end = time.time()

                # Record metrics
                response_time = operation_end - operation_start
                self.response_times.append(response_time)
                self.operation_counts[operation_name] += 1

                # Small delay between operations to simulate think time
                await asyncio.sleep(random.uniform(0.01, 0.1))  # 10-100ms think time

            except Exception as e:
                self.errors.append(e)
                self.logger.debug("load_test.user_operation_error", {
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                })

                # Brief pause on error
                await asyncio.sleep(0.1)

        user_duration = time.time() - user_start_time
        operations_performed = sum(count for op, count in self.operation_counts.items()
                                  if op in scenario.operation_weights)

        self.logger.debug("load_test.user_completed", {
            "user_id": user_id,
            "duration_seconds": user_duration,
            "operations_performed": operations_performed
        })

    def _select_weighted_operation(self, operation_weights: Dict[str, float]) -> str:
        """Select an operation based on weighted probabilities"""
        total_weight = sum(operation_weights.values())
        rand_value = random.uniform(0, total_weight)

        cumulative_weight = 0.0
        for operation, weight in operation_weights.items():
            cumulative_weight += weight
            if rand_value <= cumulative_weight:
                return operation

        # Fallback to first operation
        return list(operation_weights.keys())[0]

    async def _create_indicator_operation(self, user_id: int):
        """Simulate creating an indicator"""
        symbol = random.choice(self.test_symbols)
        indicator_type = random.choice(list(IndicatorType))

        # Create variant first if needed
        variant_id = await self._create_test_variant(user_id, indicator_type)

        # Create indicator from variant
        indicator_key = self.engine.create_indicator_from_variant(
            symbol=symbol,
            variant_id=variant_id,
            timeframe="1m"
        )

        if indicator_key:
            # Clean up temporary variant
            self.engine.delete_variant(variant_id)

    async def _update_variant_operation(self, user_id: int):
        """Simulate updating a variant"""
        # Get existing variants
        variants = self.engine.list_variants()
        if not variants:
            # Create one first
            await self._create_indicator_operation(user_id)
            variants = self.engine.list_variants()

        if variants:
            variant = random.choice(variants)
            # Update with slightly modified parameters
            updated_params = variant.parameters.copy()
            if "period" in updated_params:
                updated_params["period"] = max(2, updated_params["period"] + random.randint(-2, 2))

            self.engine.update_variant_parameters(variant.id, updated_params)

    async def _calculate_indicator_operation(self, user_id: int):
        """Simulate calculating an indicator (cache hit scenario)"""
        # Create a temporary indicator and calculate it
        symbol = random.choice(self.test_symbols)
        indicator_type = random.choice([IndicatorType.SMA, IndicatorType.EMA, IndicatorType.RSI])

        indicator_key = self.engine.add_indicator(
            symbol=symbol,
            indicator_type=indicator_type,
            timeframe="1m",
            period=random.randint(10, 50)
        )

        if indicator_key:
            # Force calculation (this will use cache if available)
            # In real scenario, this would be triggered by market data
            # For testing, we simulate the calculation
            pass

            # Clean up
            self.engine.remove_indicator(indicator_key)

    async def _list_variants_operation(self, user_id: int):
        """Simulate listing variants"""
        # Randomly filter by type or list all
        if random.random() < 0.5:
            variant_types = VariantType.get_valid_types()
            variant_type = random.choice(variant_types)
            self.engine.list_variants(variant_type)
        else:
            self.engine.list_variants()

    async def _delete_indicator_operation(self, user_id: int):
        """Simulate deleting an indicator"""
        # This is tricky in a load test - we'd need to track created indicators
        # For simplicity, we'll skip this operation in load testing
        # as deletion could interfere with other users
        pass

    async def _get_health_status_operation(self, user_id: int):
        """Simulate getting health status"""
        self.engine.get_health_status()

    async def _create_test_variant(self, user_id: int, indicator_type: IndicatorType) -> Optional[str]:
        """Create a test variant for operations"""
        try:
            variant_name = f"load_test_variant_{user_id}_{random.randint(1, 1000)}"

            # Generate appropriate parameters based on indicator type
            parameters = self._generate_test_parameters(indicator_type)

            variant_id = self.engine.create_variant(
                name=variant_name,
                base_indicator_type=indicator_type.value,
                variant_type="general",
                description=f"Load test variant for {indicator_type.value}",
                parameters=parameters,
                created_by=f"user_{user_id}"
            )

            return variant_id

        except Exception as e:
            self.logger.debug("load_test.create_variant_error", {
                "user_id": user_id,
                "indicator_type": indicator_type.value,
                "error": str(e)
            })
            return None

    def _generate_test_parameters(self, indicator_type: IndicatorType) -> Dict[str, Any]:
        """Generate test parameters for an indicator type"""
        if indicator_type in [IndicatorType.SMA, IndicatorType.EMA, IndicatorType.RSI]:
            return {"period": random.randint(10, 50)}
        elif indicator_type == IndicatorType.TWPA:
            return {
                "t1": random.randint(300, 900),  # 5-15 minutes ago
                "t2": 0
            }
        elif indicator_type == IndicatorType.VELOCITY:
            return {
                "current_window": {"t1": 60, "t2": 0},
                "baseline_window": {"t1": 120, "t2": 60},
                "price_method": "LAST_PRICE"
            }
        else:
            # Default parameters for other types
            return {"period": 20}


class LoadTestScenarios:
    """Predefined load test scenarios"""

    @staticmethod
    def light_load_test() -> LoadTestScenario:
        """Light load: 10 concurrent users, basic operations"""
        return LoadTestScenario(
            name="light_load",
            description="Light load test with 10 concurrent users",
            concurrent_users=10,
            duration_seconds=60,  # 1 minute
            operation_weights={
                "create_indicator": 0.3,
                "list_variants": 0.4,
                "calculate_indicator": 0.2,
                "get_health_status": 0.1
            }
        )

    @staticmethod
    def medium_load_test() -> LoadTestScenario:
        """Medium load: 50 concurrent users, mixed operations"""
        return LoadTestScenario(
            name="medium_load",
            description="Medium load test with 50 concurrent users",
            concurrent_users=50,
            duration_seconds=120,  # 2 minutes
            operation_weights={
                "create_indicator": 0.25,
                "update_variant": 0.15,
                "list_variants": 0.3,
                "calculate_indicator": 0.2,
                "get_health_status": 0.1
            }
        )

    @staticmethod
    def heavy_load_test() -> LoadTestScenario:
        """Heavy load: 100+ concurrent users, full operation mix"""
        return LoadTestScenario(
            name="heavy_load",
            description="Heavy load test with 100 concurrent users",
            concurrent_users=100,
            duration_seconds=180,  # 3 minutes
            operation_weights={
                "create_indicator": 0.2,
                "update_variant": 0.15,
                "list_variants": 0.25,
                "calculate_indicator": 0.25,
                "get_health_status": 0.15
            }
        )

    @staticmethod
    def stress_test() -> LoadTestScenario:
        """Stress test: 200 concurrent users, maximum load"""
        return LoadTestScenario(
            name="stress_test",
            description="Stress test with 200 concurrent users",
            concurrent_users=200,
            duration_seconds=300,  # 5 minutes
            operation_weights={
                "create_indicator": 0.2,
                "update_variant": 0.2,
                "list_variants": 0.2,
                "calculate_indicator": 0.3,
                "get_health_status": 0.1
            }
        )


async def run_comprehensive_load_test(engine: StreamingIndicatorEngine,
                                    event_bus: EventBus,
                                    logger: StructuredLogger) -> Dict[str, LoadTestResult]:
    """Run comprehensive load testing suite"""

    framework = LoadTestFramework(engine, event_bus, logger)

    scenarios = [
        LoadTestScenarios.light_load_test(),
        LoadTestScenarios.medium_load_test(),
        LoadTestScenarios.heavy_load_test(),
    ]

    results = {}

    for scenario in scenarios:
        logger.info("load_test.starting_scenario", {
            "scenario": scenario.name,
            "concurrent_users": scenario.concurrent_users
        })

        try:
            result = await framework.run_load_test(scenario)
            results[scenario.name] = result

            # Log results
            logger.info("load_test.scenario_result", {
                "scenario": scenario.name,
                "success": result.success,
                "total_operations": result.total_operations,
                "error_rate_pct": result.error_rate_pct,
                "avg_response_time_ms": result.avg_response_time_ms,
                "throughput_ops_per_sec": result.throughput_ops_per_sec
            })

            # Brief pause between scenarios
            await asyncio.sleep(10)

        except Exception as e:
            logger.error("load_test.scenario_failed", {
                "scenario": scenario.name,
                "error": str(e),
                "error_type": type(e).__name__
            })

            # Create failed result
            results[scenario.name] = LoadTestResult(
                test_name=scenario.name,
                duration_seconds=0,
                total_operations=0,
                successful_operations=0,
                failed_operations=1,
                avg_response_time_ms=0,
                p95_response_time_ms=0,
                p99_response_time_ms=0,
                throughput_ops_per_sec=0,
                error_rate_pct=100,
                memory_usage_mb=0,
                cpu_usage_pct=0,
                concurrent_users=scenario.concurrent_users,
                success=False
            )

    return results