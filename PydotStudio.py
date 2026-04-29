import argparse
import json
import logging
import os
import sys
import re
import subprocess
import tempfile
from typing import Any, Dict, Optional

import pydot

sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from package import dataframeprocedure as DFP
LOGger = DFP.LOGger


def load_json_robust(path: str, encoding: str = "utf-8-sig") -> Dict[str, Any]:
    try:
        return LOGger.load_json(path, encoding=encoding)
    except Exception:
        pass

    with open(path, "rb") as f:
        raw = f.read()

    encodings = [encoding, "utf-8-sig", "utf-8", "utf-16", "utf-16-le", "utf-16-be"]
    tried = set()
    for enc in encodings:
        if not enc or enc in tried:
            continue
        tried.add(enc)
        try:
            text = raw.decode(enc)
            text = text.lstrip("\ufeff")
            return json.loads(text)
        except Exception:
            continue

    with open(path, "r", encoding=encoding, errors="replace") as f:
        text = f.read().lstrip("\ufeff")
    return json.loads(text)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "host": "10.1.3.127",
    "port": 7223,
    "output_dir": os.path.join(BASE_DIR, "output"),
    "default_format": "png",
    "rankdir": "LR",
    "fontname": "Microsoft JhengHei",
    "font_path": BASE_DIR,
}

DEFAULT_VIEWER_CONFIG: Dict[str, Any] = {
    "default_render_mode": "cytoscape_2d",
    "cytoscape_2d": {
        "node_label_color_on_light_fill": "#0f172a",
        "node_label_color_on_dark_fill": "#e5e7eb",
        "light_fill_luminance_threshold": 0.65,
        "node_hover_scale": 1.6,
        "node_min_screen_px": 28,
    },
    "three_3d": {
        "node_background_opacity": 0.4,
        "node_border_color": "#38bdf8",
        "node_label_color": "#0f172a",
        "link_color": "#64748b",
        "link_opacity": 0.88,
        "background_color": "#050816",
        "show_particles": False,
        "warmup_ticks": 200,
        "cooldown_ticks": 0,
        "charge_strength": -140,
        "link_distance": 56,
        "center_strength": 0.04,
        "velocity_decay": 0.22,
        "alpha_decay": 0.015,
        "sprite_min_width": 120,
        "sprite_height": 44,
        "sprite_padding_x": 18,
        "sprite_font_family": "Microsoft JhengHei, Segoe UI, sans-serif",
        "sprite_font_size_px": 13,
        "focus_target_screen_fraction": 0.3333333333333333,
        "focus_transition_ms": 920,
        "focus_viewport_boost": 1.22,
        "focus_fallback_distance_extra": 108,
        "focus_sprite_world_extent": 40,
        "focus_min_cam_separation": 26,
        "focus_zoom_in_hard_cap_ratio": 0.985,
        "link_directional_arrow_length": 10,
        "link_directional_arrow_rel_pos": 0.85,
        "link_directional_arrow_color": "#94a3b8",
        "link_curvature": 0.14,
        "label_text_stroke_color": "#000000",
        "label_text_stroke_width_px": 2.75,
        "node_hover_max_scale": 12,
        "node_min_screen_fraction": 0.025,
        "node_min_size_max_scale": 5,
    },
}


def _deep_merge_dict(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = dict(base)
    for k, v in overlay.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge_dict(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str = CONFIG_PATH) -> Dict[str, Any]:
    raw: Dict[str, Any] = {}
    if os.path.isfile(path):
        raw = load_json_robust(path, encoding="utf-8-sig")
    merged = DEFAULT_CONFIG.copy()
    for k, v in raw.items():
        if k == "viewer":
            continue
        merged[k] = v
    merged["viewer"] = _deep_merge_dict(DEFAULT_VIEWER_CONFIG, raw.get("viewer") or {})
    return merged


CONFIG = load_config()
_font_path = CONFIG.get("font_path")
if _font_path:
    existing = os.environ.get("DOTFONTPATH", "")
    paths = [p for p in existing.split(os.pathsep) if p]
    if _font_path not in paths:
        os.environ["DOTFONTPATH"] = _font_path + (os.pathsep + existing if existing else "")
    gd_existing = os.environ.get("GDFONTPATH", "")
    gd_paths = [p for p in gd_existing.split(os.pathsep) if p]
    if _font_path not in gd_paths:
        os.environ["GDFONTPATH"] = _font_path + (os.pathsep + gd_existing if gd_existing else "")


def _setup_logger(log_path: Optional[str], debug: bool) -> logging.Logger:
    logger = logging.getLogger("PydotStudio")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    if log_path:
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger


def _render_graph_via_dot(
        graph: pydot.Dot,
        fmt: str,
        output_path: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ) -> Any:
    fontname = CONFIG.get("fontname")
    dot_content = graph.to_string()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".dot", mode="w", encoding="utf-8") as dot_file:
        dot_file.write(dot_content)
        dot_path = dot_file.name

    out_path = output_path
    if not out_path:
        with tempfile.NamedTemporaryFile(delete=False, suffix="." + fmt) as out_file:
            out_path = out_file.name

    cmd = ["dot", f"-T{fmt}"]
    if fontname:
        cmd.extend(
            [
                f"-Gfontname={fontname}",
                f"-Nfontname={fontname}",
                f"-Efontname={fontname}",
            ]
        )
    cmd.extend([dot_path, "-o", out_path])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            if logger:
                logger.error("dot failed: %s", proc.stderr.strip())
            raise RuntimeError(f"dot failed: {proc.stderr.strip()}")
        if output_path:
            return out_path
        with open(out_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.remove(dot_path)
        except Exception:
            pass
        if not output_path:
            try:
                os.remove(out_path)
            except Exception:
                pass


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name).strip()
    return name or "flow"


def _quote_if_needed(value: Any) -> Any:
    if isinstance(value, str) and "," in value:
        if not (value.startswith("\"") and value.endswith("\"")):
            return f"\"{value}\""
    return value


def build_label(node: Dict[str, Any], include_meta: bool) -> str:
    label = str(node.get("label", node.get("id", "")))
    if not include_meta:
        return label
    meta = node.get("meta", {}) or {}
    lines = []
    description = meta.get("description")
    if description:
        lines.append(description)
    bullets = meta.get("bullets", []) or []
    for b in bullets:
        lines.append(f"- {b}")
    files = meta.get("files", []) or []
    if files:
        lines.append("files: " + ", ".join(files))
    functions = meta.get("functions", []) or []
    if functions:
        lines.append("functions: " + ", ".join(functions))
    params = meta.get("params", []) or []
    if params:
        lines.append("params: " + ", ".join(params))
    notes = meta.get("notes", []) or []
    if notes:
        lines.append("notes: " + " / ".join(notes))
    if lines:
        label = label + "\n" + "\n".join(lines)
    return label


def _resolve_style_refs(style_refs: Any, style_presets: Dict[str, Any]) -> Dict[str, Any]:
    if not style_refs:
        return {}
    if isinstance(style_refs, str):
        refs = [style_refs]
    elif isinstance(style_refs, (list, tuple, set)):
        refs = [r for r in style_refs if r]
    else:
        return {}

    merged: Dict[str, Any] = {}
    for ref in refs:
        preset = style_presets.get(ref)
        if isinstance(preset, dict):
            merged.update(preset)
    return merged


def build_graph(data: Dict[str, Any], include_meta: bool = False) -> pydot.Dot:
    graph_attr = (data.get("graph") or {}).copy()
    if "label" not in graph_attr and data.get("title"):
        graph_attr["label"] = data.get("title")
    graph_attr.setdefault("rankdir", CONFIG.get("rankdir", "LR"))
    fontname = CONFIG.get("fontname")
    if fontname:
        graph_attr.setdefault("fontname", fontname)

    graph = pydot.Dot(graph_type="digraph", **graph_attr)
    style_presets = data.get("style_presets") or {}

    node_defaults = (data.get("node_style") or {}).copy()
    if fontname:
        node_defaults.setdefault("fontname", fontname)
    if "style" in node_defaults:
        node_defaults["style"] = _quote_if_needed(node_defaults["style"])
    if node_defaults:
        graph.set_node_defaults(**node_defaults)

    edge_defaults = (data.get("edge_style") or {}).copy()
    if fontname:
        edge_defaults.setdefault("fontname", fontname)
    if edge_defaults:
        graph.set_edge_defaults(**edge_defaults)

    groups = {}
    for group in data.get("groups", []) or []:
        gid = group.get("id")
        if not gid:
            continue
        attrs = {}
        attrs.update(_resolve_style_refs(group.get("style_ref") or group.get("style_refs"), style_presets))
        if "label" in group:
            attrs["label"] = group["label"]
        style = group.get("style")
        if isinstance(style, dict):
            attrs.update(style)
        extra_attrs = group.get("attrs")
        if isinstance(extra_attrs, dict):
            attrs.update(extra_attrs)
        if "style" in attrs:
            attrs["style"] = _quote_if_needed(str(attrs["style"]))
        if fontname:
            attrs.setdefault("fontname", fontname)
        cluster = pydot.Cluster(f"cluster_{gid}", **attrs)
        groups[gid] = cluster
        graph.add_subgraph(cluster)

    for node in data.get("nodes", []) or []:
        nid = node.get("id")
        if not nid:
            continue
        attrs: Dict[str, Any] = {}
        attrs.update(_resolve_style_refs(node.get("style_ref") or node.get("style_refs"), style_presets))
        for key in ["shape", "style", "fillcolor", "color", "fontcolor", "fontsize", "penwidth"]:
            if key in node:
                value = str(node[key])
                attrs[key] = _quote_if_needed(value) if key == "style" else value
        extra_attrs = node.get("attrs")
        if isinstance(extra_attrs, dict):
            attrs.update(extra_attrs)
        if "style" in attrs:
            attrs["style"] = _quote_if_needed(str(attrs["style"]))
        attrs["label"] = build_label(node, include_meta)
        pd_node = pydot.Node(nid, **attrs)
        gid = node.get("group")
        if gid and gid in groups:
            groups[gid].add_node(pd_node)
        else:
            graph.add_node(pd_node)

    for edge in data.get("edges", []) or []:
        src = edge.get("from")
        dst = edge.get("to")
        if not src or not dst:
            continue
        attrs = {}
        attrs.update(_resolve_style_refs(edge.get("style_ref") or edge.get("style_refs"), style_presets))
        if "label" in edge:
            attrs["label"] = edge["label"]
        if "style" in edge:
            attrs["style"] = _quote_if_needed(edge["style"])
        if "color" in edge:
            attrs["color"] = edge["color"]
        extra_attrs = edge.get("attrs")
        if isinstance(extra_attrs, dict):
            attrs.update(extra_attrs)
        if "style" in attrs:
            attrs["style"] = _quote_if_needed(str(attrs["style"]))
        graph.add_edge(pydot.Edge(src, dst, **attrs))

    return graph


def graph_to_bytes(graph: pydot.Dot, fmt: str) -> bytes:
    return graph.create(format=fmt)


def get_media_type(fmt: str) -> str:
    if fmt == "svg":
        return "image/svg+xml"
    if fmt == "png":
        return "image/png"
    if fmt == "pdf":
        return "application/pdf"
    return "application/octet-stream"


def render_flow(
        data: Dict[str, Any],
        fmt: Optional[str] = None,
        include_meta: bool = False,
        save: bool = False,
    ) -> Any:
    fmt = fmt or CONFIG.get("default_format", "png")
    graph = build_graph(data, include_meta=include_meta)
    if save:
        out_dir = CONFIG.get("output_dir", os.path.join(BASE_DIR, "output"))
        os.makedirs(out_dir, exist_ok=True)
        title = data.get("title") or "flow"
        filename = sanitize_filename(title) + "." + fmt
        out_path = os.path.join(out_dir, filename)
        _render_graph_via_dot(graph, fmt, output_path=out_path)
        return {"saved_path": out_path}
    return _render_graph_via_dot(graph, fmt)


def render_by_file(
        path: str,
        fmt: Optional[str] = None,
        include_meta: bool = False,
        save: bool = False,
    ) -> Any:
    if not os.path.isfile(path):
        raise ValueError(f"File not found: {path}")
    # with open(path, "r", encoding="utf-8") as f:
    #     data = json.load(f)
    data = load_json_robust(path, encoding="utf-8-sig")
    return render_flow(data=data, fmt=fmt, include_meta=include_meta, save=save)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PydotStudio CLI renderer")
    parser.add_argument("-i", "--input", required=True, help="Input JSON file path")
    parser.add_argument("-f", "--format", default=None, help="png/svg/pdf (default: config.json)")
    parser.add_argument("-m", "--include-meta", action="store_true", help="Include meta in labels")
    parser.add_argument("-o", "--output", default=None, help="Output file path (optional)")
    parser.add_argument("-d", "--output-dir", default=None, help="Output directory (auto filename)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logs and .dot output")
    parser.add_argument("--log", default=None, help="Log file path (optional)")
    return parser.parse_args()


def _render_cli() -> str:
    args = _parse_args()
    logger = _setup_logger(args.log, args.debug)
    logger.info("input=%s", args.input)
    logger.info("format=%s include_meta=%s output=%s output_dir=%s", args.format, args.include_meta, args.output, args.output_dir)
    logger.info("config fontname=%s font_path=%s rankdir=%s default_format=%s", CONFIG.get("fontname"), CONFIG.get("font_path"), CONFIG.get("rankdir"), CONFIG.get("default_format"))
    logger.info("DOTFONTPATH=%s", os.environ.get("DOTFONTPATH"))
    logger.info("GDFONTPATH=%s", os.environ.get("GDFONTPATH"))
    if args.debug:
        try:
            proc = subprocess.run(["dot", "-V"], capture_output=True, text=True)
            logger.info("dot -V: %s %s", proc.stdout.strip(), proc.stderr.strip())
        except Exception as e:
            logger.warning("dot -V failed: %s", e)

    if not os.path.isfile(args.input):
        raise FileNotFoundError(f"File not found: {args.input}")
    # with open(args.input, "r", encoding="utf-8") as f:
    #     data = json.load(f)
    data = load_json_robust(args.input, encoding="utf-8-sig")
    fmt = args.format or CONFIG.get("default_format", "png")
    graph = build_graph(data, include_meta=args.include_meta)

    if args.debug:
        logger.info("graph attrs: %s", data.get("graph"))
        logger.info("node_style: %s", data.get("node_style"))
        logger.info("edge_style: %s", data.get("edge_style"))
        dot_dir = args.output_dir or CONFIG.get("output_dir", os.path.join(BASE_DIR, "output"))
        os.makedirs(dot_dir, exist_ok=True)
        title = data.get("title") or os.path.splitext(os.path.basename(args.input))[0] or "flow"
        dot_path = os.path.join(dot_dir, sanitize_filename(title) + ".dot")
        with open(dot_path, "w", encoding="utf-8") as f:
            f.write(graph.to_string())
        logger.info("dot file saved: %s", dot_path)

    if args.output:
        out_path = args.output
        out_dir = os.path.dirname(out_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
    else:
        out_dir = args.output_dir or CONFIG.get("output_dir", os.path.join(BASE_DIR, "output"))
        os.makedirs(out_dir, exist_ok=True)
        title = data.get("title") or os.path.splitext(os.path.basename(args.input))[0] or "flow"
        filename = sanitize_filename(title) + "." + fmt
        out_path = os.path.join(out_dir, filename)

    _render_graph_via_dot(graph, fmt, output_path=out_path, logger=logger)
    logger.info("output saved: %s", out_path)
    return out_path


def main() -> None:
    out_path = _render_cli()
    print(out_path)


if __name__ == "__main__":
    main()
