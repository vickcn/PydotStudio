import json
import pathlib
import pydot

p = pathlib.Path(r"C:\ML_HOME\DocumentManagerQAS\issues\batch_import_url_flow.json")
raw = p.read_bytes()
text = None
for enc in ("utf-8-sig", "utf-8", "utf-16", "utf-16-le", "utf-16-be"):
    try:
        text = raw.decode(enc)
        text = text.lstrip("\ufeff")
        data = json.loads(text)
        break
    except Exception:
        data = None
if data is None:
    raise SystemExit("decode failed")


def build_label(node, include_meta=True):
    label = str(node.get("label", node.get("id", "")))
    if not include_meta:
        return label
    meta = node.get("meta", {}) or {}
    lines = []
    description = meta.get("description")
    if description:
        lines.append(description)
    for b in (meta.get("bullets") or []):
        lines.append(f"- {b}")
    files = meta.get("files") or []
    if files:
        lines.append("files: " + ", ".join(files))
    functions = meta.get("functions") or []
    if functions:
        lines.append("functions: " + ", ".join(functions))
    params = meta.get("params") or []
    if params:
        lines.append("params: " + ", ".join(params))
    notes = meta.get("notes") or []
    if notes:
        lines.append("notes: " + " / ".join(notes))
    if lines:
        label = label + "\n" + "\n".join(lines)
    return label


graph_attr = (data.get("graph") or {}).copy()
if "label" not in graph_attr and data.get("title"):
    graph_attr["label"] = data.get("title")

graph_attr.setdefault("rankdir", data.get("rankdir", "LR"))

fontname = data.get("fontname")
if fontname:
    graph_attr.setdefault("fontname", fontname)

graph = pydot.Dot(graph_type="digraph", **graph_attr)

node_defaults = (data.get("node_style") or {}).copy()
if fontname:
    node_defaults.setdefault("fontname", fontname)
if node_defaults:
    graph.set_node_defaults(**node_defaults)

edge_defaults = (data.get("edge_style") or {}).copy()
if fontname:
    edge_defaults.setdefault("fontname", fontname)
if edge_defaults:
    graph.set_edge_defaults(**edge_defaults)

groups = {}
for group in (data.get("groups") or []):
    gid = group.get("id")
    if not gid:
        continue
    attrs = {}
    if "label" in group:
        attrs["label"] = group["label"]
    style = group.get("style")
    if isinstance(style, dict):
        attrs.update(style)
    extra = group.get("attrs")
    if isinstance(extra, dict):
        attrs.update(extra)
    if fontname:
        attrs.setdefault("fontname", fontname)
    cluster = pydot.Cluster(f"cluster_{gid}", **attrs)
    groups[gid] = cluster
    graph.add_subgraph(cluster)

for node in (data.get("nodes") or []):
    nid = node.get("id")
    if not nid:
        continue
    attrs = {}
    extra = node.get("attrs")
    if isinstance(extra, dict):
        attrs.update(extra)
    for key in ["shape", "style", "fillcolor", "color", "fontcolor", "fontsize", "penwidth"]:
        if key in node:
            attrs[key] = str(node[key])
    attrs["label"] = build_label(node, include_meta=True)
    pd_node = pydot.Node(nid, **attrs)
    gid = node.get("group")
    if gid and gid in groups:
        groups[gid].add_node(pd_node)
    else:
        graph.add_node(pd_node)

for edge in (data.get("edges") or []):
    src = edge.get("from")
    dst = edge.get("to")
    if not src or not dst:
        continue
    attrs = {}
    if "label" in edge:
        attrs["label"] = edge["label"]
    if "style" in edge:
        attrs["style"] = edge["style"]
    if "color" in edge:
        attrs["color"] = edge["color"]
    extra = edge.get("attrs")
    if isinstance(extra, dict):
        attrs.update(extra)
    graph.add_edge(pydot.Edge(src, dst, **attrs))

text = graph.to_string()
lines = text.splitlines()
for i, line in enumerate(lines[:120], start=1):
    print(f"{i:02d}: {line}")
