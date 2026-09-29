from __future__ import annotations
import os
from contextlib import contextmanager
from sqlalchemy import create_engine,text
DATABASE_URL=os.getenv("DATABASE_URL")
def configured(): return bool(DATABASE_URL)
_engine=create_engine(DATABASE_URL,pool_pre_ping=True,pool_recycle=300) if DATABASE_URL else None
@contextmanager
def connect():
 if not _engine: raise RuntimeError("DATABASE_URL is required in production")
 with _engine.begin() as conn: yield conn
def tenant_context(conn,tenant_id:str):
 if not tenant_id: raise ValueError("tenant_id required")
 if conn.dialect.name=="postgresql": conn.execute(text("SELECT set_config('app.tenant_id', :tenant, true)"),{"tenant":tenant_id})
