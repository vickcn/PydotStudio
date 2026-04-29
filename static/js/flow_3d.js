window.FlowGraph3D = (() => {
  let graph = null;
  let flow = null;
  let selectedId = null;
  let onSelectCallback = null;
  let containerEl = null;
  let resizeHandler = null;
  let neighborMap = null;
  let rimArrowRafId = null;
  let rimCtlChangeDetach = null;

  function getViewer() {
    return window.__PYDOT_VIEWER__ || {};
  }

  function getCfg() {
    return getViewer().three_3d || {};
  }

  function linkEndpointId(link, which) {
    const v = which === "target" ? link.target : link.source;
    if (v && typeof v === "object" && v.id !== undefined && v.id !== null) return String(v.id);
    return String(v);
  }

  const _dblNodeL = {};
  const _dblNodeR = {};
  const _dblLinkL = {};
  const _dblLinkR = {};

  let homeNodeId = "";
  let anchorHistory = [];
  let anchorCursor = -1;
  let suspendAnchorPush = false;
  let trackedTextures = [];

  function resetNavigationState() {
    homeNodeId = "";
    anchorHistory = [];
    anchorCursor = -1;
    dispatchNavState();
  }

  function dispatchNavState() {
    try {
      window.dispatchEvent(new CustomEvent("flow3dnav"));
    } catch (ignored) {
      void ignored;
    }
  }

  function hideEdgeOtherTip() {
    const el = document.getElementById("edgeOtherTip");
    if (!el) return;
    el.classList.add("hidden");
    el.innerHTML = "";
  }

  function escHtml3d(t) {
    return String(t ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function showEdgeOtherTipForLink(evt, lnk, sId, tId) {
    if (!graph || !flow || !lnk) return;
    if (typeof graph.graph2ScreenCoords !== "function") return;

    const gs = graph.graph2ScreenCoords;
    const sn = graphDataNodes().find(n => String(n.id) === String(sId));
    const tn = graphDataNodes().find(n => String(n.id) === String(tId));
    if (!sn || !tn) return;

    const mx = typeof evt.clientX === "number" ? evt.clientX : 0;
    const my = typeof evt.clientY === "number" ? evt.clientY : 0;

    const ps = gs(Number(sn.x !== undefined ? sn.x : 0), Number(sn.y !== undefined ? sn.y : 0), Number(sn.z !== undefined ? sn.z : 0));
    const pt = gs(Number(tn.x !== undefined ? tn.x : 0), Number(tn.y !== undefined ? tn.y : 0), Number(tn.z !== undefined ? tn.z : 0));
    if (!ps || !pt) return;

    function d2(px, py) {
      const dx = px - mx;
      const dy = py - my;
      return dx * dx + dy * dy;
    }

    const nearerToSource = d2(ps.x, ps.y) <= d2(pt.x, pt.y);
    const otherId = nearerToSource ? tId : sId;

    const raw = (flow.nodes || []).find(n => String(n.id) === String(otherId)) || {};
    const summary = FlowUtils.nodeSummary(raw) || "";

    const tip = document.getElementById("edgeOtherTip");
    if (!tip) return;

    tip.innerHTML = `
      <div class="edge-tip-head">${escHtml3d(nearerToSource ? "沿箭頭方向 · 另一端節點" : "另一端節點")}</div>
      <div class="edge-tip-id">${escHtml3d(otherId)}</div>
      <div class="edge-tip-title">${escHtml3d(raw.label || otherId)}</div>
      <div class="edge-tip-meta">${escHtml3d(summary || "（無摘要）")}</div>
    `;

    tip.classList.remove("hidden");

    const pad = 14;
    tip.style.left = "0px";
    tip.style.top = "0px";
    const tw = Math.min(340, Math.max(200, tip.offsetWidth || 280));
    let left = mx - tw / 2;
    let top = my - 18;
    left = Math.min(window.innerWidth - tw - pad, Math.max(pad, left));
    top = Math.min(window.innerHeight - 12 - (tip.offsetHeight || 120), Math.max(pad, top - (tip.offsetHeight || 120)));

    tip.style.left = `${Math.round(left)}px`;
    tip.style.top = `${Math.round(top)}px`;
  }

  function initNavigationFromFlow(flowData) {
    resetNavigationState();
    const nodes = flowData?.nodes || [];
    if (nodes.length && nodes[0].id !== undefined && nodes[0].id !== null) {
      homeNodeId = String(nodes[0].id);
      anchorHistory = [homeNodeId];
      anchorCursor = 0;
    }
    dispatchNavState();
  }

  function pushAnchorVisit(nodeId) {
    if (!flow) return;
    if (suspendAnchorPush) return;
    const id = String(nodeId);
    if (!id) return;
    if (anchorHistory.length && anchorHistory[anchorCursor] === id) return;
    anchorHistory.splice(anchorCursor + 1);
    anchorHistory.push(id);
    anchorCursor = anchorHistory.length - 1;
    if (anchorHistory.length > 96) {
      const drop = anchorHistory.length - 96;
      anchorHistory.splice(0, drop);
      anchorCursor = Math.max(0, anchorCursor - drop);
    }
    dispatchNavState();
  }

  function applyNavigationAtCursor() {
    const id = anchorHistory[anchorCursor];
    if (!id || !graph) return;
    suspendAnchorPush = true;
    try {
      selectedId = id;
      refreshDimming();
      if (onSelectCallback) onSelectCallback(id);
      focusViewportOnNodeId(id);
    } finally {
      suspendAnchorPush = false;
    }
    dispatchNavState();
  }

  function navigationGoHome() {
    if (!graph || !homeNodeId) return;
    const ix = anchorHistory.indexOf(homeNodeId);
    if (ix >= 0) {
      anchorCursor = ix;
    } else {
      anchorHistory.unshift(homeNodeId);
      anchorCursor = 0;
    }
    applyNavigationAtCursor();
  }

  function navigationPrev() {
    if (anchorCursor <= 0) return;
    anchorCursor -= 1;
    applyNavigationAtCursor();
  }

  function navigationNext() {
    if (anchorCursor < 0 || anchorCursor >= anchorHistory.length - 1) return;
    anchorCursor += 1;
    applyNavigationAtCursor();
  }

  function getNavigationState() {
    return {
      hasHome: !!homeNodeId,
      canPrev: anchorCursor > 0,
      canNext: anchorCursor >= 0 && anchorCursor < anchorHistory.length - 1,
    };
  }

  function tryConsumeDoubleInteraction(key, evt, store) {
    const k = String(key);
    if (evt && typeof evt.detail === "number" && evt.detail >= 2) {
      delete store[k];
      return true;
    }
    const now = Date.now();
    const prev = store[k];
    if (typeof prev === "number" && now - prev < 450) {
      delete store[k];
      return true;
    }
    store[k] = now;
    return false;
  }

  function firstUpstreamNeighborId(nodeId) {
    const id = String(nodeId);
    for (const e of flow?.edges || []) {
      if (!e) continue;
      if (String(e.to) === id) return String(e.from);
    }
    return "";
  }

  function isLeftButton(evt) {
    if (!evt || typeof evt.button !== "number") return true;
    return evt.button === 0;
  }

  function isRightButton(evt) {
    return evt && typeof evt.button === "number" && evt.button === 2;
  }

  function graphDataNodes() {
    if (!graph || typeof graph.graphData !== "function") return [];
    const gd = graph.graphData();
    return (gd && gd.nodes) || [];
  }

  function pointInViewportInset(px, py, minX, minY, maxX, maxY) {
    return px >= minX - 1e-9 && px <= maxX + 1e-9 && py >= minY - 1e-9 && py <= maxY + 1e-9;
  }

  /*
   * 有限線段 (Ps)-(Pt) 與視窗内框矩形邊界的交點（參數 u 從 Ps 走到 Pt，u in [0,1]）。
   */
  function segmentRectIntersectionsSorted(Px, Py, Tx, Ty, minX, minY, maxX, maxY) {
    const dx = Tx - Px;
    const dy = Ty - Py;
    const tol = 1e-10;
    const map = new Map();

    function addFromU(uRaw) {
      if (!Number.isFinite(uRaw) || uRaw < -1e-6 || uRaw > 1 + 1e-6) return;
      const u = Math.min(1, Math.max(0, uRaw));
      const k = `${u.toFixed(5)}_${Math.round((Px + dx * u) * 100)}_${Math.round((Py + dy * u) * 100)}`;
      if (map.has(k)) return;
      const x = Px + dx * u;
      const y = Py + dy * u;
      map.set(k, { u, x, y });
    }

    if (Math.abs(dx) > tol) {
      for (const X of [minX, maxX]) {
        const u = (X - Px) / dx;
        const y = Py + dy * u;
        if (y >= minY - 1e-5 && y <= maxY + 1e-5) addFromU(u);
      }
    }
    if (Math.abs(dy) > tol) {
      for (const Y of [minY, maxY]) {
        const u = (Y - Py) / dy;
        const x = Px + dx * u;
        if (x >= minX - 1e-5 && x <= maxX + 1e-5) addFromU(u);
      }
    }

    const arr = Array.from(map.values());
    arr.sort((a, b) => a.u - b.u);
    return arr;
  }

  /*
   * 只在「線段穿出主框」時標箭頭：
   * - 兩端都在框內：不標（先前的無限延伸射線會在邊緣到處插箭頭）。
   * - 由 source 往 target：從框內往框外離開時，在離開邊界的那一點畫箭頭。
   * - source 在框外、target 在框內：視為「進入主框」，不標。
   */
  function rimArrowForSegmentTowardTarget(Px, Py, Tx, Ty, minX, minY, maxX, maxY) {
    const dx = Tx - Px;
    const dy = Ty - Py;
    if (!Number.isFinite(dx) || !Number.isFinite(dy)) return null;
    if (dx * dx + dy * dy < 1e-8) return null;

    const insP = pointInViewportInset(Px, Py, minX, minY, maxX, maxY);
    const insT = pointInViewportInset(Tx, Ty, minX, minY, maxX, maxY);
    if (insP && insT) return null;

    const hits = segmentRectIntersectionsSorted(Px, Py, Tx, Ty, minX, minY, maxX, maxY);
    if (!hits.length) return null;

    const angDeg = Math.atan2(dy, dx) * (180 / Math.PI);

    if (insP && !insT) {
      const h0 = hits[0];
      return { x: h0.x, y: h0.y, angDeg };
    }

    if (!insP && insT) {
      return null;
    }

    /*
     * 兩端都在框外：線段若穿過視窗，會有兩個交點；取沿 source→target 較後者（離開框往 target 方向）。
     * 僅單點相接則取該點。
     */
    if (!insP && !insT) {
      if (hits.length >= 2) {
        const last = hits[hits.length - 1];
        return { x: last.x, y: last.y, angDeg };
      }
      return { x: hits[0].x, y: hits[0].y, angDeg };
    }

    return null;
  }

  function linkBezierControlXYZ(sx, sy, sz, tx, ty, tz, curvature) {
    const dx = tx - sx;
    const dy = ty - sy;
    const dz = tz - sz;
    const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1e-6;
    const mx = (sx + tx) * 0.5;
    const my = (sy + ty) * 0.5;
    const mz = (sz + tz) * 0.5;
    let nx = dy * 0 - dz * 1;
    let ny = dz * 0 - dx * 0;
    let nz = dx * 1 - dy * 0;
    let nlen = Math.sqrt(nx * nx + ny * ny + nz * nz);
    if (nlen < 1e-9) {
      // Fallback: cross with X-axis → (0, dz, -dy), valid for Y-axis aligned edges
      nx = 0;
      ny = dz;
      nz = -dy;
      nlen = Math.sqrt(nx * nx + ny * ny + nz * nz);
    }
    if (nlen < 1e-9) {
      return { cx: mx, cy: my, cz: mz };
    }
    nx /= nlen;
    ny /= nlen;
    nz /= nlen;
    const curv =
      curvature !== undefined && curvature !== null && Number.isFinite(Number(curvature))
        ? Number(curvature)
        : 0.14;
    const off = dist * curv;
    return {
      cx: mx + nx * off,
      cy: my + ny * off,
      cz: mz + nz * off
    };
  }

  /*
   * 與視窗連線視覺相近：二階 Bézier（S -> 控制點 -> T），再逐點經 graph2ScreenCoords 投影為螢幕折線。
   */
  function buildLinkScreenPolyline(gs, sn, tn, curvature, segments) {
    const sx = Number(sn.x !== undefined ? sn.x : 0);
    const sy = Number(sn.y !== undefined ? sn.y : 0);
    const sz = Number(sn.z !== undefined ? sn.z : 0);
    const tx = Number(tn.x !== undefined ? tn.x : 0);
    const ty = Number(tn.y !== undefined ? tn.y : 0);
    const tz = Number(tn.z !== undefined ? tn.z : 0);
    const c = linkBezierControlXYZ(sx, sy, sz, tx, ty, tz, curvature);
    const seg = Number.isFinite(segments) ? Math.floor(segments) : 48;
    const n = Math.min(140, Math.max(10, seg));
    const out = [];
    for (let i = 0; i <= n; i += 1) {
      const t = i / n;
      const u = 1 - t;
      const x = u * u * sx + 2 * u * t * c.cx + t * t * tx;
      const y = u * u * sy + 2 * u * t * c.cy + t * t * ty;
      const z = u * u * sz + 2 * u * t * c.cz + t * t * tz;
      const p = gs(x, y, z);
      if (!p || !Number.isFinite(p.x) || !Number.isFinite(p.y)) continue;
      out.push({ x: p.x, y: p.y });
    }
    return out;
  }

  /*
   * 沿螢幕折線從頭往尾搜尋：第一段「框內 -> 框外」的離開點即箭頭位置（貼著與視窗繪製相近的連線）。
   */
  function rimArrowAlongScreenPolyline(pts, minX, minY, maxX, maxY) {
    if (!pts || pts.length < 2) return null;
    for (let i = 0; i < pts.length - 1; i += 1) {
      const Ax = pts[i].x;
      const Ay = pts[i].y;
      const Bx = pts[i + 1].x;
      const By = pts[i + 1].y;
      const insA = pointInViewportInset(Ax, Ay, minX, minY, maxX, maxY);
      const insB = pointInViewportInset(Bx, By, minX, minY, maxX, maxY);
      if (insA && !insB) {
        const h = rimArrowForSegmentTowardTarget(Ax, Ay, Bx, By, minX, minY, maxX, maxY);
        if (h) return h;
      }
    }
    return null;
  }

  function syncRimSvgLayout() {
    const svg = document.getElementById("fg3dViewportRim");
    if (!svg || !containerEl) return;
    svg.style.left = `${containerEl.offsetLeft}px`;
    svg.style.top = `${containerEl.offsetTop}px`;
    svg.style.width = `${containerEl.clientWidth}px`;
    svg.style.height = `${containerEl.clientHeight}px`;
  }

  function stopViewportRimArrows() {
    if (rimArrowRafId !== null) {
      cancelAnimationFrame(rimArrowRafId);
      rimArrowRafId = null;
    }
    if (typeof rimCtlChangeDetach === "function") {
      try {
        rimCtlChangeDetach();
      } catch (ignored) {
        void ignored;
      }
    }
    rimCtlChangeDetach = null;
    const svg = document.getElementById("fg3dViewportRim");
    if (svg) svg.innerHTML = "";
  }

  function updateViewportRimArrowsContent() {
    const svg = document.getElementById("fg3dViewportRim");
    if (!svg || !graph || !containerEl || typeof graph.graph2ScreenCoords !== "function") return;
    const cfg = getCfg();
    if (cfg.viewport_rim_arrows_enabled === false) {
      svg.innerHTML = "";
      return;
    }
    const W = containerEl.clientWidth || 0;
    const H = containerEl.clientHeight || 0;
    if (W < 12 || H < 12) {
      svg.innerHTML = "";
      return;
    }
    const m =
      cfg.viewport_rim_margin !== undefined && cfg.viewport_rim_margin !== null && Number(cfg.viewport_rim_margin) >= 0
        ? Number(cfg.viewport_rim_margin)
        : 6;
    const L = m;
    const T = m;
    const R = W - m;
    const B = H - m;
    if (R <= L + 2 || B <= T + 2) return;

    const gs = graph.graph2ScreenCoords;
    const nodes = graphDataNodes();
    const gd = graph.graphData();
    const links = (gd && gd.links) || [];
    const findNd = id => nodes.find(n => String(n.id) === String(id));

    const focusId =
      selectedId !== undefined && selectedId !== null && String(selectedId).trim() !== ""
        ? String(selectedId)
        : "";
    if (!focusId) {
      svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
      svg.innerHTML = "";
      return;
    }

    const stroke =
      cfg.viewport_rim_arrow_color !== undefined && cfg.viewport_rim_arrow_color !== null
        ? String(cfg.viewport_rim_arrow_color)
        : "#fb7185";
    const sw =
      cfg.viewport_rim_arrow_stroke !== undefined && cfg.viewport_rim_arrow_stroke !== null
        ? Number(cfg.viewport_rim_arrow_stroke)
        : 2.6;
    const tip =
      cfg.viewport_rim_arrow_tip !== undefined && cfg.viewport_rim_arrow_tip !== null
        ? Number(cfg.viewport_rim_arrow_tip)
        : 11;

    const parts = [];
    for (let i = 0; i < links.length; i += 1) {
      const Lk = links[i];
      if (!Lk) continue;
      const sId = linkEndpointId(Lk, "source");
      const tId = linkEndpointId(Lk, "target");
      if (String(sId) !== focusId) continue;
      const sn = findNd(sId);
      const tn = findNd(tId);
      if (!sn || !tn) continue;
      const curvature =
        cfg.link_curvature !== undefined && cfg.link_curvature !== null && Number.isFinite(Number(cfg.link_curvature))
          ? Number(cfg.link_curvature)
          : 0.14;
      const rimSegRaw =
        cfg.viewport_rim_link_segments !== undefined && cfg.viewport_rim_link_segments !== null
          ? Number(cfg.viewport_rim_link_segments)
          : 48;
      const samples = buildLinkScreenPolyline(gs, sn, tn, curvature, rimSegRaw);
      if (samples.length < 2) continue;
      const hit = rimArrowAlongScreenPolyline(samples, L, T, R, B);
      if (!hit) continue;
      const cx = hit.x;
      const cy = hit.y;
      const ang = hit.angDeg;
      const h = tip;
      const w = tip * 0.95;
      parts.push(
        `<g transform="translate(${cx.toFixed(2)},${cy.toFixed(2)}) rotate(${ang.toFixed(2)})">` +
          `<path d="M 0 0 L ${(-w).toFixed(2)} ${(-h * 0.55).toFixed(2)} L ${(-w).toFixed(2)} ${(h * 0.55).toFixed(2)} Z" ` +
          `fill="none" stroke="${stroke}" stroke-width="${sw}" stroke-linejoin="round" stroke-linecap="round" />` +
          `</g>`
      );
    }

    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("preserveAspectRatio", "none");
    svg.innerHTML = parts.join("");
  }

  function startViewportRimArrowsLoop() {
    stopViewportRimArrows();
    function tick() {
      rimArrowRafId = requestAnimationFrame(tick);
      syncRimSvgLayout();
      updateViewportRimArrowsContent();
    }
    rimArrowRafId = requestAnimationFrame(tick);
    if (graph && typeof graph.controls === "function") {
      const ctl = graph.controls();
      if (ctl && typeof ctl.addEventListener === "function") {
        const fn = () => {
          syncRimSvgLayout();
          updateViewportRimArrowsContent();
        };
        ctl.addEventListener("change", fn);
        rimCtlChangeDetach = () => {
          if (ctl && typeof ctl.removeEventListener === "function") ctl.removeEventListener("change", fn);
        };
      }
    }
  }

  /**
   * 雙擊聚焦：將選中的框拉到視線前。
   * 目標張角對應九宮「正中格」：直立方向約佔視窗 1/3（focus_target_screen_fraction，預設 1/3）。
   * focus_apparent_zoom：縮短相機距離，約略依比例放大「螢幕上所見」節點（預設 2.5）。
   */
  function focusViewportOnNodeId(nodeId) {
    if (!graph || !containerEl) return;
    const idStr = String(nodeId);
    const cfg = getCfg();
    const ms = cfg.focus_transition_ms !== undefined ? Number(cfg.focus_transition_ms) : 920;

    const ndRaw = graphDataNodes().find(n => String(n.id) === idStr);
    if (!ndRaw) return;

    resize();

    const tx = ndRaw.x !== undefined && ndRaw.x !== null ? Number(ndRaw.x) : 0;
    const ty = ndRaw.y !== undefined && ndRaw.y !== null ? Number(ndRaw.y) : 0;
    const tz = ndRaw.z !== undefined && ndRaw.z !== null ? Number(ndRaw.z) : 0;
    if (typeof THREE === "undefined") {
      try {
        if (typeof graph.zoomToFit === "function") graph.zoomToFit(ms, 60);
      } catch (ignored) {
        void ignored;
      }
      return;
    }

    try {
      const cam = typeof graph.camera === "function" ? graph.camera() : null;
      if (!cam || !cam.position) {
        fallbackFocusRadial(idStr);
        return;
      }

      const fracRaw =
        cfg.focus_target_screen_fraction !== undefined ? Number(cfg.focus_target_screen_fraction) : 1 / 3;

      const spriteHRaw =
        cfg.focus_sprite_world_extent !== undefined ? Number(cfg.focus_sprite_world_extent) : 40;

      const minSepRaw =
        cfg.focus_min_cam_separation !== undefined ? Number(cfg.focus_min_cam_separation) : 26;

      const maxInRatioRaw =
        cfg.focus_zoom_in_hard_cap_ratio !== undefined
          ? Number(cfg.focus_zoom_in_hard_cap_ratio)
          : 0.985;

      const boostRaw =
        cfg.focus_viewport_boost !== undefined ? Number(cfg.focus_viewport_boost) : 1.22;

      const frac = Number.isFinite(fracRaw) && fracRaw > 0 ? Math.min(Math.max(fracRaw, 0.08), 0.92) : 1 / 3;

      const spriteH = Number.isFinite(spriteHRaw) && spriteHRaw > 1 ? spriteHRaw : 40;

      const minSep = Number.isFinite(minSepRaw) && minSepRaw > 1 ? minSepRaw : 26;

      const maxInRatio =
        Number.isFinite(maxInRatioRaw) && maxInRatioRaw > 0 && maxInRatioRaw <= 1 ? maxInRatioRaw : 0.985;

      const vpBoost = Number.isFinite(boostRaw) && boostRaw > 0.2 ? Math.min(boostRaw, 3) : 1.22;

      const aptZoomRaw =
        cfg.focus_apparent_zoom !== undefined && cfg.focus_apparent_zoom !== null
          ? Number(cfg.focus_apparent_zoom)
          : 2.5;
      const aptZoom =
        Number.isFinite(aptZoomRaw) && aptZoomRaw > 0.05 ? Math.min(Math.max(aptZoomRaw, 0.2), 10) : 2.5;

      let fovDeg = 50;
      if (typeof cam.fov === "number") fovDeg = cam.fov;
      const fovy = THREE.MathUtils.degToRad(fovDeg);
      const tanHalf = Math.max(Math.tan(fovy / 2), 0.012);

      const tgt = new THREE.Vector3(tx, ty, tz);

      let desiredSep = spriteH / (2 * frac * tanHalf);

      desiredSep /= vpBoost;

      desiredSep /= aptZoom;

      const minSepAdjusted = Number.isFinite(minSep) ? minSep / aptZoom : 26 / aptZoom;

      const curr = cam.position.clone();
      const offset = curr.clone().sub(tgt);

      let dir = offset.clone();

      if (dir.lengthSq() < 1e-8) {
        dir.set(80, 140, 240);
      }

      dir.normalize();

      const sepCurr = curr.distanceTo(tgt);
      desiredSep = Math.min(desiredSep, sepCurr * maxInRatio);
      desiredSep = Math.max(desiredSep, minSepAdjusted);

      const newPos = tgt.clone().addScaledVector(dir, desiredSep);

      if (typeof graph.cameraPosition === "function") {
        graph.cameraPosition(
          { x: newPos.x, y: newPos.y, z: newPos.z },
          { x: tgt.x, y: tgt.y, z: tgt.z },
          ms
        );
      }

      if (typeof graph.controls === "function") {
        const ctl = graph.controls();
        if (ctl && ctl.target && typeof ctl.target.set === "function") {
          ctl.target.set(tgt.x, tgt.y, tgt.z);
          if (typeof ctl.update === "function") ctl.update();
        }
      }
    } catch (ignored) {
      void ignored;
      fallbackFocusRadial(idStr);
    }
  }

  function fallbackFocusRadial(nodeId) {
    try {
      const nd = graphDataNodes().find(n => String(n.id) === String(nodeId));
      if (!nd) return;
      const nx = Number(nd.x !== undefined ? nd.x : 0);
      const ny = Number(nd.y !== undefined ? nd.y : 0);
      const nz = Number(nd.z !== undefined ? nd.z : 0);
      const cfg = getCfg();
      const extra =
        cfg.focus_fallback_distance_extra !== undefined ? Number(cfg.focus_fallback_distance_extra) : 108;
      const aptZoomRaw =
        cfg.focus_apparent_zoom !== undefined && cfg.focus_apparent_zoom !== null
          ? Number(cfg.focus_apparent_zoom)
          : 2.5;
      const aptZoom =
        Number.isFinite(aptZoomRaw) && aptZoomRaw > 0.05 ? Math.min(Math.max(aptZoomRaw, 0.2), 10) : 2.5;
      const hyp = Math.max(Math.hypot(nx, ny, nz), 1e-3);
      const distRatio = 1 + extra / (hyp * aptZoom);
      const newPos = { x: nx * distRatio, y: ny * distRatio, z: nz * distRatio };
      const ms = cfg.focus_transition_ms !== undefined ? Number(cfg.focus_transition_ms) : 920;
      if (typeof graph.cameraPosition === "function") {
        graph.cameraPosition(newPos, { x: nx, y: ny, z: nz }, ms);
      }
    } catch (ignored) {
      void ignored;
    }
  }

  function resolveStyle(item, presets, baseNodeStyle = {}) {
    const presetsResolved = presets || {};
    const base = flow?.node_style || {};
    const mergedBase = Object.assign({}, baseNodeStyle || base);
    const refs = Array.isArray(item.style_refs) ? item.style_refs : item.style_ref ? [item.style_ref] : [];
    const merged = { ...mergedBase };
    refs.forEach(ref => Object.assign(merged, presetsResolved[ref] || {}));
    ["shape", "style", "fillcolor", "color", "fontcolor", "fontsize", "penwidth"].forEach(k => {
      if (item[k] !== undefined) merged[k] = item[k];
    });
    if (item.attrs && typeof item.attrs === "object") Object.assign(merged, item.attrs);
    return merged;
  }

  function egoPlusNeighbors(fid) {
    const key = fid !== undefined && fid !== null ? String(fid) : "";
    if (!key || !neighborMap) return null;
    const set = new Set([key]);
    const nb = neighborMap[key];
    if (nb) nb.forEach(x => set.add(String(x)));
    return set;
  }

  function buildNeighborMap(f) {
    const map = {};
    for (const n of f.nodes || []) {
      if (n.id !== undefined && n.id !== null) map[String(n.id)] = new Set();
    }
    for (const e of f.edges || []) {
      const a = e.from !== undefined && e.from !== null ? String(e.from) : "";
      const b = e.to !== undefined && e.to !== null ? String(e.to) : "";
      if (!a || !b) continue;
      if (!map[a]) map[a] = new Set();
      if (!map[b]) map[b] = new Set();
      map[a].add(b);
      map[b].add(a);
    }
    return map;
  }

  function coerceForceGraphCtor() {
    if (typeof ForceGraph3D === "function") return ForceGraph3D;
    if (window.ForceGraph3D && typeof window.ForceGraph3D === "function") return window.ForceGraph3D;
    return null;
  }

  function makeSprite(node) {
    const cfg = getCfg();
    const opacity = cfg.node_background_opacity !== undefined ? Number(cfg.node_background_opacity) : 0.4;
    const labelColor = cfg.node_label_color || "#0f172a";
    const borderColor = node.borderCss || cfg.node_border_color || "#38bdf8";
    const label = node.labelText || "";
    const minW = Number(cfg.sprite_min_width || 120);
    const baseH = Number(cfg.sprite_height || 44);
    const padX = Number(cfg.sprite_padding_x || 18);
    const fs = Number(cfg.sprite_font_size_px || 13);
    const font = cfg.sprite_font_family || "Microsoft JhengHei, Segoe UI, sans-serif";

    if (typeof THREE === "undefined") {
      return null;
    }

    const pixelRatio = Math.min(2, window.devicePixelRatio || 1);
    const scratch = document.createElement("canvas");
    const ctx = scratch.getContext("2d");
    ctx.font = `700 ${fs}px ${font}`;
    const maxTextW = 520;
    const lines = wrapLabelLines(ctx, label, maxTextW);
    const widest = Math.max(...lines.map(t => ctx.measureText(t).width), 24);
    const w = Math.max(minW, Math.ceil(widest + padX * 2));
    const lh = fs + 5;
    const h = Math.max(baseH, Math.ceil(lines.length * lh + 18));

    const canvas = document.createElement("canvas");
    canvas.width = Math.ceil(w * pixelRatio);
    canvas.height = Math.ceil(h * pixelRatio);
    const cctx = canvas.getContext("2d");
    cctx.scale(pixelRatio, pixelRatio);
    const r = 14;
    roundedRectFillStroke(
      cctx,
      1,
      1,
      w - 2,
      h - 2,
      r,
      `rgba(255,255,255,${opacity})`,
      borderColor,
      2
    );
    cctx.fillStyle = labelColor;
    cctx.font = `700 ${fs}px ${font}`;
    cctx.textAlign = "center";
    cctx.textBaseline = "middle";
    const strokeW = cfg.label_text_stroke_width_px !== undefined ? Number(cfg.label_text_stroke_width_px) : 2.75;
    const strokeCol = cfg.label_text_stroke_color !== undefined ? String(cfg.label_text_stroke_color) : "#000000";
    const startY = h / 2 - ((lines.length - 1) * lh) / 2;
    cctx.strokeStyle = strokeCol;
    cctx.lineJoin = "round";
    cctx.lineCap = "round";
    lines.forEach((line, idx) => {
      cctx.lineWidth = strokeW;
      cctx.strokeText(line, w / 2, startY + idx * lh);
      cctx.fillText(line, w / 2, startY + idx * lh);
    });

    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    trackedTextures.push(texture);
    const mat = new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false });
    const sprite = new THREE.Sprite(mat);
    /*
     * Sprite 的世界座標縮放必須與 canvas（纹理）長寬比一致，否則會非等比例拉伸。
     * 先前分別用 w/130、h/44 再乘同一倍率，會讓扁寛框在 3D 裡變成接近正方形，字看起來横向往內擠成「窄窄的」。
     * 改為單一參考邊長 ref，使 scaleX : scaleY = w : h。
     */
    const refPx =
      cfg.sprite_aspect_ref_px !== undefined && cfg.sprite_aspect_ref_px !== null && Number(cfg.sprite_aspect_ref_px) > 8
        ? Number(cfg.sprite_aspect_ref_px)
        : 130;
    const baseScale =
      cfg.sprite_world_scale_base !== undefined && cfg.sprite_world_scale_base !== null && Number(cfg.sprite_world_scale_base) > 0
        ? Number(cfg.sprite_world_scale_base)
        : 11.5;
    const minSide =
      cfg.sprite_world_min_side !== undefined && cfg.sprite_world_min_side !== null && Number(cfg.sprite_world_min_side) > 0
        ? Number(cfg.sprite_world_min_side)
        : 0.78;
    let sx = (w / refPx) * baseScale;
    let sy = (h / refPx) * baseScale;
    const minScaled = Math.min(sx, sy);
    if (minScaled < minSide && minScaled > 0) {
      const u = minSide / minScaled;
      sx *= u;
      sy *= u;
    }
    sprite.scale.set(sx, sy, 1);
    sprite.userData.texture = texture;
    return sprite;
  }

  function roundedRectFillStroke(ctx, x, y, w, h, r, fill, stroke, lineW) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
    ctx.fillStyle = fill;
    ctx.fill();
    ctx.strokeStyle = stroke;
    ctx.lineWidth = lineW;
    ctx.stroke();
  }

  function wrapLabelLines(ctx, text, maxWidth) {
    const s = String(text || "").trim();
    if (!s) return [""];
    if (!/\s/.test(s)) {
      const lines = [];
      let buf = "";
      for (let i = 0; i < s.length; i += 1) {
        const ch = s[i];
        const tryLine = buf + ch;
        if (ctx.measureText(tryLine).width <= maxWidth || !buf) buf = tryLine;
        else {
          lines.push(buf);
          buf = ch;
        }
      }
      if (buf) lines.push(buf);
      return lines.length ? lines : [s];
    }
    const words = s.split(/\s+/);
    const lines = [];
    let line = "";
    for (let i = 0; i < words.length; i += 1) {
      const w = words[i];
      const tryLine = line ? `${line} ${w}` : w;
      if (ctx.measureText(tryLine).width <= maxWidth || !line) {
        line = tryLine;
      } else {
        lines.push(line);
        line = w;
      }
    }
    if (line) lines.push(line);
    return lines;
  }

  function applyDynamics() {
    if (!graph) return;
    const cfg = getCfg();
    graph.d3VelocityDecay(Number(cfg.velocity_decay !== undefined ? cfg.velocity_decay : 0.22));
    if (graph.d3AlphaDecay) graph.d3AlphaDecay(Number(cfg.alpha_decay !== undefined ? cfg.alpha_decay : 0.015));
    const charge = graph.d3Force("charge");
    if (charge && typeof charge.strength === "function") {
      charge.strength(Number(cfg.charge_strength !== undefined ? cfg.charge_strength : -140));
    }
    const linkForce = graph.d3Force("link");
    if (linkForce && linkForce.distance) {
      linkForce.distance(Number(cfg.link_distance !== undefined ? cfg.link_distance : 56));
    }
    const center = graph.d3Force("center");
    if (center && typeof center.strength === "function") {
      const cs = cfg.center_strength !== undefined ? Number(cfg.center_strength) : 0.04;
      center.strength(cs);
    }
  }

  function refreshDimming() {
    if (!graph) return;
    const cfg = getCfg();
    const baseEdge = cfg.link_opacity !== undefined ? Number(cfg.link_opacity) : 0.88;
    const set = egoPlusNeighbors(selectedId);
    graph.nodeOpacity(n => {
      if (!set) return 1;
      const id =
        n && (n.id !== undefined && n.id !== null) ? String(n.id) : String(n.__id || "");
      return set.has(id) ? 1 : 0.12;
    });
    graph.linkOpacity(link => {
      if (!selectedId) return baseEdge;
      const sId = typeof link.source === "object" ? link.source.id : link.source;
      const tId = typeof link.target === "object" ? link.target.id : link.target;
      const a = String(sId);
      const b = String(tId);
      const touches = set && (set.has(a) || set.has(b));
      return touches ? baseEdge : baseEdge * 0.12;
    });
    try {
      if (graph && typeof graph.refresh === "function") graph.refresh();
    } catch (ignored) {
      void ignored;
    }
  }

  function teardownGraphDom() {
    stopViewportRimArrows();
    trackedTextures.forEach(t => { try { t.dispose(); } catch (ignored) { void ignored; } });
    trackedTextures = [];
    if (graph) {
      try {
        if (typeof graph._destructor === "function") graph._destructor();
      } catch (ignored) {
        void ignored;
      }
      graph = null;
    }
    if (containerEl) {
      containerEl.innerHTML = "";
    }
  }

  function resize() {
    if (!containerEl || !graph) return;
    const w = containerEl.clientWidth || 720;
    const h = containerEl.clientHeight || 520;
    graph.width(w);
    graph.height(h);
  }

  function init(containerId, onSelect) {
    destroy();
    onSelectCallback = onSelect;
    containerEl = document.getElementById(containerId);
    resizeHandler = () => {
      resize();
      syncRimSvgLayout();
      updateViewportRimArrowsContent();
    };
    window.addEventListener("resize", resizeHandler);
  }

  function load(newFlow) {
    teardownGraphDom();
    flow = newFlow;
    neighborMap = buildNeighborMap(newFlow);
    selectedId = null;
    if (!containerEl) return;

    const FG = coerceForceGraphCtor();
    if (!FG) {
      containerEl.innerHTML = `<div class="empty-state" style="padding:22px;">3D：找不到 ForceGraph3D（請確認已載入 3d-force-graph）</div>`;
      return;
    }

    const cfg = getCfg();
    const presets = newFlow.style_presets || {};
    const baseNs = Object.assign({}, newFlow.node_style || {});

    const nodesRaw = [];
    for (const n of newFlow.nodes || []) {
      const st = resolveStyle(n, presets, baseNs);
      const borderCss = String(st.color || "#38bdf8");
      nodesRaw.push({
        id: String(n.id),
        labelText: n.label ? String(n.label) : String(n.id),
        borderCss: borderCss,
        raw: n
      });
    }

    const links = [];
    (newFlow.edges || []).forEach((e, idx) => {
      if (!e || !e.from || !e.to) return;
      links.push({
        source: String(e.from),
        target: String(e.to),
        uid: `e_${idx}_${e.from}_${e.to}`
      });
    });

    const bg = cfg.background_color !== undefined ? String(cfg.background_color) : "#050816";
    const wBox = Math.max(320, containerEl.clientWidth || containerEl.offsetParent?.clientWidth || 0, 720);
    const hBox = Math.max(240, containerEl.clientHeight || containerEl.offsetParent?.clientHeight || 0, 520);

    graph = FG()(containerEl);
    if (typeof graph.width === "function") graph.width(wBox);
    if (typeof graph.height === "function") graph.height(hBox);

    graph
      .graphData({
        nodes: nodesRaw.map(x => ({
          id: x.id,
          labelText: x.labelText,
          borderCss: x.borderCss
        })),
        links
      })
      .nodeId("id");

    if (typeof graph.linkSource === "function") graph.linkSource("source");
    if (typeof graph.linkTarget === "function") graph.linkTarget("target");
    if (typeof graph.backgroundColor === "function") graph.backgroundColor(bg);

    graph.linkOpacity(cfg.link_opacity !== undefined ? Number(cfg.link_opacity) : 0.88);
    graph.linkColor(() => cfg.link_color || "#64748b");
    if (typeof graph.linkDirectionalParticles === "function") {
      graph.linkDirectionalParticles(cfg.show_particles ? 4 : 0);
    }
    const arrLen = cfg.link_directional_arrow_length !== undefined ? Number(cfg.link_directional_arrow_length) : 10;
    const arrRel = cfg.link_directional_arrow_rel_pos !== undefined ? Number(cfg.link_directional_arrow_rel_pos) : 0.85;
    const baseLinkColor = cfg.link_color || "#64748b";
    const arrColor = cfg.link_directional_arrow_color !== undefined ? String(cfg.link_directional_arrow_color) : "#94a3b8";
    if (typeof graph.linkDirectionalArrowLength === "function") graph.linkDirectionalArrowLength(arrLen);
    if (typeof graph.linkDirectionalArrowRelPos === "function") graph.linkDirectionalArrowRelPos(arrRel);
    if (typeof graph.linkDirectionalArrowColor === "function") graph.linkDirectionalArrowColor(() => arrColor);
    if (typeof graph.linkCurvature === "function") graph.linkCurvature(cfg.link_curvature !== undefined ? Number(cfg.link_curvature) : 0.14);
    if (typeof graph.linkWidth === "function") graph.linkWidth(0.72);

    if (cfg.warmup_ticks !== undefined && typeof graph.warmupTicks === "function") {
      graph.warmupTicks(Number(cfg.warmup_ticks));
    }
    if (cfg.cooldown_ticks !== undefined && typeof graph.cooldownTicks === "function") {
      graph.cooldownTicks(Number(cfg.cooldown_ticks));
    }

    graph.nodeThreeObject(n => {
      try {
        const s = makeSprite(n);
        if (s) return s;
      } catch (ignored) {
        void ignored;
      }
      return null;
    });
    if (typeof graph.nodeThreeObjectExtend === "function") graph.nodeThreeObjectExtend(false);

    applyDynamics();

    graph.onBackgroundClick(() => {
      hideEdgeOtherTip();
      selectedId = null;
      refreshDimming();
      Object.keys(_dblNodeL).forEach(k => delete _dblNodeL[k]);
      Object.keys(_dblNodeR).forEach(k => delete _dblNodeR[k]);
      Object.keys(_dblLinkL).forEach(k => delete _dblLinkL[k]);
      Object.keys(_dblLinkR).forEach(k => delete _dblLinkR[k]);
      if (onSelectCallback) onSelectCallback(null);
    });

    graph.onNodeClick((node, evt) => {
      if (!isLeftButton(evt)) return;
      const id =
        node && (node.id !== undefined && node.id !== null) ? String(node.id) : String(node.__id || "");
      hideEdgeOtherTip();
      selectedId = id;
      refreshDimming();
      if (onSelectCallback) onSelectCallback(id);

      const d = evt && typeof evt.detail === "number" ? evt.detail : 1;
      if (d <= 1) pushAnchorVisit(id);

      if (node && tryConsumeDoubleInteraction(`nodeL:${id}`, evt, _dblNodeL)) {
        focusViewportOnNodeId(id);
      }
    });

    graph.onNodeRightClick((node, evt) => {
      if (!evt || !isRightButton(evt)) return;
      if (evt.cancelable) evt.preventDefault();
      if (typeof evt.stopPropagation === "function") evt.stopPropagation();
      if (!node) return;
      const id =
        node && (node.id !== undefined && node.id !== null) ? String(node.id) : String(node.__id || "");
      const prevId = firstUpstreamNeighborId(id);
      if (!prevId) return;

      if (tryConsumeDoubleInteraction(`nodeR:${id}`, evt, _dblNodeR)) {
        selectedId = prevId;
        refreshDimming();
        if (onSelectCallback) onSelectCallback(prevId);
        pushAnchorVisit(prevId);
        focusViewportOnNodeId(prevId);
      }
    });

    graph.onLinkClick((lnk, evt) => {
      if (!isLeftButton(evt)) return;
      if (!lnk) return;
      const sId = linkEndpointId(lnk, "source");
      const tId = linkEndpointId(lnk, "target");
      const lk = `${sId}>>${tId}`;

      if (evt && evt.detail >= 2) {
        hideEdgeOtherTip();
      } else {
        showEdgeOtherTipForLink(evt, lnk, sId, tId);
      }

      if (tryConsumeDoubleInteraction(`linkL:${lk}`, evt, _dblLinkL)) {
        selectedId = tId;
        refreshDimming();
        if (onSelectCallback) onSelectCallback(tId);
        pushAnchorVisit(tId);
        focusViewportOnNodeId(tId);
      }
    });

    graph.onLinkRightClick((lnk, evt) => {
      if (!evt || !isRightButton(evt)) return;
      if (evt.cancelable) evt.preventDefault();
      if (!lnk) return;
      const sId = linkEndpointId(lnk, "source");
      const tId = linkEndpointId(lnk, "target");
      const lk = `${sId}>>${tId}`;

      if (tryConsumeDoubleInteraction(`linkR:${lk}`, evt, _dblLinkR)) {
        selectedId = sId;
        refreshDimming();
        if (onSelectCallback) onSelectCallback(sId);
        pushAnchorVisit(sId);
        focusViewportOnNodeId(sId);
      }
    });

    resize();
    refreshDimming();
    const zf = () => {
      resize();
      try {
        if (graph && typeof graph.zoomToFit === "function") graph.zoomToFit(520, 48);
      } catch (ignored) {
        void ignored;
      }
    };
    requestAnimationFrame(() => {
      zf();
      requestAnimationFrame(zf);
    });
    setTimeout(zf, 180);

    initNavigationFromFlow(newFlow);
    syncRimSvgLayout();
    startViewportRimArrowsLoop();
  }

  function layout() {
    if (!graph || !flow) return;
    try {
      if (typeof graph.d3ReheatSimulation === "function") graph.d3ReheatSimulation();
      else if (typeof graph.refresh === "function") graph.refresh();
    } catch (ignored) {
      void ignored;
    }
    applyDynamics();
    try {
      if (typeof graph.resumeAnimation === "function") graph.resumeAnimation();
    } catch (ignored2) {
      void ignored2;
    }
  }

  function fit() {
    if (!graph || !containerEl) return;
    resize();
    try {
      graph.zoomToFit(480, 40);
    } catch (ignored) {
      void ignored;
    }
    syncRimSvgLayout();
    updateViewportRimArrowsContent();
  }

  function selectNode(id, notify = false) {
    selectedId = String(id || "");
    refreshDimming();
    if (notify && onSelectCallback) onSelectCallback(selectedId);
  }

  function focusNodeInView(nodeId) {
    if (!graph) return;
    const id = String(nodeId ?? "");
    if (!id) return;
    pushAnchorVisit(id);
    focusViewportOnNodeId(id);
  }

  function findNode(id) {
    return (flow?.nodes || []).find(n => String(n.id) === String(id)) || {};
  }

  function destroy() {
    if (resizeHandler) {
      window.removeEventListener("resize", resizeHandler);
      resizeHandler = null;
    }
    teardownGraphDom();
    selectedId = null;
    flow = null;
    neighborMap = null;
    Object.keys(_dblNodeL).forEach(k => {
      delete _dblNodeL[k];
    });
    Object.keys(_dblNodeR).forEach(k => {
      delete _dblNodeR[k];
    });
    Object.keys(_dblLinkL).forEach(k => {
      delete _dblLinkL[k];
    });
    Object.keys(_dblLinkR).forEach(k => {
      delete _dblLinkR[k];
    });
    hideEdgeOtherTip();
    resetNavigationState();
    onSelectCallback = null;
    containerEl = null;
  }

  return {
    init,
    load,
    layout,
    fit,
    selectNode,
    findNode,
    focusNodeInView,
    destroy,
    navigationGoHome,
    navigationPrev,
    navigationNext,
    getNavigationState
  };
})();
