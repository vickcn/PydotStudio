window.FlowGraph = (() => {
  let cy = null;
  let flow = null;
  let selectedId = null;
  let onSelectCallback = null;
  let _zoomRafId = null;

  function getViewerCy() {
    const v = window.__PYDOT_VIEWER__ || {};
    return v.cytoscape_2d || {};
  }

  function parseCssColor(rgb) {
    const s = String(rgb || "").trim();
    let r = 30;
    let g = 41;
    let b = 59;
    if (s.startsWith("#")) {
      let h = s.slice(1);
      if (h.length === 3) {
        r = parseInt(h[0] + h[0], 16);
        g = parseInt(h[1] + h[1], 16);
        b = parseInt(h[2] + h[2], 16);
      } else if (h.length >= 6) {
        r = parseInt(h.slice(0, 2), 16);
        g = parseInt(h.slice(2, 4), 16);
        b = parseInt(h.slice(4, 6), 16);
      }
    }
    return { r, g, b };
  }

  function luminance(rgb) {
    const r = rgb.r / 255;
    const g = rgb.g / 255;
    const b = rgb.b / 255;
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }

  function pickLabelColor(forFillColor) {
    const cfg = getViewerCy();
    const lum = luminance(parseCssColor(forFillColor));
    const th =
      cfg.light_fill_luminance_threshold !== undefined
        ? Number(cfg.light_fill_luminance_threshold)
        : 0.65;
    if (lum >= th) return cfg.node_label_color_on_light_fill || "#0f172a";
    return cfg.node_label_color_on_dark_fill || "#e5e7eb";
  }

  /*
   * 依目前 zoom 值，對超出最小螢幕高度 (node_min_screen_px) 的節點強制放大。
   * 使用 cy.batch() 一次提交，避免多次重排。
   * 懸停中的節點跳過（hover 已自行放大）。
   */
  function enforceMinNodeScreenSize() {
    if (!cy) return;
    const cfg = getViewerCy();
    const minPx =
      cfg.node_min_screen_px !== undefined && Number.isFinite(Number(cfg.node_min_screen_px))
        ? Math.max(0, Number(cfg.node_min_screen_px))
        : 28;
    if (minPx <= 0) return;
    const z = cy.zoom();
    cy.batch(() => {
      cy.nodes().forEach(n => {
        if (n.scratch("_isHovered")) return;
        const natH = n.scratch("_natH");
        const natW = n.scratch("_natW");
        if (natH === undefined || natW === undefined) return;
        const screenH = natH * z;
        if (screenH < minPx) {
          const u = minPx / screenH;
          n.style({ width: natW * u, height: natH * u });
          n.scratch("_minSzActive", true);
        } else if (n.scratch("_minSzActive")) {
          n.style({ width: natW, height: natH });
          n.scratch("_minSzActive", false);
        }
      });
    });
  }

  function init(containerId, onSelect) {
    destroy();
    onSelectCallback = onSelect;
    cy = cytoscape({
      container: document.getElementById(containerId),
      elements: [],
      wheelSensitivity: 0.18,
      style: [
        {
          selector: "node",
          style: {
            "label": "data(label)",
            "text-wrap": "wrap",
            "text-max-width": 190,
            "font-family": "Microsoft JhengHei, Segoe UI, sans-serif",
            "font-size": 12,
            "font-weight": 700,
            "color": "data(labelColor)",
            "background-color": "data(fillcolor)",
            "border-color": "data(color)",
            "border-width": "data(penwidth)",
            "shape": "data(cyShape)",
            "width": "label",
            "height": "label",
            "padding": "16px",
            "text-valign": "center",
            "text-halign": "center",
            "overlay-opacity": 0,
          }
        },
        {
          selector: "edge",
          style: {
            "label": "data(label)",
            "font-family": "Microsoft JhengHei, Segoe UI, sans-serif",
            "font-size": 10,
            "color": "#cbd5e1",
            "text-background-color": "#020617",
            "text-background-opacity": 0.78,
            "text-background-padding": 3,
            "line-color": "#64748b",
            "target-arrow-color": "#64748b",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "width": 1.8,
          }
        },
        {
          selector: ".faded",
          style: { "opacity": 0.16 }
        },
        {
          selector: ".highlighted",
          style: {
            "opacity": 1,
            "border-width": 4,
            "border-color": "#38bdf8",
            "line-color": "#38bdf8",
            "target-arrow-color": "#38bdf8",
            "z-index": 10,
          }
        },
        {
          selector: ".selected",
          style: {
            "border-width": 5,
            "border-color": "#34d399",
            "box-shadow": "0 0 24px #34d399",
          }
        }
      ],
    });

    cy.on("tap", "node", evt => selectNode(evt.target.id(), true));

    cy.on("mouseover", "node", evt => {
      const n = evt.target;
      n.scratch("_isHovered", true);
      // 懸停放大：以自然尺寸 × node_hover_scale
      const natW = n.scratch("_natW") !== undefined ? n.scratch("_natW") : n.width();
      const natH = n.scratch("_natH") !== undefined ? n.scratch("_natH") : n.height();
      if (n.scratch("_natW") === undefined) { n.scratch("_natW", natW); n.scratch("_natH", natH); }
      const cfg = getViewerCy();
      const hs =
        cfg.node_hover_scale !== undefined && Number.isFinite(Number(cfg.node_hover_scale)) && Number(cfg.node_hover_scale) > 0
          ? Number(cfg.node_hover_scale) : 1.6;
      n.stop(true, true);
      n.animate({ style: { width: natW * hs, height: natH * hs }, duration: 180, easing: "ease-out" });
      highlightNeighborhood(n.id());
      FlowPanel.showTooltip(findNode(n.id()), evt.originalEvent.clientX, evt.originalEvent.clientY);
    });

    cy.on("mousemove", "node", evt => {
      FlowPanel.showTooltip(findNode(evt.target.id()), evt.originalEvent.clientX, evt.originalEvent.clientY);
    });

    cy.on("mouseout", "node", evt => {
      const n = evt.target;
      n.scratch("_isHovered", false);
      const natW = n.scratch("_natW");
      const natH = n.scratch("_natH");
      if (natW !== undefined && natH !== undefined) {
        n.stop(true, true);
        // 縮回後立刻重新套用最小尺寸保護
        n.animate({
          style: { width: natW, height: natH },
          duration: 150,
          easing: "ease-out",
          complete: () => { enforceMinNodeScreenSize(); },
        });
      }
      if (selectedId) highlightNeighborhood(selectedId);
      else clearHighlight();
      FlowPanel.hideTooltip();
    });

    cy.on("tap", evt => {
      if (evt.target === cy) {
        selectedId = null;
        clearHighlight();
        if (onSelectCallback) onSelectCallback(null);
      }
    });

    // 最小節點尺寸：zoom 事件用 RAF 節流，避免每幀呼叫
    cy.on("zoom", () => {
      if (_zoomRafId !== null) return;
      _zoomRafId = requestAnimationFrame(() => {
        _zoomRafId = null;
        enforceMinNodeScreenSize();
      });
    });
  }

  function load(newFlow) {
    flow = newFlow;
    selectedId = null;
    if (!cy) return;
    const elements = toElements(newFlow);
    cy.elements().remove();
    cy.add(elements);
    layout();
  }

  function toElements(data) {
    const presets = data.style_presets || {};
    const baseNodeStyle = data.node_style || {};
    const elements = [];

    (data.nodes || []).forEach(n => {
      const style = resolveStyle(n, presets, baseNodeStyle);
      const fill = style.fillcolor || "#1e293b";
      elements.push({
        group: "nodes",
        data: {
          id: n.id,
          label: n.label || n.id,
          groupId: n.group || "",
          fillcolor: fill,
          labelColor: pickLabelColor(fill),
          color: style.color || "#38bdf8",
          penwidth: Number(style.penwidth || 2),
          cyShape: graphvizShapeToCy(style.shape || n.shape || "box"),
          raw: n,
        }
      });
    });

    (data.edges || []).forEach((e, idx) => {
      elements.push({
        group: "edges",
        data: {
          id: `e_${idx}_${e.from}_${e.to}`,
          source: e.from,
          target: e.to,
          label: e.label || "",
          raw: e,
        }
      });
    });
    return elements;
  }

  function resolveStyle(item, presets, base = {}) {
    const refs = Array.isArray(item.style_refs) ? item.style_refs : (item.style_ref ? [item.style_ref] : []);
    const merged = { ...base };
    refs.forEach(ref => Object.assign(merged, presets[ref] || {}));
    ["shape", "style", "fillcolor", "color", "fontcolor", "fontsize", "penwidth"].forEach(k => {
      if (item[k] !== undefined) merged[k] = item[k];
    });
    if (item.attrs && typeof item.attrs === "object") Object.assign(merged, item.attrs);
    return merged;
  }

  function graphvizShapeToCy(shape) {
    const s = String(shape || "").toLowerCase();
    if (s === "diamond") return "diamond";
    if (s === "ellipse" || s === "oval") return "ellipse";
    if (s === "circle") return "ellipse";
    if (s === "hexagon") return "hexagon";
    return "round-rectangle";
  }

  function layout() {
    if (!cy) return;
    const lay = cy.layout({ name: "breadthfirst", directed: true, spacingFactor: 1.35, animate: true, animationDuration: 420 });
    lay.on("layoutstop", () => {
      // 版面完成後存自然尺寸，供 hover 放大與最小尺寸保護使用
      cy.nodes().forEach(n => {
        n.scratch("_natW", n.width());
        n.scratch("_natH", n.height());
        n.scratch("_isHovered", false);
        n.scratch("_minSzActive", false);
      });
      enforceMinNodeScreenSize();
    });
    lay.run();
  }

  function fit() { cy?.fit(undefined, 40); }

  function focusNodeInView(id) {
    if (!cy) return;
    const sid = String(id ?? "");
    if (!sid) return;
    const ele = cy.getElementById(sid);
    if (!ele || ele.empty()) return;
    try {
      cy.animate({
        fit: { eles: ele, padding: 48 },
        duration: 280,
        easing: "ease-out-cubic",
      });
    } catch (ignored) {
      try {
        cy.fit(ele, 48);
      } catch (ignored2) {
        void ignored2;
      }
    }
  }

  function selectNode(id, notify = false) {
    selectedId = id;
    cy.elements().removeClass("selected");
    const ele = cy.getElementById(id);
    ele.addClass("selected");
    highlightNeighborhood(id);
    if (notify && onSelectCallback) onSelectCallback(id);
  }

  function highlightNeighborhood(id) {
    clearHighlight();
    const node = cy.getElementById(id);
    const neighborhood = node.closedNeighborhood();
    cy.elements().not(neighborhood).addClass("faded");
    neighborhood.addClass("highlighted");
    node.addClass("selected");
  }

  function clearHighlight() {
    cy?.elements().removeClass("faded highlighted selected");
  }

  function findNode(id) {
    return (flow?.nodes || []).find(n => n.id === id) || {};
  }

  function destroy() {
    if (_zoomRafId !== null) { cancelAnimationFrame(_zoomRafId); _zoomRafId = null; }
    if (cy) {
      cy.destroy();
      cy = null;
    }
    selectedId = null;
    flow = null;
    onSelectCallback = null;
  }

  return { init, load, layout, fit, selectNode, findNode, focusNodeInView, destroy };
})();
