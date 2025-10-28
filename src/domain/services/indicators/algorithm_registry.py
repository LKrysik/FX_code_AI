"""
Indicator Algorithm Registry with Auto-Discovery
==============================================
Automatically discovers and registers indicator algorithms from the indicators/ folder.
"""

import importlib
import inspect
from pathlib import Path
from typing import Dict, Optional, List, Any
import logging

# Import IndicatorAlgorithm base classes
from .base_algorithm import IndicatorAlgorithm, MultiWindowIndicatorAlgorithm

# ✅ LOGGER FIX: Use absolute import (project standard) instead of relative import
from src.core.logger import StructuredLogger, get_logger


class IndicatorAlgorithmRegistry:
    """
    Registry for indicator algorithms with automatic discovery.
    
    Features:
    - Auto-discovery of algorithms from indicators/ folder
    - Manual registration support
    - Algorithm metadata caching
    - Integration with streaming engine
    """
    
    def __init__(self, logger: Optional[Any] = None):
        # ✅ LOGGER FIX: Use get_logger() for fallback instead of direct StructuredLogger
        self.logger = logger or get_logger(__name__)
        self._algorithms: Dict[str, IndicatorAlgorithm] = {}
        self._metadata_cache: Dict[str, Dict[str, Any]] = {}
        self._discovery_attempted = False
    
    def auto_discover_algorithms(self) -> int:
        """
        Automatically discover and register algorithms from indicators/ folder.
        
        Returns:
            Number of algorithms discovered and registered
        """
        if self._discovery_attempted:
            return len(self._algorithms)
        
        self._discovery_attempted = True
        discovered_count = 0
        
        # Get indicators directory relative to this file
        indicators_dir = Path(__file__).parent
        
        self.logger.debug("indicator_algorithm_registry.discovery_started", {
            "indicators_dir": str(indicators_dir),
            "existing_algorithms": len(self._algorithms)
        })
        
        files_found = list(indicators_dir.glob("*.py"))
        self.logger.info("indicator_algorithm_registry.files_found", {
            "total_files": len(files_found),
            "files": [f.name for f in files_found]
        })

        for py_file in files_found:
            if py_file.name.startswith("_") or py_file.name in ["base_algorithm.py", "algorithm_registry.py"]:
                self.logger.info("indicator_algorithm_registry.file_skipped", {
                    "file": py_file.name,
                    "reason": "excluded"
                })
                continue

            module_name = py_file.stem
            self.logger.info("indicator_algorithm_registry.loading_module", {
                "module": module_name,
                "file": py_file.name
            })
            count = self._load_algorithms_from_module(module_name)
            self.logger.info("indicator_algorithm_registry.module_loaded", {
                "module": module_name,
                "algorithms_found": count
            })
            discovered_count += count
        
        self.logger.info("indicator_algorithm_registry.discovery_completed", {
            "total_algorithms": len(self._algorithms),
            "newly_discovered": discovered_count
        })
        
        return discovered_count
    
    def _load_algorithms_from_module(self, module_name: str) -> int:
        """Load algorithms from a specific module."""
        discovered_count = 0
        
        try:
            # Dynamic import - handle both relative and absolute imports
            module = None
            import_attempts = [
                f"src.domain.services.indicators.{module_name}",
                f"...indicators.{module_name}",
                f".{module_name}",
                module_name
            ]
            
            for import_path in import_attempts:
                try:
                    if import_path.startswith("..."):
                        module = importlib.import_module(import_path, __name__)
                    elif import_path.startswith("."):
                        module = importlib.import_module(import_path, __package__)
                    else:
                        module = importlib.import_module(import_path)
                    self.logger.info("indicator_algorithm_registry.import_success", {
                        "module": module_name,
                        "import_path": import_path
                    })
                    break
                except (ImportError, ValueError) as e:
                    self.logger.info("indicator_algorithm_registry.import_attempt_failed", {
                        "module": module_name,
                        "import_path": import_path,
                        "error": str(e)
                    })
                    continue
            
            if not module:
                self.logger.warning("indicator_algorithm_registry.module_import_failed", {
                    "module": module_name,
                    "attempts": import_attempts
                })
                return 0
            
            # Find algorithm classes and instances
            members_count = 0
            for name, obj in inspect.getmembers(module):
                members_count += 1
                if self._is_algorithm_class(obj):
                    # Instantiate and register algorithm class
                    try:
                        algorithm = obj()
                        self.register_algorithm(algorithm)
                        discovered_count += 1

                        self.logger.info("indicator_algorithm_registry.algorithm_class_registered", {
                            "module": module_name,
                            "class_name": name,
                            "indicator_type": algorithm.get_indicator_type()
                        })
                    except Exception as e:
                        self.logger.warning("indicator_algorithm_registry.algorithm_instantiation_failed", {
                            "module": module_name,
                            "class_name": name,
                            "error": str(e)
                        })

                elif self._is_algorithm_instance(obj):
                    # Register algorithm instance directly
                    self.register_algorithm(obj)
                    discovered_count += 1

                    self.logger.info("indicator_algorithm_registry.algorithm_instance_registered", {
                        "module": module_name,
                        "instance_name": name,
                        "indicator_type": obj.get_indicator_type()
                    })

            self.logger.info("indicator_algorithm_registry.module_inspection_complete", {
                "module": module_name,
                "total_members": members_count,
                "algorithms_found": discovered_count
            })
        
        except Exception as e:
            self.logger.warning("indicator_algorithm_registry.module_load_failed", {
                "module": module_name,
                "error": str(e)
            })
        
        return discovered_count
    
    def _is_algorithm_class(self, obj) -> bool:
        """Check if object is an algorithm class (not instance)."""
        return (
            inspect.isclass(obj) and
            issubclass(obj, IndicatorAlgorithm) and
            obj is not IndicatorAlgorithm and
            obj is not MultiWindowIndicatorAlgorithm
        )
    
    def _is_algorithm_instance(self, obj) -> bool:
        """Check if object is an algorithm instance."""
        return isinstance(obj, IndicatorAlgorithm)
    
    def register_algorithm(self, algorithm: IndicatorAlgorithm) -> None:
        """
        Manually register an algorithm instance.
        
        Args:
            algorithm: Instance of IndicatorAlgorithm to register
        """
        indicator_type = algorithm.get_indicator_type()
        
        if indicator_type in self._algorithms:
            self.logger.warning("indicator_algorithm_registry.algorithm_overwrite", {
                "indicator_type": indicator_type,
                "existing_name": self._algorithms[indicator_type].get_name(),
                "new_name": algorithm.get_name()
            })
        
        self._algorithms[indicator_type] = algorithm
        self._metadata_cache[indicator_type] = algorithm.get_registry_metadata()
        
        self.logger.debug("indicator_algorithm_registry.algorithm_registered", {
            "indicator_type": indicator_type,
            "algorithm_name": algorithm.get_name(),
            "category": algorithm.get_category()
        })
    
    def get_algorithm(self, indicator_type: str) -> Optional[IndicatorAlgorithm]:
        """Get algorithm instance by type."""
        if not self._discovery_attempted:
            self.auto_discover_algorithms()
        
        return self._algorithms.get(indicator_type)
    
    def get_all_algorithms(self) -> Dict[str, IndicatorAlgorithm]:
        """Get all registered algorithms."""
        if not self._discovery_attempted:
            self.auto_discover_algorithms()
        
        return self._algorithms.copy()
    
    def get_algorithm_metadata(self, indicator_type: str) -> Optional[Dict[str, Any]]:
        """Get cached metadata for algorithm."""
        if not self._discovery_attempted:
            self.auto_discover_algorithms()
        
        return self._metadata_cache.get(indicator_type)
    
    def get_all_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Get metadata for all algorithms."""
        if not self._discovery_attempted:
            self.auto_discover_algorithms()
        
        return self._metadata_cache.copy()
    
    def get_algorithms_by_category(self, category: str) -> Dict[str, IndicatorAlgorithm]:
        """Get algorithms filtered by category."""
        if not self._discovery_attempted:
            self.auto_discover_algorithms()
        
        return {
            indicator_type: algorithm
            for indicator_type, algorithm in self._algorithms.items()
            if algorithm.get_category() == category
        }
    
    def get_categories(self) -> List[str]:
        """Get all available categories."""
        if not self._discovery_attempted:
            self.auto_discover_algorithms()
        
        categories = set(algorithm.get_category() for algorithm in self._algorithms.values())
        return sorted(categories)
    
    def calculate_refresh_interval(self, indicator_type: str, params: Dict[str, Any]) -> Optional[float]:
        """Calculate refresh interval for an algorithm with given parameters."""
        algorithm = self.get_algorithm(indicator_type)
        if not algorithm:
            return None
        
        from .base_algorithm import IndicatorParameters
        wrapped_params = IndicatorParameters(params)
        return algorithm.calculate_refresh_interval(wrapped_params)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        if not self._discovery_attempted:
            self.auto_discover_algorithms()
        
        categories = {}
        for algorithm in self._algorithms.values():
            category = algorithm.get_category()
            categories[category] = categories.get(category, 0) + 1
        
        return {
            "total_algorithms": len(self._algorithms),
            "categories_count": len(categories),
            "algorithms_by_category": categories,
            "discovery_attempted": self._discovery_attempted
        }