import argparse
import os
from typing import Any, Dict, Optional

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from PydotStudio import CONFIG
from PydotStudio import render_flow as core_render_flow
from PydotStudio import render_by_file as core_render_by_file
from PydotStudio import get_media_type

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(_BASE_DIR, "template", "flow_editor.html"))


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/viewer-config")
def viewer_config_route() -> Dict[str, Any]:
    return CONFIG.get("viewer") or {}


@app.post("/render")
def render_flow_endpoint(
    data: Dict[str, Any] = Body(...),
    fmt: Optional[str] = Query(None, alias="format"),
    include_meta: bool = Query(False),
    save: bool = Query(False),
):
    fmt_used = fmt or CONFIG.get("default_format", "png")
    result = core_render_flow(data=data, fmt=fmt_used, include_meta=include_meta, save=save)
    if save:
        return result
    return Response(content=result, media_type=get_media_type(fmt_used))


@app.post("/render/by-file")
def render_by_file_endpoint(
    path: str = Body(..., embed=True),
    fmt: Optional[str] = Query(None, alias="format"),
    include_meta: bool = Query(False),
    save: bool = Query(False),
):
    if not os.path.isfile(path):
        raise HTTPException(status_code=400, detail="file not found")
    fmt_used = fmt or CONFIG.get("default_format", "png")
    result = core_render_by_file(path=path, fmt=fmt_used, include_meta=include_meta, save=save)
    if save:
        return result
    return Response(content=result, media_type=get_media_type(fmt_used))


app.mount("/static", StaticFiles(directory=os.path.join(_BASE_DIR, "static")), name="static")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PydotStudio API Server")
    parser.add_argument("--host", default=None, help="Override host (default: config.json)")
    parser.add_argument("--port", type=int, default=None, help="Override port (default: config.json)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    return parser.parse_args()


def main() -> None:
    import uvicorn

    args = _parse_args()
    host = args.host or CONFIG.get("host", "0.0.0.0")
    port = args.port or int(CONFIG.get("port", 8010))
    uvicorn.run("api_server:app", host=host, port=port, reload=args.reload)


if __name__ == "__main__":
    main()
