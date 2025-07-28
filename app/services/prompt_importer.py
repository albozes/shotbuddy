import json
import logging
from PIL import Image

logger = logging.getLogger(__name__)


def extract_prompt_from_png(path):
    """Return prompt and negative prompt from PNG metadata if available."""
    try:
        with Image.open(path) as img:
            if img.format != "PNG":
                return None
            metadata = getattr(img, "text", {}) or {}
    except Exception as e:
        logger.warning("Failed to read image metadata: %s", e)
        return None

    if not metadata:
        return None

    if "parameters" in metadata:
        return _parse_a1111(metadata["parameters"])
    if "workflow" in metadata or "prompt" in metadata:
        return _parse_comfyui(metadata)
    return None


def _parse_a1111(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    positive = lines[0]
    negative = ""
    for line in lines[1:]:
        if line.lower().startswith("negative prompt:"):
            negative = line[len("Negative prompt:"):].strip()
            break
    return {"prompt": positive, "negative_prompt": negative}


def _parse_comfyui(metadata):
    data = None
    for key in ("prompt", "workflow"):
        if key in metadata:
            try:
                data = json.loads(metadata[key])
                if isinstance(data, dict):
                    break
            except Exception as e:
                logger.warning("Failed to parse %s chunk: %s", key, e)
    if not isinstance(data, dict):
        return None

    nodes = data.get("nodes") or data.get("workflow") or data
    positive = None
    negative = None

    def handle_node(node):
        nonlocal positive, negative
        if node.get("class_type") in {"CLIPTextEncode", "CLIPTextEncodeSDXL"}:
            widgets = node.get("widgets_values")
            if isinstance(widgets, list) and widgets:
                if positive is None:
                    positive = widgets[0] if isinstance(widgets[0], str) else None
                if len(widgets) > 1 and negative is None:
                    negative = widgets[1] if isinstance(widgets[1], str) else None

    if isinstance(nodes, list):
        for node in nodes:
            if isinstance(node, dict):
                handle_node(node)
    elif isinstance(nodes, dict):
        for node in nodes.values():
            if isinstance(node, dict):
                handle_node(node)

    if positive:
        return {"prompt": positive, "negative_prompt": negative or ""}
    return None
