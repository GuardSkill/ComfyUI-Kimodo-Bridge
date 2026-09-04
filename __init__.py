"""Kimodo Motion Bridge: generation plus Mixamo, Unity and Rive delivery."""
import traceback

print("[Kimodo Motion Bridge] loading...", flush=True)

try:
    from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    print(f"[Kimodo Motion Bridge] Loaded {len(NODE_CLASS_MAPPINGS)} nodes: {list(NODE_CLASS_MAPPINGS.keys())}", flush=True)
except Exception as e:
    print(f"[Kimodo Motion Bridge] Failed to import nodes: {e}", flush=True)
    traceback.print_exc()
    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
__version__ = "1.0.0"
