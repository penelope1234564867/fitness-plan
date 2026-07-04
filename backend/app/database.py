"""SQLite 数据库连接配置"""

from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

DB_PATH = Path(__file__).parent.parent / "fitness.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """启用 WAL 模式 + 优化并发性能。"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    """初始化数据库：创建所有表 + 迁移旧表字段。"""
    from app.models import orm_models  # noqa: F401 — 触发模型注册
    Base.metadata.create_all(bind=engine)

    # ── 字段迁移：检查 UserCurrentState 是否有新字段 ──
    _migrate_user_current_state(engine)


def _migrate_user_current_state(engine):
    """给 UserCurrentState 表添加新字段（如果不存在）。"""
    import sqlalchemy as sa
    inspector = sa.inspect(engine)
    columns = [c["name"] for c in inspector.get_columns("user_current_state")]

    new_columns = {
        "avg_completion_rate": "REAL DEFAULT 0.0",
        "rpe_trend": "VARCHAR(20) DEFAULT 'stable'",
        "consecutive_weeks_completed": "INTEGER DEFAULT 0",
        "exercise_blacklist": "TEXT DEFAULT '[]'",
        "weekly_progress": "TEXT DEFAULT '[]'",
        "pool_loaded": "INTEGER DEFAULT 0",
    }

    with engine.begin() as conn:
        for col_name, col_type in new_columns.items():
            if col_name not in columns:
                conn.execute(
                    sa.text(
                        f"ALTER TABLE user_current_state ADD COLUMN {col_name} {col_type}"
                    )
                )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
