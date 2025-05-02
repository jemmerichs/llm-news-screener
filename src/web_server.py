from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json
from src.logger import setup_logging
from src.main import app_repo, main as main_loop
import threading
import time

# Ensure logging is set up even if main.py is not run
default_logging_config = type('LoggingConfig', (), {"file": "logs/app.log", "max_size": "10 MB", "backup_count": "10 days", "level": "DEBUG"})()
setup_logging(default_logging_config)

app = FastAPI()

# Allow all origins for local dev/OBS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def start_background_thread():
    def run_main_loop():
        try:
            main_loop(with_signals=False)
        except Exception as e:
            import traceback
            print("Background main loop crashed:", e)
            traceback.print_exc()
    thread = threading.Thread(target=run_main_loop, daemon=True)
    thread.start()

@app.get("/api/state")
def get_state(news_limit: str = Query("10")):
    try:
        state = app_repo.get_app_data()  # Serve in-memory state directly
        # Filter news_items if news_limit is set
        if news_limit != "all":
            try:
                limit = int(news_limit)
                state["news_items"] = state["news_items"][:limit]
            except Exception:
                pass  # fallback to all if invalid
        print("/api/state: news count:", len(state["news_items"]))
        return JSONResponse(content=state)
    except Exception:
        return JSONResponse(content={"events": [], "portfolio": {}, "news_items": [], "llm_log": []})

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/logs")
def get_logs():
    log_path = "logs/app.log"
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-100:]
        return PlainTextResponse("".join(lines))
    except Exception as e:
        return PlainTextResponse(f"Error reading log: {e}", status_code=500)

# Serve static files
static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def root():
    return FileResponse(static_dir / "index.html")

@app.on_event("shutdown")
def shutdown_event():
    print("Shutting down, saving state...")
    app_repo.save() 