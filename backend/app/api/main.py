"""FastAPI 主应用"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import init_db
from app.api.routes import user, fitness, record

settings = get_settings()

app = FastAPI(
    title="Fitness Planner API",
    version="1.0.0",
    description="基于 HelloAgents 框架的 AI 健身计划助手",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router, prefix="/api")
app.include_router(fitness.router, prefix="/api")
app.include_router(record.router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    init_db()
    print("\n" + "=" * 60)
    print("[START] Fitness Planner API v1.0.0")
    print("[DB]    fitness.db 已初始化")
    print("[DOCS]  http://localhost:8000/docs")
    print("=" * 60 + "\n")


@app.get("/")
async def root():
    return {"name": "Fitness Planner API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
