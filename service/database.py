import os
from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

# Читаем URL базы из окружения. Если его нет, то используем локальный SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./history.db")

# Параметр check_same_thread нужен только для SQLite
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ModerationLog(Base):
    __tablename__ = "moderation_logs"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), index=True)
    overall_status = Column(String(50))
    found_logos = Column(Integer, default=0)
    best_match = Column(String(100), default="None")
    max_similarity = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
