PydotStudio 部署注意事項（Windows / macOS）

通用前提:
- 建議使用 Python 3.9 ~ 3.11，並建立獨立虛擬環境。
- Graphviz 必須安裝，且 `dot` 要在 `PATH` 中，否則會出現 `dot failed` 錯誤。
- 若需要資料庫功能，請先安裝對應資料庫的 ODBC 驅動。

Windows 重點:
- Graphviz 安裝後，確認 `C:\Program Files\Graphviz\bin` 已加入 `PATH`。
- 若需連 SQL Server，安裝 Microsoft ODBC Driver 18 for SQL Server。
- `minepy` 若遇到編譯問題，需安裝 Visual Studio Build Tools（C++）。

macOS 重點:
- Graphviz 建議用 Homebrew：`brew install graphviz`。
- Apple Silicon（M1/M2/M3）使用 `tensorflow-macos` + `tensorflow-metal`；Intel Mac 請改用 `tensorflow`。
- 若需連 SQL Server，安裝 Microsoft ODBC Driver 18 for SQL Server（macOS）與 `unixODBC`。
- `minepy` 若需編譯，安裝 Xcode Command Line Tools：`xcode-select --install`。

字型與圖形渲染:
- `config.json` 預設字型為 `Microsoft JhengHei`，macOS 通常沒有此字型。
- macOS 可改用 `PingFang TC`、`Heiti TC` 或 `Noto Sans CJK TC`。
- 若使用自訂字型，請設定 `font_path`，並確認 `DOTFONTPATH` / `GDFONTPATH` 能指到字型位置。

安裝指令範例（Windows）:
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements-windows.txt
```

安裝指令範例（macOS）:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-macos.txt
```

常見問題:
- `dot failed`: 確認 Graphviz 已安裝且 `dot` 在 `PATH`。
- `pyodbc` 連線失敗: 驗證 ODBC Driver 是否安裝、連線字串與 Driver 名稱是否正確。
