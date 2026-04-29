(() => {
  let currentFlow = null;
  let currentFileName = "pydot_flow.json";
  let activeId = null;
  let viewDriver = null;

  const $ = (id) => document.getElementById(id);

  document.addEventListener("DOMContentLoaded", () => {
    void bootstrap();
  });

  async function bootstrap() {
    try {
      window.__PYDOT_VIEWER__ = await FlowAPI.viewerConfig();
    } catch (err) {
      window.__PYDOT_VIEWER__ = {};
      console.warn("viewer-config failed", err);
    }
    bindModeUi();
    applyMode(normalizeMode(window.__PYDOT_VIEWER__.default_render_mode));
    bindEvents();
    window.addEventListener("flow3dnav", () => updateGraphNavButtons());
  }

  function normalizeMode(m) {
    const s = String(m || "").toLowerCase();
    if (s === "three_3d" || s === "3d") return "three_3d";
    return "cytoscape_2d";
  }

  function bindModeUi() {
    const sel = $("renderModeSelect");
    if (!sel) return;
    sel.value = normalizeMode(window.__PYDOT_VIEWER__.default_render_mode) === "three_3d" ? "three_3d" : "cytoscape_2d";
    sel.addEventListener("change", () => {
      applyMode(normalizeMode(sel.value));
      if (currentFlow) reloadCurrentFlow();
    });
  }

  function applyMode(modeRaw) {
    const mode = normalizeMode(modeRaw);
    const cyEl = $("cy");
    const g3El = $("fg3d");
    if (cyEl) cyEl.classList.toggle("hidden", mode === "three_3d");
    if (g3El) g3El.classList.toggle("hidden", mode !== "three_3d");
    const navOv = $("graphNavOverlay");
    if (navOv) navOv.classList.toggle("hidden", mode !== "three_3d");
    const rim = $("fg3dViewportRim");
    if (rim) rim.classList.toggle("hidden", mode !== "three_3d");
    FlowGraph.destroy();
    FlowGraph3D.destroy();
    if (mode === "three_3d") {
      FlowGraph3D.init("fg3d", handleSelectNode);
      viewDriver = FlowGraph3D;
    } else {
      FlowGraph.init("cy", handleSelectNode);
      viewDriver = FlowGraph;
    }
    updateGraphNavButtons();
  }

  function updateGraphNavButtons() {
    const ov = $("graphNavOverlay");
    if (!ov || ov.classList.contains("hidden")) return;
    const st =
      viewDriver && typeof viewDriver.getNavigationState === "function"
        ? viewDriver.getNavigationState()
        : null;
    const prevBtn = $("btnNavPrev");
    const nextBtn = $("btnNavNext");
    const homeBtn = $("btnNavHome");
    if (!prevBtn || !nextBtn || !homeBtn) return;
    if (!st) {
      prevBtn.disabled = true;
      nextBtn.disabled = true;
      homeBtn.disabled = true;
      return;
    }
    prevBtn.disabled = !st.canPrev;
    nextBtn.disabled = !st.canNext;
    homeBtn.disabled = !st.hasHome;
  }

  function bindEvents() {
    $("jsonFileInput").addEventListener("change", handleFileLoad);
    $("searchInput").addEventListener("input", () => refreshNodeList());
    $("btnFit").addEventListener("click", () => safeViewFit());
    $("btnLayout").addEventListener("click", () => safeViewLayout());
    $("btnRenderSvg").addEventListener("click", renderSvgPreview);
    $("btnDownloadJson").addEventListener("click", () => {
      if (!currentFlow) return;
      FlowUtils.downloadText(currentFileName.replace(/\.json$/i, "") + ".edited.json", JSON.stringify(currentFlow, null, 2));
    });
    const h = $("btnNavHome");
    const p = $("btnNavPrev");
    const n = $("btnNavNext");
    if (h) {
      h.addEventListener("click", () => {
        if (!viewDriver || typeof viewDriver.navigationGoHome !== "function") return;
        viewDriver.navigationGoHome();
        updateGraphNavButtons();
      });
    }
    if (p) {
      p.addEventListener("click", () => {
        if (!viewDriver || typeof viewDriver.navigationPrev !== "function") return;
        viewDriver.navigationPrev();
        updateGraphNavButtons();
      });
    }
    if (n) {
      n.addEventListener("click", () => {
        if (!viewDriver || typeof viewDriver.navigationNext !== "function") return;
        viewDriver.navigationNext();
        updateGraphNavButtons();
      });
    }
  }

  function safeViewFit() {
    if (viewDriver && typeof viewDriver.fit === "function") viewDriver.fit();
  }

  function safeViewLayout() {
    if (viewDriver && typeof viewDriver.layout === "function") viewDriver.layout();
  }

  async function handleFileLoad(evt) {
    const file = evt.target.files?.[0];
    if (!file) return;
    currentFileName = file.name;
    const text = await file.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch (err) {
      alert("JSON 解析失敗：" + err.message);
      return;
    }
    try {
      const errors = FlowUtils.validateFlow(data);
      if (errors.length) {
        alert("Flow JSON 格式有疑慮：\n" + errors.slice(0, 12).join("\n"));
      }
      currentFlow = data;
      activeId = null;
      FlowPanel.renderStats(currentFlow);
      reloadCurrentFlow();
    } catch (err) {
      alert("套用流程到畫面時發生錯誤：" + err.message);
    }
  }

  function reloadCurrentFlow() {
    if (!currentFlow) return;
    if (!viewDriver) return;
    viewDriver.load(currentFlow);
    refreshNodeList();
    const sel = $("renderModeSelect");
    const mode = sel ? normalizeMode(sel.value) : normalizeMode(window.__PYDOT_VIEWER__.default_render_mode);
    if ($("canvasTitle")) {
      $("canvasTitle").textContent =
        mode === "three_3d" ? `${currentFlow.title || "未命名流程"}（3D 無重力視圖）` : `${currentFlow.title || "未命名流程"}`;
    }
    updateGraphNavButtons();
  }

  function handleSelectNode(id) {
    if (!currentFlow) return;
    if (id === null || id === undefined || String(id).trim() === "") {
      activeId = null;
      const de = $("detailEmpty");
      const dc = $("detailContent");
      if (de) de.classList.remove("hidden");
      if (dc) dc.classList.add("hidden");
      refreshNodeList();
      return;
    }
    activeId = id;
    const node = currentFlow.nodes.find(n => String(n.id) === String(id));
    if (!node) return;
    const incoming = (currentFlow.edges || []).filter(e => String(e.to) === String(id));
    const outgoing = (currentFlow.edges || []).filter(e => String(e.from) === String(id));
    FlowPanel.showNodeDetail(node, incoming, outgoing);
    refreshNodeList();
  }

  function handleNodeListActivate(id) {
    if (!currentFlow || !viewDriver) return;
    viewDriver.selectNode(id, false);
    handleSelectNode(id);
    if (typeof viewDriver.focusNodeInView === "function") {
      viewDriver.focusNodeInView(id);
    }
  }

  function refreshNodeList() {
    if (!currentFlow || !viewDriver) return;
    FlowPanel.renderNodeList(
      currentFlow,
      nodeId => {
        viewDriver.selectNode(nodeId, false);
        handleSelectNode(nodeId);
      },
      $("searchInput").value,
      activeId,
      handleNodeListActivate
    );
  }

  async function renderSvgPreview() {
    if (!currentFlow) {
      alert("請先載入 PydotStudio Flow JSON");
      return;
    }
    const preview = $("renderPreview");
    preview.innerHTML = `<div class="empty-state">渲染中...</div>`;
    try {
      const svgText = await FlowAPI.renderSvg(currentFlow, $("includeMeta").checked);
      preview.innerHTML = svgText;
    } catch (err) {
      preview.innerHTML = `<div class="empty-state">${escapeHtml(err.message)}</div>`;
    }
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }
})();
