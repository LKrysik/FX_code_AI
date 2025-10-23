#!/usr/bin/env python3
"""
Monitoring and Alerting Setup for Indicator Variants System
==========================================================

Automated setup of comprehensive monitoring, alerting, and observability
for production deployments.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List
import subprocess


class MonitoringSetup:
    """
    Comprehensive monitoring and alerting setup for production
    """

    def __init__(self, config_path: Path = None):
        self.config_path = config_path or Path("config/production.json")
        self.monitoring_dir = Path("monitoring")
        self.monitoring_dir.mkdir(exist_ok=True)

        with open(self.config_path) as f:
            self.config = json.load(f)

    def setup_monitoring(self) -> bool:
        """Setup complete monitoring stack"""
        print("Setting up comprehensive monitoring and alerting...")

        try:
            # 1. Setup Prometheus metrics
            self._setup_prometheus_metrics()

            # 2. Configure alerting rules
            self._setup_alerting_rules()

            # 3. Setup log aggregation
            self._setup_log_aggregation()

            # 4. Configure dashboards
            self._setup_dashboards()

            # 5. Setup health checks
            self._setup_health_checks()

            # 6. Configure backup monitoring
            self._setup_backup_monitoring()

            print("✅ Monitoring and alerting setup completed successfully!")
            return True

        except Exception as e:
            print(f"❌ Monitoring setup failed: {e}")
            return False

    def _setup_prometheus_metrics(self) -> None:
        """Setup Prometheus metrics collection"""
        print("Setting up Prometheus metrics...")

        # Create metrics configuration
        metrics_config = {
            "global": {
                "scrape_interval": "15s",
                "evaluation_interval": "15s"
            },
            "scrape_configs": [
                {
                    "job_name": "indicator-variants",
                    "static_configs": [
                        {
                            "targets": ["localhost:9090"]
                        }
                    ],
                    "metrics_path": "/metrics"
                }
            ]
        }

        # Write Prometheus configuration
        prometheus_config_path = self.monitoring_dir / "prometheus.yml"
        with open(prometheus_config_path, 'w') as f:
            json.dump(metrics_config, f, indent=2)

        # Create metrics exporter configuration
        metrics_exporter_config = {
            "port": self.config["monitoring"]["prometheus_port"],
            "metrics_prefix": self.config["monitoring"]["metrics_prefix"],
            "enabled_metrics": [
                "http_requests_total",
                "http_request_duration_seconds",
                "cache_hit_ratio",
                "memory_usage_bytes",
                "cpu_usage_percent",
                "indicator_calculations_total",
                "error_rate",
                "uptime_seconds"
            ]
        }

        metrics_config_path = self.monitoring_dir / "metrics_exporter.json"
        with open(metrics_config_path, 'w') as f:
            json.dump(metrics_exporter_config, f, indent=2)

        print("✅ Prometheus metrics configured")

    def _setup_alerting_rules(self) -> None:
        """Setup comprehensive alerting rules"""
        print("Setting up alerting rules...")

        alerting_rules = {
            "groups": [
                {
                    "name": "indicator_variants_alerts",
                    "rules": [
                        {
                            "alert": "HighErrorRate",
                            "expr": "rate(http_requests_total{status=~'5..'}[5m]) / rate(http_requests_total[5m]) > 0.05",
                            "for": "5m",
                            "labels": {
                                "severity": "critical"
                            },
                            "annotations": {
                                "summary": "High error rate detected",
                                "description": "Error rate is {{ $value }}% which is above 5%"
                            }
                        },
                        {
                            "alert": "LowCacheHitRatio",
                            "expr": "cache_hit_ratio < 0.8",
                            "for": "10m",
                            "labels": {
                                "severity": "warning"
                            },
                            "annotations": {
                                "summary": "Low cache hit ratio",
                                "description": "Cache hit ratio is {{ $value }}% which is below 80%"
                            }
                        },
                        {
                            "alert": "HighMemoryUsage",
                            "expr": "memory_usage_bytes / 1024 / 1024 > 450",
                            "for": "5m",
                            "labels": {
                                "severity": "warning"
                            },
                            "annotations": {
                                "summary": "High memory usage",
                                "description": "Memory usage is {{ $value }}MB which is above 450MB"
                            }
                        },
                        {
                            "alert": "HighCPUUsage",
                            "expr": "cpu_usage_percent > 80",
                            "for": "5m",
                            "labels": {
                                "severity": "warning"
                            },
                            "annotations": {
                                "summary": "High CPU usage",
                                "description": "CPU usage is {{ $value }}% which is above 80%"
                            }
                        },
                        {
                            "alert": "ServiceDown",
                            "expr": "up == 0",
                            "for": "1m",
                            "labels": {
                                "severity": "critical"
                            },
                            "annotations": {
                                "summary": "Service is down",
                                "description": "Indicator Variants service is not responding"
                            }
                        },
                        {
                            "alert": "SlowResponseTime",
                            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2.0",
                            "for": "5m",
                            "labels": {
                                "severity": "warning"
                            },
                            "annotations": {
                                "summary": "Slow response times",
                                "description": "95th percentile response time is {{ $value }}s which is above 2s"
                            }
                        }
                    ]
                }
            ]
        }

        # Write alerting rules
        alerting_rules_path = self.monitoring_dir / "alerting_rules.yml"
        with open(alerting_rules_path, 'w') as f:
            json.dump(alerting_rules, f, indent=2)

        print("✅ Alerting rules configured")

    def _setup_log_aggregation(self) -> None:
        """Setup log aggregation and analysis"""
        print("Setting up log aggregation...")

        log_config = {
            "logstash": {
                "input": {
                    "file": {
                        "path": "/var/log/indicator-variants/*.log",
                        "start_position": "beginning"
                    }
                },
                "filter": {
                    "json": {
                        "source": "message"
                    },
                    "date": {
                        "match": ["timestamp", "ISO8601"]
                    }
                },
                "output": {
                    "elasticsearch": {
                        "hosts": ["localhost:9200"],
                        "index": "indicator-variants-%{+YYYY.MM.dd}"
                    }
                }
            }
        }

        log_config_path = self.monitoring_dir / "logstash.conf"
        with open(log_config_path, 'w') as f:
            json.dump(log_config, f, indent=2)

        print("✅ Log aggregation configured")

    def _setup_dashboards(self) -> None:
        """Setup monitoring dashboards"""
        print("Setting up monitoring dashboards...")

        # Create Grafana dashboard configuration
        dashboard_config = {
            "dashboard": {
                "title": "Indicator Variants System Overview",
                "tags": ["indicator-variants", "production"],
                "timezone": "UTC",
                "panels": [
                    {
                        "title": "Request Rate",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "rate(http_requests_total[5m])",
                                "legendFormat": "Requests/sec"
                            }
                        ]
                    },
                    {
                        "title": "Error Rate",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "rate(http_requests_total{status=~'5..'}[5m]) / rate(http_requests_total[5m]) * 100",
                                "legendFormat": "Error Rate %"
                            }
                        ]
                    },
                    {
                        "title": "Response Time",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
                                "legendFormat": "95th percentile"
                            },
                            {
                                "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
                                "legendFormat": "50th percentile"
                            }
                        ]
                    },
                    {
                        "title": "Cache Performance",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "cache_hit_ratio * 100",
                                "legendFormat": "Hit Ratio %"
                            }
                        ]
                    },
                    {
                        "title": "Memory Usage",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "memory_usage_bytes / 1024 / 1024",
                                "legendFormat": "Memory Usage MB"
                            }
                        ]
                    },
                    {
                        "title": "CPU Usage",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "cpu_usage_percent",
                                "legendFormat": "CPU Usage %"
                            }
                        ]
                    }
                ]
            }
        }

        dashboard_path = self.monitoring_dir / "grafana_dashboard.json"
        with open(dashboard_path, 'w') as f:
            json.dump(dashboard_config, f, indent=2)

        print("✅ Monitoring dashboards configured")

    def _setup_health_checks(self) -> None:
        """Setup comprehensive health checks"""
        print("Setting up health checks...")

        health_checks = {
            "checks": [
                {
                    "name": "api_health",
                    "type": "http",
                    "url": "http://localhost:8000/health",
                    "interval": "30s",
                    "timeout": "10s"
                },
                {
                    "name": "database_health",
                    "type": "tcp",
                    "host": "localhost",
                    "port": 5432,
                    "interval": "30s",
                    "timeout": "5s"
                },
                {
                    "name": "redis_health",
                    "type": "tcp",
                    "host": "localhost",
                    "port": 6379,
                    "interval": "30s",
                    "timeout": "5s"
                },
                {
                    "name": "disk_space",
                    "type": "disk",
                    "path": "/opt/indicator-variants",
                    "interval": "5m",
                    "threshold": "85%"
                },
                {
                    "name": "memory_usage",
                    "type": "process",
                    "pid_file": "/var/run/indicator-variants.pid",
                    "metric": "memory_percent",
                    "threshold": 80.0,
                    "interval": "1m"
                }
            ]
        }

        health_checks_path = self.monitoring_dir / "health_checks.json"
        with open(health_checks_path, 'w') as f:
            json.dump(health_checks, f, indent=2)

        print("✅ Health checks configured")

    def _setup_backup_monitoring(self) -> None:
        """Setup backup monitoring and alerting"""
        print("Setting up backup monitoring...")

        backup_monitoring = {
            "backup_checks": [
                {
                    "name": "daily_backup",
                    "type": "file_age",
                    "path": "/opt/backups/indicator-variants/latest",
                    "max_age_hours": 25,
                    "alert_threshold_hours": 26
                },
                {
                    "name": "backup_size",
                    "type": "file_size",
                    "path": "/opt/backups/indicator-variants/latest",
                    "min_size_mb": 100,
                    "alert_threshold_mb": 50
                },
                {
                    "name": "backup_integrity",
                    "type": "command",
                    "command": "tar -tzf /opt/backups/indicator-variants/latest/backup.tar.gz > /dev/null",
                    "interval": "1h",
                    "timeout": "5m"
                }
            ]
        }

        backup_config_path = self.monitoring_dir / "backup_monitoring.json"
        with open(backup_config_path, 'w') as f:
            json.dump(backup_monitoring, f, indent=2)

        print("✅ Backup monitoring configured")

    def validate_monitoring_setup(self) -> bool:
        """Validate that monitoring setup is working"""
        print("Validating monitoring setup...")

        try:
            # Check that configuration files exist
            required_files = [
                "prometheus.yml",
                "alerting_rules.yml",
                "health_checks.json",
                "backup_monitoring.json"
            ]

            for filename in required_files:
                file_path = self.monitoring_dir / filename
                if not file_path.exists():
                    print(f"❌ Missing configuration file: {filename}")
                    return False

            # Validate JSON files
            json_files = ["health_checks.json", "backup_monitoring.json"]
            for filename in json_files:
                file_path = self.monitoring_dir / filename
                try:
                    with open(file_path) as f:
                        json.load(f)
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON in {filename}: {e}")
                    return False

            print("✅ Monitoring setup validation passed")
            return True

        except Exception as e:
            print(f"❌ Monitoring validation failed: {e}")
            return False


def main():
    """Main monitoring setup entry point"""
    print("Indicator Variants - Monitoring Setup")
    print("=" * 40)

    setup = MonitoringSetup()

    # Setup monitoring
    if not setup.setup_monitoring():
        print("Monitoring setup failed!")
        return 1

    # Validate setup
    if not setup.validate_monitoring_setup():
        print("Monitoring validation failed!")
        return 1

    print("\nMonitoring setup completed successfully!")
    print("\nNext steps:")
    print("1. Start Prometheus: prometheus --config.file=monitoring/prometheus.yml")
    print("2. Start Grafana and import dashboard: monitoring/grafana_dashboard.json")
    print("3. Configure alerting: Copy monitoring/alerting_rules.yml to Alertmanager")
    print("4. Setup log aggregation: Configure logstash with monitoring/logstash.conf")

    return 0


if __name__ == "__main__":
    exit(main())