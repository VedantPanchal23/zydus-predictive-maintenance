"""Re-export canonical Equipment Registry."""
from core.equipment_registry import list_active_equipment_ids, resolve_equipment_id

__all__ = ["list_active_equipment_ids", "resolve_equipment_id"]
