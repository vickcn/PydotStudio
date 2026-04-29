window.FlowAPI = (() => {
  const API_BASE = window.PYDOT_API_BASE || "";

  async function viewerConfig() {
    const url = `${API_BASE}/viewer-config`;
    const resp = await fetch(url);
    if (!resp.ok) {
      throw new Error(`viewer-config failed: ${resp.status}`);
    }
    return await resp.json();
  }

  async function renderSvg(flowJson, includeMeta = true) {
    const url = `${API_BASE}/render?format=svg&include_meta=${includeMeta ? "true" : "false"}&save=false`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(flowJson),
    });
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`render failed: ${resp.status} ${text}`);
    }
    return await resp.text();
  }

  return { renderSvg, viewerConfig };
})();
