"""FastAPI 主应用"""

import sys
import os
import io
from contextlib import asynccontextmanager

# Windows GBK 编码兼容：替换 stdout/stderr 为 UTF-8 版本（errors='replace'）
# 解决 hello_agents 库 print(emoji) 在 GBK 终端上崩溃的问题
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    # 用 UTF-8 errors=replace 包装 stdout，确保 print(emoji) 不抛异常
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import init_db
from app.api.routes import user, fitness, wger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动/关闭事件处理器（替代弃用的 on_event）"""
    # --- startup ---
    init_db()
    print("\n" + "=" * 60)
    print("[START] Fitness Planner API v1.0.0")
    print("[DB]    fitness.db 已初始化")
    print("[DOCS]  http://localhost:8000/docs")
    print("=" * 60 + "\n")
    yield
    # --- shutdown ---
    print("[SHUTDOWN] 服务关闭")


app = FastAPI(
    title="Fitness Planner API",
    version="1.0.0",
    description="基于 HelloAgents 框架的 AI 健身计划助手",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router, prefix="/api")
app.include_router(fitness.router, prefix="/api")
app.include_router(wger.router, prefix="/api")


@app.get("/")
async def root():
    return {"name": "Fitness Planner API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
