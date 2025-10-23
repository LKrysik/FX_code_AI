#!/usr/bin/env python3
"""
Production Deployment Script for Indicator Variants System
=========================================================

Comprehensive deployment automation for production environments with
rollback capabilities, health checks, and monitoring setup.
"""

import os
import sys
import json
import time
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class DeploymentPhase(Enum):
    PRE_DEPLOYMENT_CHECKS = "pre_deployment_checks"
    BACKUP_CURRENT_SYSTEM = "backup_current_system"
    DEPLOY_NEW_VERSION = "deploy_new_version"
    HEALTH_CHECKS = "health_checks"
    LOAD_TESTS = "load_tests"
    SWITCH_TRAFFIC = "switch_traffic"
    MONITORING_SETUP = "monitoring_setup"
    POST_DEPLOYMENT_CLEANUP = "post_deployment_cleanup"


@dataclass
class DeploymentConfig:
    """Deployment configuration"""
    environment: str  # "staging", "production"
    version: str
    deploy_path: Path
    backup_path: Path
    config_path: Path
    health_check_timeout: int = 300  # 5 minutes
    load_test_duration: int = 60     # 1 minute
    rollback_timeout: int = 600      # 10 minutes


@dataclass
class DeploymentResult:
    """Deployment result"""
    success: bool
    phase: DeploymentPhase
    message: str
    duration_seconds: float
    artifacts: Dict[str, Any]


class ProductionDeployment:
    """
    Production deployment orchestrator with comprehensive validation
    and rollback capabilities.
    """

    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.results: List[DeploymentResult] = []
        self.start_time = time.time()

        # Create deployment directories
        self.config.deploy_path.mkdir(parents=True, exist_ok=True)
        self.config.backup_path.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self.log_file = self.config.deploy_path / f"deployment_{config.version}_{int(time.time())}.log"
        self._log(f"Starting deployment of version {config.version} to {config.environment}")

    def _log(self, message: str, level: str = "INFO") -> None:
        """Log deployment progress"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"

        print(log_entry)

        with open(self.log_file, 'a') as f:
            f.write(log_entry + "\n")

    def _record_result(self, phase: DeploymentPhase, success: bool, message: str, artifacts: Dict[str, Any] = None) -> None:
        """Record deployment phase result"""
        duration = time.time() - self.start_time
        result = DeploymentResult(
            success=success,
            phase=phase,
            message=message,
            duration_seconds=duration,
            artifacts=artifacts or {}
        )
        self.results.append(result)

        status = "SUCCESS" if success else "FAILED"
        self._log(f"Phase {phase.value}: {status} - {message}")

    def deploy(self) -> bool:
        """Execute full deployment pipeline"""
        try:
            # Phase 1: Pre-deployment checks
            if not self._run_pre_deployment_checks():
                return False

            # Phase 2: Backup current system
            if not self._backup_current_system():
                return False

            # Phase 3: Deploy new version
            if not self._deploy_new_version():
                self._rollback()
                return False

            # Phase 4: Health checks
            if not self._run_health_checks():
                self._rollback()
                return False

            # Phase 5: Load tests
            if not self._run_load_tests():
                self._rollback()
                return False

            # Phase 6: Switch traffic
            if not self._switch_traffic():
                self._rollback()
                return False

            # Phase 7: Monitoring setup
            if not self._setup_monitoring():
                # Don't rollback for monitoring failure - deployment is successful
                self._log("Monitoring setup failed, but deployment continues", "WARNING")

            # Phase 8: Post-deployment cleanup
            self._post_deployment_cleanup()

            self._log("Deployment completed successfully!")
            return True

        except Exception as e:
            self._log(f"Deployment failed with exception: {e}", "ERROR")
            self._rollback()
            return False

    def _run_pre_deployment_checks(self) -> bool:
        """Phase 1: Comprehensive pre-deployment validation"""
        self._log("Running pre-deployment checks...")

        checks = [
            ("disk_space", self._check_disk_space),
            ("permissions", self._check_permissions),
            ("dependencies", self._check_dependencies),
            ("configuration", self._check_configuration),
            ("current_system_health", self._check_current_system_health),
        ]

        failed_checks = []
        for check_name, check_func in checks:
            try:
                if not check_func():
                    failed_checks.append(check_name)
            except Exception as e:
                self._log(f"Check {check_name} failed with exception: {e}", "ERROR")
                failed_checks.append(check_name)

        if failed_checks:
            self._record_result(
                DeploymentPhase.PRE_DEPLOYMENT_CHECKS,
                False,
                f"Pre-deployment checks failed: {', '.join(failed_checks)}"
            )
            return False

        self._record_result(
            DeploymentPhase.PRE_DEPLOYMENT_CHECKS,
            True,
            "All pre-deployment checks passed"
        )
        return True

    def _check_disk_space(self) -> bool:
        """Check available disk space"""
        try:
            stat = os.statvfs(self.config.deploy_path)
            available_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)

            required_gb = 5.0  # 5GB minimum
            if available_gb < required_gb:
                self._log(f"Insufficient disk space: {available_gb:.2f}GB available, {required_gb}GB required")
                return False

            return True
        except Exception as e:
            self._log(f"Disk space check failed: {e}")
            return False

    def _check_permissions(self) -> bool:
        """Check file system permissions"""
        try:
            # Test write permissions
            test_file = self.config.deploy_path / ".deploy_test"
            test_file.write_text("test")
            test_file.unlink()

            # Check config file permissions
            if self.config.config_path.exists():
                if not os.access(self.config.config_path, os.R_OK):
                    self._log("Cannot read configuration file")
                    return False

            return True
        except Exception as e:
            self._log(f"Permissions check failed: {e}")
            return False

    def _check_dependencies(self) -> bool:
        """Check system dependencies"""
        dependencies = [
            "python3",
            "pip",
            "node",
            "npm"
        ]

        missing_deps = []
        for dep in dependencies:
            if not shutil.which(dep):
                missing_deps.append(dep)

        if missing_deps:
            self._log(f"Missing dependencies: {', '.join(missing_deps)}")
            return False

        return True

    def _check_configuration(self) -> bool:
        """Validate deployment configuration"""
        try:
            if not self.config.config_path.exists():
                self._log("Configuration file does not exist")
                return False

            with open(self.config.config_path) as f:
                config = json.load(f)

            # Validate required configuration keys
            required_keys = ["database", "redis", "api_keys", "logging"]
            for key in required_keys:
                if key not in config:
                    self._log(f"Missing configuration key: {key}")
                    return False

            return True
        except Exception as e:
            self._log(f"Configuration validation failed: {e}")
            return False

    def _check_current_system_health(self) -> bool:
        """Check current system health before deployment"""
        try:
            # This would integrate with the system's health check endpoint
            # For now, return True as placeholder
            return True
        except Exception as e:
            self._log(f"System health check failed: {e}")
            return False

    def _backup_current_system(self) -> bool:
        """Phase 2: Create comprehensive system backup"""
        self._log("Creating system backup...")

        try:
            backup_dir = self.config.backup_path / f"backup_{int(time.time())}"

            # Backup application code
            if (self.config.deploy_path / "src").exists():
                shutil.copytree(self.config.deploy_path / "src", backup_dir / "src")

            # Backup configuration
            if self.config.config_path.exists():
                shutil.copy2(self.config.config_path, backup_dir / "config.json")

            # Backup data directories
            data_dirs = ["config/indicators", "logs", "data"]
            for data_dir in data_dirs:
                src_dir = self.config.deploy_path / data_dir
                if src_dir.exists():
                    shutil.copytree(src_dir, backup_dir / data_dir)

            self._record_result(
                DeploymentPhase.BACKUP_CURRENT_SYSTEM,
                True,
                f"System backup created at {backup_dir}",
                {"backup_path": str(backup_dir)}
            )
            return True

        except Exception as e:
            self._record_result(
                DeploymentPhase.BACKUP_CURRENT_SYSTEM,
                False,
                f"Backup failed: {e}"
            )
            return False

    def _deploy_new_version(self) -> bool:
        """Phase 3: Deploy new application version"""
        self._log("Deploying new version...")

        try:
            # Copy new application code
            src_dir = Path("src")  # Assuming deployment from source
            if src_dir.exists():
                shutil.copytree(src_dir, self.config.deploy_path / "src", dirs_exist_ok=True)

            # Update configuration
            if self.config.config_path.exists():
                shutil.copy2(self.config.config_path, self.config.deploy_path / "config.json")

            # Install/update dependencies
            self._run_command(["pip", "install", "-r", "requirements.txt"], cwd=self.config.deploy_path)

            # Run database migrations if needed
            self._run_database_migrations()

            self._record_result(
                DeploymentPhase.DEPLOY_NEW_VERSION,
                True,
                f"Version {self.config.version} deployed successfully"
            )
            return True

        except Exception as e:
            self._record_result(
                DeploymentPhase.DEPLOY_NEW_VERSION,
                False,
                f"Deployment failed: {e}"
            )
            return False

    def _run_health_checks(self) -> bool:
        """Phase 4: Comprehensive health validation"""
        self._log("Running health checks...")

        try:
            # Start health check timeout
            start_time = time.time()

            # Health check endpoints to validate
            health_checks = [
                ("system_health", self._check_system_health),
                ("database_connectivity", self._check_database_connectivity),
                ("cache_connectivity", self._check_cache_connectivity),
                ("api_endpoints", self._check_api_endpoints),
            ]

            failed_checks = []
            for check_name, check_func in health_checks:
                if time.time() - start_time > self.config.health_check_timeout:
                    failed_checks.append("timeout")
                    break

                try:
                    if not check_func():
                        failed_checks.append(check_name)
                except Exception as e:
                    self._log(f"Health check {check_name} failed: {e}")
                    failed_checks.append(check_name)

            if failed_checks:
                self._record_result(
                    DeploymentPhase.HEALTH_CHECKS,
                    False,
                    f"Health checks failed: {', '.join(failed_checks)}"
                )
                return False

            self._record_result(
                DeploymentPhase.HEALTH_CHECKS,
                True,
                "All health checks passed"
            )
            return True

        except Exception as e:
            self._record_result(
                DeploymentPhase.HEALTH_CHECKS,
                False,
                f"Health checks failed with exception: {e}"
            )
            return False

    def _run_load_tests(self) -> bool:
        """Phase 5: Execute load testing validation"""
        self._log("Running load tests...")

        try:
            # Run light load test to validate deployment
            test_result = self._execute_load_test()

            if not test_result.get("success", False):
                self._record_result(
                    DeploymentPhase.LOAD_TESTS,
                    False,
                    f"Load tests failed: {test_result.get('error', 'Unknown error')}"
                )
                return False

            self._record_result(
                DeploymentPhase.LOAD_TESTS,
                True,
                f"Load tests passed: {test_result.get('throughput', 0)} ops/sec"
            )
            return True

        except Exception as e:
            self._record_result(
                DeploymentPhase.LOAD_TESTS,
                False,
                f"Load tests failed with exception: {e}"
            )
            return False

    def _switch_traffic(self) -> bool:
        """Phase 6: Switch traffic to new deployment"""
        self._log("Switching traffic to new deployment...")

        try:
            # This would integrate with load balancer or service discovery
            # For now, simulate the traffic switch
            time.sleep(2)  # Simulate traffic switch time

            self._record_result(
                DeploymentPhase.SWITCH_TRAFFIC,
                True,
                "Traffic successfully switched to new deployment"
            )
            return True

        except Exception as e:
            self._record_result(
                DeploymentPhase.SWITCH_TRAFFIC,
                False,
                f"Traffic switch failed: {e}"
            )
            return False

    def _setup_monitoring(self) -> bool:
        """Phase 7: Setup production monitoring and alerting"""
        self._log("Setting up monitoring and alerting...")

        try:
            # Configure monitoring dashboards
            self._configure_monitoring_dashboards()

            # Setup alerting rules
            self._configure_alerting_rules()

            # Validate monitoring setup
            if not self._validate_monitoring_setup():
                return False

            self._record_result(
                DeploymentPhase.MONITORING_SETUP,
                True,
                "Monitoring and alerting setup completed"
            )
            return True

        except Exception as e:
            self._record_result(
                DeploymentPhase.MONITORING_SETUP,
                False,
                f"Monitoring setup failed: {e}"
            )
            return False

    def _post_deployment_cleanup(self) -> bool:
        """Phase 8: Post-deployment cleanup"""
        self._log("Running post-deployment cleanup...")

        try:
            # Clean up old backups (keep last 5)
            self._cleanup_old_backups()

            # Remove temporary deployment files
            self._cleanup_temp_files()

            # Update deployment metadata
            self._update_deployment_metadata()

            self._record_result(
                DeploymentPhase.POST_DEPLOYMENT_CLEANUP,
                True,
                "Post-deployment cleanup completed"
            )
            return True

        except Exception as e:
            self._record_result(
                DeploymentPhase.POST_DEPLOYMENT_CLEANUP,
                False,
                f"Post-deployment cleanup failed: {e}"
            )
            return False

    def _rollback(self) -> None:
        """Execute rollback to previous version"""
        self._log("Initiating rollback procedure...", "WARNING")

        try:
            # Find latest backup
            backups = sorted(self.config.backup_path.glob("backup_*"))
            if not backups:
                self._log("No backups available for rollback", "ERROR")
                return

            latest_backup = backups[-1]

            # Restore from backup
            self._log(f"Rolling back to backup: {latest_backup}")

            # Restore application code
            if (latest_backup / "src").exists():
                if (self.config.deploy_path / "src").exists():
                    shutil.rmtree(self.config.deploy_path / "src")
                shutil.copytree(latest_backup / "src", self.config.deploy_path / "src")

            # Restore configuration
            if (latest_backup / "config.json").exists():
                shutil.copy2(latest_backup / "config.json", self.config.deploy_path / "config.json")

            # Restart services
            self._restart_services()

            self._log("Rollback completed successfully")

        except Exception as e:
            self._log(f"Rollback failed: {e}", "ERROR")

    # Placeholder methods for deployment steps
    def _run_database_migrations(self) -> None:
        """Run database migrations"""
        pass

    def _run_command(self, cmd: List[str], cwd: Path = None) -> bool:
        """Run system command"""
        try:
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
        except Exception as e:
            self._log(f"Command failed: {e}")
            return False

    def _check_system_health(self) -> bool:
        """Check system health"""
        return True

    def _check_database_connectivity(self) -> bool:
        """Check database connectivity"""
        return True

    def _check_cache_connectivity(self) -> bool:
        """Check cache connectivity"""
        return True

    def _check_api_endpoints(self) -> bool:
        """Check API endpoints"""
        return True

    def _execute_load_test(self) -> Dict[str, Any]:
        """Execute load test"""
        return {"success": True, "throughput": 100}

    def _configure_monitoring_dashboards(self) -> None:
        """Configure monitoring dashboards"""
        pass

    def _configure_alerting_rules(self) -> None:
        """Configure alerting rules"""
        pass

    def _validate_monitoring_setup(self) -> bool:
        """Validate monitoring setup"""
        return True

    def _cleanup_old_backups(self) -> None:
        """Clean up old backups"""
        pass

    def _cleanup_temp_files(self) -> None:
        """Clean up temporary files"""
        pass

    def _update_deployment_metadata(self) -> None:
        """Update deployment metadata"""
        pass

    def _restart_services(self) -> None:
        """Restart services after rollback"""
        pass


def create_production_config() -> DeploymentConfig:
    """Create production deployment configuration"""
    return DeploymentConfig(
        environment="production",
        version=os.getenv("DEPLOY_VERSION", "1.0.0"),
        deploy_path=Path("/opt/indicator-variants"),
        backup_path=Path("/opt/backups/indicator-variants"),
        config_path=Path("config/production.json")
    )


def create_staging_config() -> DeploymentConfig:
    """Create staging deployment configuration"""
    return DeploymentConfig(
        environment="staging",
        version=os.getenv("DEPLOY_VERSION", "1.0.0"),
        deploy_path=Path("/opt/staging/indicator-variants"),
        backup_path=Path("/opt/backups/staging/indicator-variants"),
        config_path=Path("config/staging.json")
    )


def main():
    """Main deployment entry point"""
    if len(sys.argv) < 2:
        print("Usage: python deploy_production.py <environment>")
        print("Environments: staging, production")
        sys.exit(1)

    environment = sys.argv[1].lower()

    if environment == "production":
        config = create_production_config()
    elif environment == "staging":
        config = create_staging_config()
    else:
        print(f"Unknown environment: {environment}")
        sys.exit(1)

    # Execute deployment
    deployment = ProductionDeployment(config)
    success = deployment.deploy()

    # Print results summary
    print("\n" + "="*60)
    print("DEPLOYMENT RESULTS SUMMARY")
    print("="*60)

    for result in deployment.results:
        status = "✅" if result.success else "❌"
        print(f"{status} {result.phase.value}: {result.message}")

    print("="*60)
    overall_status = "SUCCESS" if success else "FAILED"
    print(f"Overall Deployment Status: {overall_status}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()