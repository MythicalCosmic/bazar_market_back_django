from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.app.router import files
from src.middlewares.token_auth_middleware import TokenAuthMiddleware

app = FastAPI(title="File Downloader for Bazar Market", version="0.0.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TokenAuthMiddleware)
app.include_router(files.router)


@app.get('/health')
async def get_health():
    return JSONResponse({
        "success": True,
        "health": "ok",
        "version": "0.0.1"
    })