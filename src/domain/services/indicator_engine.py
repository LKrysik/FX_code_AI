"""
Indicator Engine - Wrapper for indicator variant functionality
Provides a clean API for indicator variant management with file-based persistence.
"""

from collections import defaultdict
from typing import Dict, Any, List, Optional
from .streaming_indicator_engine import StreamingIndicatorEngine


class IndicatorEngine:
    """
    Indicator Engine wrapper providing variant management functionality
    with file-based persistence per user_feedback.md requirements.
    """

    def __init__(self, streaming_engine: StreamingIndicatorEngine):
        self._streaming_engine = streaming_engine

    def create_variant(self, variant_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new indicator variant with file storage per user_feedback.md"""
        try:
            variant_id = self._streaming_engine.create_variant(
                name=variant_data["name"],
                base_indicator_type=variant_data["base_indicator"],
                variant_type=variant_data["type"],
                description=variant_data["description"],
                parameters=variant_data["parameters"],
                created_by=variant_data.get("created_by", "system")
            )

            return {
                "success": True,
                "variant": {
                    "id": variant_id,
                    "name": variant_data["name"],
                    "type": variant_data["type"],
                    "base_indicator": variant_data["base_indicator"],
                    "parameters": variant_data["parameters"],
                    "description": variant_data["description"],
                    "is_active": variant_data.get("is_active", True)
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_variant(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """Get variant by ID"""
        variant = self._streaming_engine.get_variant(variant_id)
        if not variant:
            return None

        return {
            "id": variant.id,
            "name": variant.name,
            "type": variant.variant_type,
            "base_indicator": variant.base_indicator_type,
            "parameters": variant.parameters,
            "description": variant.description,
            "is_active": True,  # All loaded variants are considered active
            "created_at": variant.created_at,
            "updated_at": variant.updated_at
        }

    def get_all_variants(self) -> List[Dict[str, Any]]:
        """Get all variants"""
        variants = []
        for variant in self._streaming_engine.list_variants():
            variants.append({
                "id": variant.id,
                "name": variant.name,
                "type": variant.variant_type,
                "base_indicator": variant.base_indicator_type,
                "parameters": variant.parameters,
                "description": variant.description,
                "is_active": True,
                "created_at": variant.created_at,
                "updated_at": variant.updated_at
            })
        return variants

    def get_variants_by_type(self, variant_type: str) -> List[Dict[str, Any]]:
        """Get variants filtered by type"""
        variants = self._streaming_engine.list_variants(variant_type)
        return [{
            "id": v.id,
            "name": v.name,
            "type": v.variant_type,
            "base_indicator": v.base_indicator_type,
            "parameters": v.parameters,
            "description": v.description,
            "is_active": True,
            "created_at": v.created_at,
            "updated_at": v.updated_at
        } for v in variants]

    def list_variants(self, variant_type: str = None) -> List[Dict[str, Any]]:
        """List all variants, optionally filtered by type (alias for compatibility)"""
        if variant_type:
            return self.get_variants_by_type(variant_type)
        variants = self._streaming_engine.list_variants()
        return [{
            "id": v.id,
            "name": v.name,
            "type": v.variant_type,
            "base_indicator": v.base_indicator_type,
            "parameters": v.parameters,
            "description": v.description,
            "is_active": True,
            "created_at": v.created_at,
            "updated_at": v.updated_at
        } for v in variants]

    def update_variant(self, variant_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update variant with file persistence per user_feedback.md"""
        try:
            # Get current variant
            current_variant = self._streaming_engine.get_variant(variant_id)
            if not current_variant:
                return {
                    "success": False,
                    "error": f"Variant {variant_id} not found"
                }

            # Prepare updated parameters
            updated_parameters = update_data.get("parameters", current_variant.parameters)

            # Update using streaming engine
            success = self._streaming_engine.update_variant_parameters(variant_id, updated_parameters)
            if not success:
                return {
                    "success": False,
                    "error": "Failed to update variant parameters"
                }

            # Get updated variant
            updated_variant = self._streaming_engine.get_variant(variant_id)

            return {
                "success": True,
                "variant": {
                    "id": updated_variant.id,
                    "name": update_data.get("name", updated_variant.name),
                    "type": updated_variant.variant_type,
                    "base_indicator": updated_variant.base_indicator_type,
                    "parameters": updated_variant.parameters,
                    "description": update_data.get("description", updated_variant.description),
                    "is_active": update_data.get("is_active", True)
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def update_variant_parameters(self, variant_id: str, parameters: Dict[str, Any]) -> bool:
        """Update parameters of a variant directly"""
        try:
            return self._streaming_engine.update_variant_parameters(variant_id, parameters)
        except Exception:
            return False

    def delete_variant(self, variant_id: str) -> Dict[str, Any]:
        """Delete variant and its file per user_feedback.md"""
        try:
            success = self._streaming_engine.delete_variant(variant_id)
            if success:
                return {"success": True}
            else:
                return {
                    "success": False,
                    "error": f"Variant {variant_id} not found"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def copy_variant(self, variant_id: str, new_name: str) -> Dict[str, Any]:
        """Copy/clone variant with new ID and name per user_feedback.md"""
        try:
            # Get original variant
            original = self._streaming_engine.get_variant(variant_id)
            if not original:
                return {
                    "success": False,
                    "error": f"Original variant {variant_id} not found"
                }

            # Create copy with new name
            copy_data = {
                "name": new_name,
                "base_indicator": original.base_indicator_type,
                "type": original.variant_type,
                "description": original.description,
                "parameters": original.parameters.copy(),
                "created_by": "system",  # Copy operation
                "is_active": True
            }

            # Create the copy
            result = self.create_variant(copy_data)
            if result["success"]:
                # Update name to include "(Copy)" suffix
                result["variant"]["name"] = f"{new_name} (Copy)"

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_system_indicators(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get system indicators organized by type for Create Variant tab per user_feedback.md"""
        system_indicators_data = self._streaming_engine.get_system_indicators()
        
        # Check if the data is in the new format
        if isinstance(system_indicators_data, dict) and "indicators" in system_indicators_data:
            indicators_list = system_indicators_data["indicators"]
        elif isinstance(system_indicators_data, list):
            # Handle old format if necessary
            indicators_list = system_indicators_data
        else:
            return {}

        # Group indicators by category
        grouped_indicators = defaultdict(list)
        for indicator in indicators_list:
            category = indicator.get("category", "general")
            grouped_indicators[category].append(indicator)
            
        return dict(grouped_indicators)

    def load_variants_from_files(self) -> List[Dict[str, Any]]:
        """Load variants from config/indicators/ directory per user_feedback.md"""
        return self._streaming_engine.load_variants_from_files()