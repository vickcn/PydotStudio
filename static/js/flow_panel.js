window.FlowPanel = (() => {
  const $ = (id) => document.getElementById(id);

  function renderStats(flow) {
    const nodes = flow?.nodes?.length || 0;
    const edges = flow?.edges?.length || 0;
    const groups = flow?.groups?.length || 0;
    $("flowTitle").textContent = flow?.title || "未命名流程";
    $("canvasTitle").textContent = flow?.title || "未命名流程";
    $("flowStats").textContent = `nodes: ${nodes} · edges: ${edges} · groups: ${groups}`;
  }

  function renderNodeList(flow, onSelect, keyword = "", activeId = null, onActivate = null) {
    const box = $("nodeList");
    box.innerHTML = "";
    const q = keyword.trim().toLowerCase();
    const nodes = flow?.nodes || [];
    nodes
      .filter(n => {
        if (!q) return true;
        return JSON.stringify(n).toLowerCase().includes(q);
      })
      .forEach(node => {
        const item = document.createElement("div");
        const active = activeId !== null && activeId !== undefined && String(node.id) === String(activeId);
        item.className = `node-item ${active ? "active" : ""}`;
        item.innerHTML = `
          <div class="node-id">${escapeHtml(node.id || "")}</div>
          <div class="node-label">${escapeHtml(node.label || "")}</div>
          <div class="node-meta">${escapeHtml(FlowUtils.nodeSummary(node) || node.group || "")}</div>
        `;
        item.addEventListener("click", () => onSelect(node.id));
        if (onActivate) {
          item.addEventListener("dblclick", evt => {
            if (evt && evt.cancelable) evt.preventDefault();
            onActivate(node.id);
          });
        }
        box.appendChild(item);
      });
  }

  function showNodeDetail(node, incoming = [], outgoing = []) {
    $("detailEmpty").classList.add("hidden");
    const box = $("detailContent");
    box.classList.remove("hidden");
    const meta = node.meta || {};
    box.innerHTML = `
      <div class="detail-title">${escapeHtml(node.label || node.id || "")}</div>
      <div class="detail-grid">
        ${row("id", node.id)}
        ${row("group", node.group)}
        ${row("style_ref", node.style_ref || node.style_refs)}
        ${row("description", meta.description)}
        ${row("functions", meta.functions)}
        ${row("files", meta.files)}
        ${row("params", meta.params)}
        ${row("notes", meta.notes)}
        ${row("incoming", incoming.map(e => `${e.from} → ${e.to}${e.label ? `｜${e.label}` : ""}`))}
        ${row("outgoing", outgoing.map(e => `${e.from} → ${e.to}${e.label ? `｜${e.label}` : ""}`))}
        ${row("raw", node)}
      </div>
    `;
  }

  function showTooltip(node, x, y, bounds = null) {
    const tip = $("hoverTooltip");
    const pad = 10;
    const offset = 10;
    tip.innerHTML = `
      <div class="tooltip-title">${escapeHtml(node.label || node.id || "")}</div>
      <div class="tooltip-sub">${escapeHtml(node.id || "")} ${node.group ? "· " + escapeHtml(node.group) : ""}</div>
      <div class="tooltip-sub">${escapeHtml(FlowUtils.nodeSummary(node) || "無 meta 摘要")}</div>
    `;
    tip.classList.remove("hidden");

    const hostRect = tip.offsetParent?.getBoundingClientRect() || {
      left: 0,
      top: 0,
      right: window.innerWidth,
      bottom: window.innerHeight,
    };
    const rawLeft = Number.isFinite(bounds?.left) ? Number(bounds.left) : hostRect.left;
    const rawTop = Number.isFinite(bounds?.top) ? Number(bounds.top) : hostRect.top;
    const rawRight = Number.isFinite(bounds?.right) ? Number(bounds.right) : hostRect.right;
    const rawBottom = Number.isFinite(bounds?.bottom) ? Number(bounds.bottom) : hostRect.bottom;

    const areaLeft = Math.max(hostRect.left, rawLeft) + pad;
    const areaTop = Math.max(hostRect.top, rawTop) + pad;
    const areaRight = Math.min(hostRect.right, rawRight) - pad;
    const areaBottom = Math.min(hostRect.bottom, rawBottom) - pad;
    const areaWidth = Math.max(180, areaRight - areaLeft);
    tip.style.width = `${Math.min(320, areaWidth)}px`;
    tip.style.maxWidth = `${areaWidth}px`;

    const tw = tip.offsetWidth || 320;
    const th = tip.offsetHeight || 140;

    let leftAbs = x + offset;
    let topAbs = y + offset;

    if (leftAbs + tw > areaRight) leftAbs = x - tw - offset;
    if (topAbs + th > areaBottom) topAbs = y - th - offset;

    leftAbs = Math.max(areaLeft, Math.min(leftAbs, Math.max(areaLeft, areaRight - tw)));
    topAbs = Math.max(areaTop, Math.min(topAbs, Math.max(areaTop, areaBottom - th)));

    tip.style.left = `${leftAbs - hostRect.left}px`;
    tip.style.top = `${topAbs - hostRect.top}px`;
  }

  function hideTooltip() {
    $("hoverTooltip").classList.add("hidden");
  }

  function row(key, value) {
    const text = FlowUtils.safeText(value, "");
    if (!text || text === "[]" || text === "{}") return "";
    return `<div class="detail-row"><div class="detail-key">${escapeHtml(key)}</div><div class="detail-value">${escapeHtml(text)}</div></div>`;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  return { renderStats, renderNodeList, showNodeDetail, showTooltip, hideTooltip };
})();
