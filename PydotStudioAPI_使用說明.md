# PydotStudio API 使用說明

本服務由 `api_server.py` 提供，使用 FastAPI 對外輸出流程圖。

## 啟動服務
```bat
python C:/ML_HOME/PydotStudio/api_server.py
```

## 常用參數
- `--host`：覆寫 config.json 的 host
- `--port`：覆寫 config.json 的 port
- `--reload`：啟用熱重載

## 端點
- `GET /health`：健康檢查
- `POST /render`：直接傳 JSON，回傳圖檔或保存結果
- `POST /render/by-file`：傳 JSON 檔案路徑，回傳圖檔或保存結果

## Query 參數
- `format`：`png` / `svg` / `pdf`
- `include_meta`：是否將 `meta` 附加到標籤
- `save`：是否保存為檔案（回傳 `saved_path`）

## JSON 擴充：style_presets
- 在 JSON 頂層新增 `style_presets`，並於 node/edge/group 使用 `style_ref` 或 `style_refs` 套用樣式。
- 可把「呈現用屬性」與 `meta` 描述分離，避免干擾文字內容。

範例（POST /render / by-file 同用）：
```json
{
  "style_presets": {
    "warn": {"fillcolor": "#FFF2CC", "color": "#B45F06", "penwidth": "2", "style": "rounded,filled"},
    "dashed": {"style": "dashed", "color": "#D9534F", "penwidth": "2"}
  },
  "nodes": [
    {"id": "A", "label": "節點A", "style_ref": "warn"}
  ],
  "edges": [
    {"from": "A", "to": "B", "label": "轉移", "style_ref": "dashed"}
  ],
  "groups": [
    {"id": "g1", "label": "群組", "style_ref": "warn"}
  ]
}
```

## 範例
```bat
curl -X POST "http://127.0.0.1:8010/render/by-file?format=png&include_meta=true&save=true" -H "Content-Type: application/json" -d "{\"path\":\"C:\\ML_HOME\\DocumentManagerQAS\\issues\\batch_import_url_flow.json\"}"
```

```bat
curl -X POST "http://127.0.0.1:8010/render?format=svg&include_meta=false" -H "Content-Type: application/json" -d @C:/ML_HOME/DocumentManagerQAS/issues/batch_import_url_flow.json --output C:/ML_HOME/PydotStudio/output/flow.svg
```

## 回傳說明
- `save=true`：回傳 JSON，例如 `{ "saved_path": "..." }`
- `save=false`：直接回傳圖檔內容（image/png, image/svg+xml, application/pdf）

## 字型與亂碼
- 請在 `config.json` 設定 `fontname` 與 `font_path`
- 若仍亂碼，使用 CLI 的 `--debug` 產生 `.dot` 後手動用 dot 驗證
