# PydotStudio 使用說明

PydotStudio.py 是命令列工具，用來把流程 JSON 轉成流程圖（PNG/SVG/PDF）。

## 前置需求
- Graphviz（可執行 `dot -V`）
- Python 套件 `pydot`
- 建議使用相同虛擬環境執行

## 主要檔案
- `C:/ML_HOME/PydotStudio/PydotStudio.py`
- `C:/ML_HOME/PydotStudio/config.json`
- 預設輸出資料夾：`C:/ML_HOME/PydotStudio/output`

## 基本用法
```bat
python C:/ML_HOME/PydotStudio/PydotStudio.py -i C:/ML_HOME/DocumentManagerQAS/issues/batch_import_url_flow.json
```

## 常用參數
| 參數 | 說明 |
| --- | --- |
| `-i` / `--input` | 輸入 JSON 檔案路徑 | 
| `-f` / `--format` | 輸出格式（`png`/`svg`/`pdf`） | 
| `-m` / `--include-meta` | 將 `meta` 資訊附加到節點標籤 | 
| `-o` / `--output` | 指定輸出檔名與完整路徑 | 
| `-d` / `--output-dir` | 指定輸出目錄，檔名自動生成 | 
| `--debug` | 產出 `.dot` 並輸出除錯訊息 | 
| `--log` | 指定 log 檔案路徑 | 

## 範例
```bat
python C:/ML_HOME/PydotStudio/PydotStudio.py -i C:/ML_HOME/DocumentManagerQAS/issues/batch_import_url_flow.json -m

python C:/ML_HOME/PydotStudio/PydotStudio.py -i C:/ML_HOME/DocumentManagerQAS/issues/batch_import_url_flow.json -m -f svg

python C:/ML_HOME/PydotStudio/PydotStudio.py -i C:/ML_HOME/DocumentManagerQAS/issues/batch_import_url_flow.json -m -o C:/ML_HOME/PydotStudio/output/flow.png

python C:/ML_HOME/PydotStudio/PydotStudio.py -i C:/ML_HOME/DocumentManagerQAS/issues/batch_import_url_flow.json -m --debug --log C:/ML_HOME/PydotStudio/output/pydot_debug.log
```

## config.json 說明
- `fontname`：字型名稱（繁中建議 `Microsoft JhengHei`）
- `font_path`：字型資料夾（例如 `C:/Windows/Fonts`）
- `output_dir`：預設輸出資料夾
- `default_format`：預設輸出格式
- `rankdir`：預設方向（`LR` 橫向、`TB` 縱向）

## 重要提醒
- `charset` 必須放在「流程 JSON」的 `graph` 區塊中才會生效。
- 若中文亂碼，通常是字型未被 Graphviz 使用，請確認 `fontname` 與 `font_path`。
- 使用 `--debug` 會生成 `.dot`，可用 `dot` 指令手動驗證字型。

## 輸入 JSON 常見格式

最小可行格式（只有 nodes/edges）：
```json
{
  "title": "Sample Flow",
  "nodes": [
    {"id": "A", "label": "開始"},
    {"id": "B", "label": "結束"}
  ],
  "edges": [
    {"from": "A", "to": "B"}
  ]
}
```

包含群組（cluster）：
```json
{
  "groups": [
    {"id": "g1", "label": "區段一"}
  ],
  "nodes": [
    {"id": "A", "label": "A", "group": "g1"}
  ]
}
```

包含樣式（全域與節點/邊）：
```json
{
  "graph": {"rankdir": "TB", "charset": "UTF-8"},
  "node_style": {"shape": "box", "style": "rounded,filled"},
  "edge_style": {"color": "#555555"},
  "nodes": [
    {"id": "A", "label": "節點", "style": "filled", "fillcolor": "#F7F7F7"}
  ]
}
```

## 動態欄位 / 擴充機制
- `nodes[*].attrs` / `edges[*].attrs` / `groups[*].attrs` 可直接傳 Graphviz 原生屬性（例如 `rank`, `margin`, `fontsize`, `fontname`, `color`）。
- 覆寫規則（簡化說明）：
- Node：`style_ref` → 節點本身 `shape/style/color/...` → `attrs`（`attrs` 會覆寫）。
- Edge：`style_ref` → `label/style/color` → `attrs`（`attrs` 會覆寫）。
- Group：`style_ref` → `style` → `attrs`（`attrs` 會覆寫）。
- `meta` 目前支援：`description`、`bullets`、`files`、`functions`、`params`、`notes`。使用 `-m/--include-meta` 才會附加到標籤。
- 其他欄位預設會被忽略，不影響繪圖。若要顯示更多欄位，可擴充 `build_label()`。

### 樣式預設（style_presets）
- 可在 JSON 頂層定義 `style_presets`，並用 `style_ref` / `style_refs` 套用到節點、邊、群組。
- 用途：把「呈現用樣式」與「描述用 meta」分離，避免互相干擾。

範例：
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

## JSON 結構摘要
- `nodes`：節點清單
- `edges`：連線清單
- `groups`：子群組（cluster）
- `meta`：可記錄說明、檔案、函式、參數等資訊
