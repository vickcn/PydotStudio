window.FlowUtils = (() => {
  function safeText(value, fallback = "") {
    if (value === null || value === undefined) return fallback;
    if (typeof value === "string") return value;
    return JSON.stringify(value, null, 2);
  }

  function firstText(...values) {
    for (const v of values) {
      if (typeof v === "string" && v.trim()) return v.trim();
      if (Array.isArray(v) && v.length) return v.join(" / ");
      if (v && typeof v === "object" && Object.keys(v).length) return JSON.stringify(v, null, 2);
    }
    return "";
  }

  function nodeSummary(node) {
    const meta = node.meta || {};
    return firstText(meta.description, meta.notes, meta.functions, meta.files, meta.params);
  }

  function validateFlow(data) {
    const errors = [];
    if (!data || typeof data !== "object") errors.push("flow JSON 必須是 object");
    const nodes = Array.isArray(data?.nodes) ? data.nodes : [];
    const edges = Array.isArray(data?.edges) ? data.edges : [];
    const groups = Array.isArray(data?.groups) ? data.groups : [];
    const stylePresets = data?.style_presets || {};

    const nodeIds = new Set();
    nodes.forEach((n, i) => {
      if (!n.id) errors.push(`nodes[${i}] 缺少 id`);
      if (nodeIds.has(n.id)) errors.push(`node id 重複：${n.id}`);
      nodeIds.add(n.id);
    });

    const groupIds = new Set(groups.map(g => g.id).filter(Boolean));
    nodes.forEach(n => {
      if (n.group && !groupIds.has(n.group)) errors.push(`node ${n.id} 使用不存在的 group：${n.group}`);
      const refs = Array.isArray(n.style_refs) ? n.style_refs : (n.style_ref ? [n.style_ref] : []);
      refs.forEach(ref => { if (!stylePresets[ref]) errors.push(`node ${n.id} 使用不存在的 style_ref：${ref}`); });
    });

    edges.forEach((e, i) => {
      if (!e.from || !e.to) errors.push(`edges[${i}] 缺少 from/to`);
      if (e.from && !nodeIds.has(e.from)) errors.push(`edge from 不存在：${e.from}`);
      if (e.to && !nodeIds.has(e.to)) errors.push(`edge to 不存在：${e.to}`);
    });
    return errors;
  }

  function downloadText(filename, content) {
    const blob = new Blob([content], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  return { safeText, firstText, nodeSummary, validateFlow, downloadText };
})();
