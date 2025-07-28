import json
import logging
from PIL import Image

logger = logging.getLogger(__name__)


def extract_prompt_from_png(path):
    """Return prompt and negative prompt from PNG metadata if available."""
    try:
        with Image.open(path) as img:
            if img.format != "PNG":
                logger.info("%s is not a PNG file", path)
                return None
            metadata = {}
            metadata.update(getattr(img, "text", {}) or {})
            metadata.update(img.info or {})
    except Exception as e:
        logger.warning("Failed to read image metadata for %s: %s", path, e)
        return None

    if not metadata:
        logger.info("No PNG metadata found in %s", path)
        return None

    key = _find_key(metadata, ["parameters"])
    if key:
        result = _parse_a1111(metadata[key])
        if result:
            logger.info("Extracted AUTOMATIC1111 prompt from %s", path)
        else:
            logger.warning("Failed to parse AUTOMATIC1111 prompt in %s", path)
        return result

    key = _find_key(metadata, ["prompt", "workflow"])
    if key:
        result = _parse_comfyui(metadata[key])
        if result:
            logger.info("Extracted ComfyUI prompt from %s", path)
        else:
            logger.warning("Failed to parse ComfyUI prompt in %s", path)
        return result

    logger.info("No recognizable prompt metadata in %s", path)
    return None


def _find_key(metadata, names):
    """Return the key from metadata matching one of the names."""
    lower = {k.lower(): k for k in metadata.keys()}
    for name in names:
        for k in metadata.keys():
            if k.lower().startswith(name.lower()):
                return k
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def _parse_a1111(text: str):
    """Parse AUTOMATIC1111/Forge style metadata."""
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


def _parse_comfyui(json_text: str):
    """Parse ComfyUI prompt or workflow JSON string."""
    try:
        data = json.loads(json_text)
    except Exception as e:
        logger.warning("Failed to parse ComfyUI JSON: %s", e)
        return None

    if not isinstance(data, dict):
        return None

    nodes = data.get("nodes") or data.get("workflow") or data
    positive = None
    negative = None

    def handle_node(node):
        nonlocal positive, negative
        if node.get("class_type") in {"CLIPTextEncode", "CLIPTextEncodeSDXL"}:
            widgets = node.get("widgets_values")
            if isinstance(widgets, list):
                if len(widgets) > 0 and positive is None and isinstance(widgets[0], str):
                    positive = widgets[0]
                if len(widgets) > 1 and negative is None and isinstance(widgets[1], str):
                    negative = widgets[1]
            inputs = node.get("inputs", {})
            if positive is None and isinstance(inputs.get("text"), str):
                positive = inputs.get("text")
            if negative is None and isinstance(inputs.get("negative"), str):
                negative = inputs.get("negative")

    if isinstance(nodes, dict):
        for node in nodes.values():
            if isinstance(node, dict):
                handle_node(node)
    elif isinstance(nodes, list):
        for node in nodes:
            if isinstance(node, dict):
                handle_node(node)

    if positive or negative:
        return {"prompt": positive or "", "negative_prompt": negative or ""}
    return None

