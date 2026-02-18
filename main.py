# ═══════════════════════════════════════════════════════════════════════════════
# RUHI-VIG QNR Distributed Database Cloud System v2.0
# SINGLE FILE ARCHITECTURE - Copy & Deploy Directly to Render.com
# File: main.py
# Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
# ═══════════════════════════════════════════════════════════════════════════════

import os
import json
import threading
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from contextlib import asynccontextmanager

# ── FastAPI Imports ────────────────────────────────────────────────────────────
from fastapi import FastAPI, Request, Response, HTTPException, status, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

# ── Database Imports ───────────────────────────────────────────────────────────
from sqlalchemy import (
    Column, DateTime, Integer, String, Boolean,
    Text, BigInteger, Float, create_engine, text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

# ── Auth Imports ───────────────────────────────────────────────────────────────
from jose import JWTError, jwt
from passlib.context import CryptContext

# ── Scheduler Imports ──────────────────────────────────────────────────────────
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# ── Pydantic ───────────────────────────────────────────────────────────────────
from pydantic import BaseModel, field_validator

# ── Std Lib ────────────────────────────────────────────────────────────────────
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RUHI-VIG-QNR")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

MASTER_DB_URL = os.getenv(
    "MASTER_DB_URL",
    "postgresql://ruhi_user:password@localhost/ruhi_master"
)
SECRET_KEY = os.getenv("SECRET_KEY", "RUHIVIGQNR_SECRET_KEY_2024_CHANGE_ME")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24
WORKER_SOFT_LIMIT_MB = 950
WORKER_HARD_LIMIT_MB = 1000
PING_INTERVAL_MINUTES = 10

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
Base = declarative_base()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: DATABASE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class WorkerDatabase(Base):
    __tablename__ = "worker_databases"
    id               = Column(Integer, primary_key=True, autoincrement=True)
    name             = Column(String(255), nullable=False, unique=True)
    connection_url   = Column(Text, nullable=False)
    is_active        = Column(Boolean, default=True)
    is_current_write = Column(Boolean, default=False)
    size_used_mb     = Column(Float, default=0.0)
    max_size_mb      = Column(Float, default=1000.0)
    record_count     = Column(BigInteger, default=0)
    last_pinged      = Column(DateTime, nullable=True)
    last_size_check  = Column(DateTime, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    added_by         = Column(String(255), nullable=True)
    notes            = Column(Text, nullable=True)
    ping_status      = Column(String(50), default="unknown")

class DataShardMapping(Base):
    __tablename__ = "data_shard_mappings"
    id                = Column(Integer, primary_key=True, autoincrement=True)
    shard_key         = Column(String(255), nullable=False, unique=True, index=True)
    shard_type        = Column(String(100), nullable=False)
    worker_db_id      = Column(Integer, nullable=False)
    worker_table_name = Column(String(255), nullable=False)
    record_id         = Column(String(255), nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow)
    size_bytes        = Column(BigInteger, default=0)

class SystemConfig(Base):
    __tablename__ = "system_config"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    config_key   = Column(String(255), nullable=False, unique=True, index=True)
    config_value = Column(Text, nullable=True)
    config_type  = Column(String(50), default="string")
    updated_at   = Column(DateTime, default=datetime.utcnow)
    updated_by   = Column(String(255), nullable=True)

class UserAccount(Base):
    __tablename__ = "user_accounts"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    username      = Column(String(255), nullable=False, unique=True, index=True)
    email         = Column(String(255), nullable=True)
    password_hash = Column(Text, nullable=False)
    role          = Column(String(50), default="user")
    balance       = Column(Float, default=0.0)
    is_active     = Column(Boolean, default=True)
    contact_info  = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    created_by    = Column(String(255), nullable=True)
    last_login    = Column(DateTime, nullable=True)
    profile_data  = Column(Text, nullable=True)

class UIDesignConfig(Base):
    __tablename__ = "ui_design_config"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    design_key   = Column(String(255), nullable=False, unique=True)
    design_value = Column(Text, nullable=True)
    design_type  = Column(String(100), default="css")
    updated_at   = Column(DateTime, default=datetime.utcnow)
    updated_by   = Column(String(255), nullable=True)

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    user       = Column(String(255), nullable=True)
    action     = Column(String(500), nullable=False)
    details    = Column(Text, nullable=True)
    ip_address = Column(String(100), nullable=True)
    timestamp  = Column(DateTime, default=datetime.utcnow)
    level      = Column(String(50), default="INFO")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: CONNECTION POOL MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class ConnectionPoolManager:
    def __init__(self):
        self._pools: Dict[int, Any]   = {}
        self._sessions: Dict[int, Any] = {}
        self._pool_lock = threading.Lock()
        self._master_engine = None
        self._master_session_factory = None

    def get_master_engine(self):
        if self._master_engine is None:
            self._master_engine = create_engine(
                MASTER_DB_URL,
                poolclass=QueuePool,
                pool_size=20,
                max_overflow=30,
                pool_pre_ping=True,
                pool_recycle=300,
                connect_args={"connect_timeout": 10}
            )
        return self._master_engine

    def get_master_session(self) -> Session:
        if self._master_session_factory is None:
            engine = self.get_master_engine()
            self._master_session_factory = sessionmaker(
                autocommit=False, autoflush=False, bind=engine
            )
        return self._master_session_factory()

    def get_worker_engine(self, worker_id: int, connection_url: str):
        with self._pool_lock:
            if worker_id not in self._pools:
                engine = create_engine(
                    connection_url,
                    poolclass=QueuePool,
                    pool_size=5,
                    max_overflow=10,
                    pool_pre_ping=True,
                    pool_recycle=300,
                    pool_timeout=30,
                    connect_args={"connect_timeout": 15}
                )
                self._pools[worker_id] = engine
                self._sessions[worker_id] = sessionmaker(
                    autocommit=False, autoflush=False, bind=engine
                )
            return self._pools[worker_id]

    def get_worker_session(self, worker_id: int, connection_url: str) -> Session:
        self.get_worker_engine(worker_id, connection_url)
        return self._sessions[worker_id]()

    def remove_pool(self, worker_id: int):
        with self._pool_lock:
            if worker_id in self._pools:
                self._pools[worker_id].dispose()
                del self._pools[worker_id]
                del self._sessions[worker_id]

    def dispose_all(self):
        with self._pool_lock:
            for engine in self._pools.values():
                try:
                    engine.dispose()
                except Exception:
                    pass
            self._pools.clear()
            self._sessions.clear()

pool_manager = ConnectionPoolManager()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: DATABASE ROUTER (SHARDING ENGINE)
# ═══════════════════════════════════════════════════════════════════════════════

class DatabaseRouter:
    def __init__(self):
        self._writer_lock = threading.Lock()

    # ── MASTER INIT ──────────────────────────────────────────────────────────
    def initialize_master(self):
        engine = pool_manager.get_master_engine()
        Base.metadata.create_all(bind=engine)
        session = pool_manager.get_master_session()
        try:
            self._seed_owner(session)
            self._seed_config(session)
            self._seed_ui(session)
            session.commit()
            logger.info("✅ Master DB initialized")
        except Exception as e:
            session.rollback()
            logger.error(f"Init error: {e}")
        finally:
            session.close()

    def _seed_owner(self, session: Session):
        existing = session.query(UserAccount).filter_by(
            username="RUHIVIGQNR@QNR"
        ).first()
        if not existing:
            session.add(UserAccount(
                username="RUHIVIGQNR@QNR",
                email="owner@ruhivigqnr.com",
                password_hash=pwd_context.hash("RUHIVIGQNR"),
                role="owner",
                is_active=True,
                created_by="SYSTEM"
            ))
            logger.info("✅ Owner account created")

    def _seed_config(self, session: Session):
        defaults = [
            ("maintenance_mode",   "false",                       "boolean"),
            ("site_name",          "RUHI-VIG QNR Cloud",          "string"),
            ("site_tagline",       "Distributed Database System",  "string"),
            ("bg_video_url",       "",                            "string"),
            ("bg_music_url",       "",                            "string"),
            ("bg_music_autoplay",  "false",                       "boolean"),
            ("anti_sleep_enabled", "true",                        "boolean"),
            ("allow_registration", "true",                        "boolean"),
        ]
        for key, val, vtype in defaults:
            if not session.query(SystemConfig).filter_by(config_key=key).first():
                session.add(SystemConfig(
                    config_key=key, config_value=val, config_type=vtype
                ))

    def _seed_ui(self, session: Session):
        ui_defaults = [
            ("primary_color",    "#6C63FF",                          "css"),
            ("secondary_color",  "#FF6584",                          "css"),
            ("background_color", "#0F0F1A",                          "css"),
            ("text_color",       "#FFFFFF",                          "css"),
            ("card_color",       "#1A1A2E",                          "css"),
            ("font_family",      "Inter, sans-serif",                "css"),
            ("custom_css",       "",                                 "css"),
            ("custom_html_header","",                                "html"),
            ("logo_text",        "RUHI-VIG QNR",                    "html"),
            ("hero_title",       "Virtual Database Cloud",           "html"),
            ("hero_subtitle",    "Aggregating 1000+ databases into one unified pool", "html"),
        ]
        for key, val, vtype in ui_defaults:
            if not session.query(UIDesignConfig).filter_by(design_key=key).first():
                session.add(UIDesignConfig(
                    design_key=key, design_value=val, design_type=vtype
                ))

    # ── CONFIG HELPERS ───────────────────────────────────────────────────────
    def get_config(self, key: str, default: Any = None) -> Any:
        session = pool_manager.get_master_session()
        try:
            c = session.query(SystemConfig).filter_by(config_key=key).first()
            return c.config_value if c else default
        finally:
            session.close()

    def set_config(self, key: str, value: str, updated_by: str = "system"):
        session = pool_manager.get_master_session()
        try:
            c = session.query(SystemConfig).filter_by(config_key=key).first()
            if c:
                c.config_value = value
                c.updated_at   = datetime.utcnow()
                c.updated_by   = updated_by
            else:
                session.add(SystemConfig(
                    config_key=key, config_value=value, updated_by=updated_by
                ))
            session.commit()
        except Exception as e:
            session.rollback()
        finally:
            session.close()

    def get_ui_config(self) -> Dict:
        session = pool_manager.get_master_session()
        try:
            configs = session.query(UIDesignConfig).all()
            return {c.design_key: c.design_value for c in configs}
        finally:
            session.close()

    def set_ui_config(self, key: str, value: str, updated_by: str = "admin"):
        session = pool_manager.get_master_session()
        try:
            c = session.query(UIDesignConfig).filter_by(design_key=key).first()
            if c:
                c.design_value = value
                c.updated_at   = datetime.utcnow()
                c.updated_by   = updated_by
            else:
                session.add(UIDesignConfig(
                    design_key=key, design_value=value, updated_by=updated_by
                ))
            session.commit()
        except Exception as e:
            session.rollback()
        finally:
            session.close()

    def is_maintenance(self) -> bool:
        return self.get_config("maintenance_mode", "false").lower() == "true"

    def toggle_maintenance(self, enabled: bool, by: str):
        self.set_config("maintenance_mode", "true" if enabled else "false", by)
        self.log_activity(by, "MAINTENANCE_TOGGLE",
                          f"Maintenance {'enabled' if enabled else 'disabled'}")

    # ── WORKER MANAGEMENT ────────────────────────────────────────────────────
    def _test_connection(self, url: str) -> Dict:
        try:
            conn = psycopg2.connect(url, connect_timeout=15)
            cur  = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                "SELECT pg_database_size(current_database()) / (1024*1024.0) AS size_mb"
            )
            row     = cur.fetchone()
            size_mb = float(row["size_mb"]) if row else 0.0
            cur.close()
            conn.close()
            return {"success": True, "size_mb": size_mb}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _init_worker_schema(self, url: str) -> bool:
        try:
            conn = psycopg2.connect(url, connect_timeout=15)
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS data_records (
                    id              SERIAL PRIMARY KEY,
                    shard_key       VARCHAR(255) UNIQUE NOT NULL,
                    record_type     VARCHAR(100) NOT NULL DEFAULT 'generic',
                    data_json       TEXT,
                    file_blob       BYTEA,
                    file_name       VARCHAR(500),
                    file_size_bytes BIGINT DEFAULT 0,
                    owner_username  VARCHAR(255),
                    is_public       BOOLEAN DEFAULT false,
                    created_at      TIMESTAMP DEFAULT NOW(),
                    updated_at      TIMESTAMP DEFAULT NOW(),
                    tags            TEXT DEFAULT '[]',
                    metadata        TEXT DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_sk  ON data_records(shard_key);
                CREATE INDEX IF NOT EXISTS idx_own ON data_records(owner_username);
                CREATE INDEX IF NOT EXISTS idx_rt  ON data_records(record_type);
            """)
            cur.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Schema init error: {e}")
            return False

    def validate_and_add_worker(
        self, url: str, name: str, added_by: str, notes: str = ""
    ) -> Tuple[bool, str, Optional[Any]]:
        session = pool_manager.get_master_session()
        try:
            test = self._test_connection(url)
            if not test["success"]:
                return False, f"Connection failed: {test['error']}", None

            if session.query(WorkerDatabase).filter_by(connection_url=url).first():
                return False, "This URL already exists in the pool.", None

            if not self._init_worker_schema(url):
                return False, "Failed to initialize worker schema.", None

            worker = WorkerDatabase(
                name=name, connection_url=url, is_active=True,
                is_current_write=False,
                size_used_mb=test.get("size_mb", 0),
                max_size_mb=1000.0,
                last_pinged=datetime.utcnow(),
                last_size_check=datetime.utcnow(),
                added_by=added_by, notes=notes, ping_status="online"
            )
            session.add(worker)
            session.commit()

            write_count = session.query(WorkerDatabase).filter_by(
                is_current_write=True, is_active=True
            ).count()
            if write_count == 0:
                worker.is_current_write = True
                session.commit()

            logger.info(f"✅ Worker DB added: {name} (#{worker.id})")
            return True, f"Database '{name}' added!", worker
        except Exception as e:
            session.rollback()
            return False, str(e), None
        finally:
            session.close()

    # ── WRITE / READ ROUTING ─────────────────────────────────────────────────
    def get_write_db(self) -> Optional[WorkerDatabase]:
        session = pool_manager.get_master_session()
        try:
            writer = session.query(WorkerDatabase).filter_by(
                is_current_write=True, is_active=True
            ).first()
            if not writer:
                writer = session.query(WorkerDatabase).filter(
                    WorkerDatabase.is_active == True,
                    WorkerDatabase.size_used_mb < WORKER_SOFT_LIMIT_MB
                ).order_by(WorkerDatabase.id).first()
                if writer:
                    writer.is_current_write = True
                    session.commit()
            elif writer.size_used_mb >= WORKER_SOFT_LIMIT_MB:
                writer = self._switch_write_db(session, writer)
            return writer
        except Exception as e:
            logger.error(f"get_write_db error: {e}")
            return None
        finally:
            session.close()

    def _switch_write_db(
        self, session: Session, current: WorkerDatabase
    ) -> Optional[WorkerDatabase]:
        with self._writer_lock:
            current.is_current_write = False
            nxt = session.query(WorkerDatabase).filter(
                WorkerDatabase.is_active == True,
                WorkerDatabase.id != current.id,
                WorkerDatabase.size_used_mb < WORKER_SOFT_LIMIT_MB,
                WorkerDatabase.is_current_write == False
            ).order_by(WorkerDatabase.id).first()
            if nxt:
                nxt.is_current_write = True
                session.commit()
                logger.info(f"✅ Switched write → DB #{nxt.id} ({nxt.name})")
                self._log(session, "SYSTEM", "AUTO_DB_SWITCH",
                          f"#{current.id} → #{nxt.id} (capacity limit)")
                return nxt
            logger.critical("❌ No available write DB!")
            return None

    def write_record(
        self, shard_key: str, record_type: str,
        data: Dict, owner: str = None
    ) -> Tuple[bool, str]:
        writer = self.get_write_db()
        if not writer:
            return False, "No available worker DB. Add one from DB Manager."

        w_session = pool_manager.get_worker_session(
            writer.id, writer.connection_url
        )
        m_session = pool_manager.get_master_session()
        try:
            data_json = json.dumps(data)
            size      = len(data_json.encode("utf-8"))

            existing = m_session.query(DataShardMapping).filter_by(
                shard_key=shard_key
            ).first()
            if existing:
                wdb = m_session.query(WorkerDatabase).get(existing.worker_db_id)
                if wdb:
                    ws2 = pool_manager.get_worker_session(
                        wdb.id, wdb.connection_url
                    )
                    try:
                        ws2.execute(text(
                            "UPDATE data_records SET data_json=:d, updated_at=NOW() "
                            "WHERE shard_key=:k"
                        ), {"d": data_json, "k": shard_key})
                        ws2.commit()
                    finally:
                        ws2.close()
                return True, f"Record updated in DB #{existing.worker_db_id}"

            w_session.execute(text("""
                INSERT INTO data_records
                    (shard_key, record_type, data_json, owner_username, file_size_bytes)
                VALUES (:k, :t, :d, :o, :s)
                ON CONFLICT (shard_key) DO UPDATE
                    SET data_json=EXCLUDED.data_json, updated_at=NOW()
            """), {"k": shard_key, "t": record_type, "d": data_json,
                   "o": owner, "s": size})
            w_session.commit()

            m_session.add(DataShardMapping(
                shard_key=shard_key, shard_type=record_type,
                worker_db_id=writer.id, worker_table_name="data_records",
                size_bytes=size
            ))
            wdb_row = m_session.query(WorkerDatabase).get(writer.id)
            if wdb_row:
                wdb_row.size_used_mb += size / (1024 * 1024)
                wdb_row.record_count += 1
            m_session.commit()
            return True, f"Saved to Worker DB #{writer.id} ({writer.name})"
        except Exception as e:
            w_session.rollback()
            m_session.rollback()
            return False, str(e)
        finally:
            w_session.close()
            m_session.close()

    def read_record(self, shard_key: str) -> Tuple[bool, Optional[Dict], str]:
        m_session = pool_manager.get_master_session()
        try:
            mapping = m_session.query(DataShardMapping).filter_by(
                shard_key=shard_key
            ).first()
            if not mapping:
                return False, None, "Record not found."

            worker = m_session.query(WorkerDatabase).get(mapping.worker_db_id)
            if not worker or not worker.is_active:
                return False, None, "Worker DB unavailable."

            w_session = pool_manager.get_worker_session(
                worker.id, worker.connection_url
            )
            try:
                row = w_session.execute(text("""
                    SELECT shard_key, record_type, data_json,
                           owner_username, is_public, created_at, updated_at
                    FROM data_records WHERE shard_key=:k
                """), {"k": shard_key}).fetchone()

                if not row:
                    return False, None, "Record missing in worker DB."

                return True, {
                    "shard_key":   row[0],
                    "record_type": row[1],
                    "data":        json.loads(row[2]) if row[2] else {},
                    "owner":       row[3],
                    "is_public":   row[4],
                    "created_at":  str(row[5]),
                    "updated_at":  str(row[6]),
                    "worker_db":   worker.name,
                    "worker_id":   worker.id,
                }, "OK"
            finally:
                w_session.close()
        except Exception as e:
            return False, None, str(e)
        finally:
            m_session.close()

    def search_records(
        self, record_type=None, owner=None, page=1, limit=50
    ) -> List[Dict]:
        results  = []
        m_session = pool_manager.get_master_session()
        try:
            workers = m_session.query(WorkerDatabase).filter_by(
                is_active=True
            ).all()
            for worker in workers:
                try:
                    w_session = pool_manager.get_worker_session(
                        worker.id, worker.connection_url
                    )
                    conds  = []
                    params = {"limit": limit, "offset": (page - 1) * limit}
                    if record_type:
                        conds.append("record_type=:rt")
                        params["rt"] = record_type
                    if owner:
                        conds.append("owner_username=:own")
                        params["own"] = owner
                    where = "WHERE " + " AND ".join(conds) if conds else ""
                    rows = w_session.execute(text(f"""
                        SELECT shard_key, record_type, data_json,
                               owner_username, created_at
                        FROM data_records {where}
                        ORDER BY created_at DESC
                        LIMIT :limit OFFSET :offset
                    """), params).fetchall()
                    for r in rows:
                        results.append({
                            "shard_key":   r[0],
                            "record_type": r[1],
                            "data":        json.loads(r[2]) if r[2] else {},
                            "owner":       r[3],
                            "created_at":  str(r[4]),
                            "worker_db":   worker.name
                        })
                    w_session.close()
                except Exception as e:
                    logger.error(f"Search error on #{worker.id}: {e}")
        finally:
            m_session.close()
        return results

    def delete_record(self, shard_key: str, by: str) -> Tuple[bool, str]:
        m_session = pool_manager.get_master_session()
        try:
            mapping = m_session.query(DataShardMapping).filter_by(
                shard_key=shard_key
            ).first()
            if not mapping:
                return False, "Record not found."
            worker = m_session.query(WorkerDatabase).get(mapping.worker_db_id)
            if worker:
                w_session = pool_manager.get_worker_session(
                    worker.id, worker.connection_url
                )
                try:
                    w_session.execute(text(
                        "DELETE FROM data_records WHERE shard_key=:k"
                    ), {"k": shard_key})
                    w_session.commit()
                    worker.size_used_mb -= mapping.size_bytes / (1024 * 1024)
                    worker.record_count -= 1
                finally:
                    w_session.close()
            m_session.delete(mapping)
            m_session.commit()
            return True, f"Record '{shard_key}' deleted."
        except Exception as e:
            m_session.rollback()
            return False, str(e)
        finally:
            m_session.close()

    # ── PING / ANTI-SLEEP ────────────────────────────────────────────────────
    def ping_all_workers(self) -> Dict:
        m_session = pool_manager.get_master_session()
        results   = {"success": 0, "failed": 0, "details": []}
        try:
            workers = m_session.query(WorkerDatabase).filter_by(is_active=True).all()
            for w in workers:
                test = self._test_connection(w.connection_url)
                if test["success"]:
                    w.last_pinged      = datetime.utcnow()
                    w.ping_status      = "online"
                    w.size_used_mb     = test.get("size_mb", w.size_used_mb)
                    w.last_size_check  = datetime.utcnow()
                    results["success"] += 1
                    results["details"].append({
                        "worker": w.name, "status": "online",
                        "size_mb": round(test.get("size_mb", 0), 2)
                    })
                else:
                    w.ping_status  = "offline"
                    results["failed"] += 1
                    results["details"].append({
                        "worker": w.name, "status": "offline",
                        "error":  test.get("error")
                    })
            m_session.commit()
        except Exception as e:
            logger.error(f"Ping error: {e}")
        finally:
            m_session.close()
        return results

    # ── STATS ─────────────────────────────────────────────────────────────────
    def get_stats(self) -> Dict:
        m_session = pool_manager.get_master_session()
        try:
            workers          = m_session.query(WorkerDatabase).all()
            total_workers    = len(workers)
            active_workers   = sum(1 for w in workers if w.is_active)
            total_size_mb    = sum(w.size_used_mb for w in workers)
            total_cap_mb     = sum(w.max_size_mb  for w in workers)
            total_records    = sum(w.record_count  for w in workers)
            user_count       = m_session.query(UserAccount).count()
            admin_count      = m_session.query(UserAccount).filter_by(
                role="admin"
            ).count()
            current_writer   = m_session.query(WorkerDatabase).filter_by(
                is_current_write=True
            ).first()
            recent_logs      = m_session.query(ActivityLog).order_by(
                ActivityLog.timestamp.desc()
            ).limit(20).all()

            return {
                "total_workers":   total_workers,
                "active_workers":  active_workers,
                "total_size_mb":   round(total_size_mb, 2),
                "total_size_gb":   round(total_size_mb / 1024, 3),
                "total_cap_mb":    total_cap_mb,
                "total_cap_gb":    round(total_cap_mb / 1024, 2),
                "usage_percent":   round(
                    (total_size_mb / total_cap_mb * 100) if total_cap_mb > 0 else 0, 2
                ),
                "total_records":   total_records,
                "user_count":      user_count,
                "admin_count":     admin_count,
                "current_write_db": {
                    "id":      current_writer.id,
                    "name":    current_writer.name,
                    "size_mb": round(current_writer.size_used_mb, 2)
                } if current_writer else None,
                "workers": [{
                    "id":            w.id,
                    "name":          w.name,
                    "is_active":     w.is_active,
                    "is_current_write": w.is_current_write,
                    "size_used_mb":  round(w.size_used_mb, 2),
                    "max_size_mb":   w.max_size_mb,
                    "usage_percent": round(
                        (w.size_used_mb / w.max_size_mb * 100)
                        if w.max_size_mb > 0 else 0, 1
                    ),
                    "record_count":  w.record_count,
                    "last_pinged":   str(w.last_pinged) if w.last_pinged else None,
                    "ping_status":   w.ping_status,
                    "added_by":      w.added_by,
                    "notes":         w.notes,
                } for w in workers],
                "recent_logs": [{
                    "user":      l.user,
                    "action":    l.action,
                    "details":   l.details,
                    "timestamp": str(l.timestamp),
                    "level":     l.level,
                } for l in recent_logs],
            }
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {}
        finally:
            m_session.close()

    # ── ACTIVITY LOG ─────────────────────────────────────────────────────────
    def _log(self, session, user, action, details=None, level="INFO", ip=None):
        try:
            session.add(ActivityLog(
                user=user, action=action, details=details,
                level=level, ip_address=ip
            ))
        except Exception:
            pass

    def log_activity(self, user, action, details=None, level="INFO", ip=None):
        session = pool_manager.get_master_session()
        try:
            self._log(session, user, action, details, level, ip)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

db_router = DatabaseRouter()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    username: str
    password: str

class AddWorkerRequest(BaseModel):
    connection_url: str
    name: str
    notes: Optional[str] = ""

    @field_validator("connection_url")
    @classmethod
    def validate_url(cls, v):
        if not (v.startswith("postgresql://") or v.startswith("postgres://")):
            raise ValueError("Must be a valid PostgreSQL URL")
        return v

class WriteRecordRequest(BaseModel):
    shard_key: str
    record_type: str = "generic"
    data: Dict[str, Any]

class CreateUserRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    role: str = "user"

class UpdateUIRequest(BaseModel):
    design_key: str
    design_value: str

class BulkUIRequest(BaseModel):
    updates: Dict[str, str]

class UpdateConfigRequest(BaseModel):
    config_key: str
    config_value: str

class UpdateBalanceRequest(BaseModel):
    username: str
    new_balance: float

class UpdateContactRequest(BaseModel):
    username: str
    contact_info: str

class MaintenanceRequest(BaseModel):
    enabled: bool

class MediaRequest(BaseModel):
    bg_video_url: Optional[str] = None
    bg_music_url: Optional[str] = None
    bg_music_autoplay: Optional[bool] = None

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: AUTH HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def create_token(data: dict) -> str:
    payload = {**data, "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

def authenticate_user(username: str, password: str) -> Optional[UserAccount]:
    session = pool_manager.get_master_session()
    try:
        user = session.query(UserAccount).filter_by(
            username=username, is_active=True
        ).first()
        if not user or not verify_password(password, user.password_hash):
            return None
        user.last_login = datetime.utcnow()
        session.commit()
        return user
    finally:
        session.close()

def get_user_from_request(request: Request) -> Optional[dict]:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    return decode_token(token) if token else None

async def require_auth(request: Request) -> dict:
    user = get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

async def require_admin(request: Request) -> dict:
    user = await require_auth(request)
    if user.get("role") not in ("admin", "owner"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

async def require_owner(request: Request) -> dict:
    user = await require_auth(request)
    if user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Owner access required")
    return user

def create_user_account(
    username, password, role, email=None, created_by=None
) -> Tuple[bool, str]:
    session = pool_manager.get_master_session()
    try:
        if session.query(UserAccount).filter_by(username=username).first():
            return False, "Username already exists"
        session.add(UserAccount(
            username=username, email=email,
            password_hash=hash_password(password),
            role=role, created_by=created_by
        ))
        session.commit()
        return True, f"User '{username}' created successfully"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7: SCHEDULER
# ═══════════════════════════════════════════════════════════════════════════════

scheduler = BackgroundScheduler()

def run_anti_sleep():
    try:
        if db_router.get_config("anti_sleep_enabled", "true").lower() == "true":
            logger.info("🔔 Anti-sleep ping running...")
            r = db_router.ping_all_workers()
            logger.info(f"Ping: {r['success']} online, {r['failed']} offline")
    except Exception as e:
        logger.error(f"Anti-sleep error: {e}")

def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            run_anti_sleep,
            trigger=IntervalTrigger(minutes=PING_INTERVAL_MINUTES),
            id="anti_sleep", replace_existing=True
        )
        scheduler.start()
        logger.info("✅ Scheduler started")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8: HTML TEMPLATES (INLINE STRINGS)
# ═══════════════════════════════════════════════════════════════════════════════

def build_base_styles(ui: dict) -> str:
    """Returns <style> block with dynamic CSS variables."""
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Orbitron:wght@400;600;700;900&display=swap');
    :root {{
        --primary:   {ui.get('primary_color',   '#6C63FF')};
        --secondary: {ui.get('secondary_color', '#FF6584')};
        --bg:        {ui.get('background_color','#0F0F1A')};
        --card:      {ui.get('card_color',      '#1A1A2E')};
        --text:      {ui.get('text_color',      '#FFFFFF')};
        --font:      {ui.get('font_family',     'Inter, sans-serif')};
    }}
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    html{{scroll-behavior:smooth}}
    body{{
        background:var(--bg);color:var(--text);
        font-family:var(--font);min-height:100vh;overflow-x:hidden;
    }}
    a{{text-decoration:none;color:inherit}}
    #bg-vid-wrap{{
        position:fixed;top:0;left:0;width:100%;height:100%;z-index:-2;overflow:hidden;
    }}
    #bg-vid{{width:100%;height:100%;object-fit:cover;opacity:.3}}
    .vid-overlay{{
        position:fixed;top:0;left:0;width:100%;height:100%;
        background:linear-gradient(135deg,rgba(15,15,26,.88),rgba(26,26,46,.78));z-index:-1;
    }}
    .glass{{
        background:rgba(26,26,46,.7);backdrop-filter:blur(20px);
        -webkit-backdrop-filter:blur(20px);
        border:1px solid rgba(108,99,255,.2);border-radius:16px;
        transition:all .3s ease;
    }}
    .glass:hover{{
        border-color:rgba(108,99,255,.5);transform:translateY(-2px);
        box-shadow:0 20px 60px rgba(108,99,255,.15);
    }}
    .btn{{
        background:linear-gradient(135deg,var(--primary),var(--secondary));
        border:none;color:#fff;padding:.65rem 1.5rem;border-radius:50px;
        cursor:pointer;font-weight:700;font-size:.9rem;
        transition:all .3s ease;box-shadow:0 4px 20px rgba(108,99,255,.4);
        display:inline-flex;align-items:center;gap:.4rem;
    }}
    .btn:hover{{transform:translateY(-2px);box-shadow:0 8px 30px rgba(108,99,255,.6)}}
    .btn:active{{transform:translateY(0)}}
    .btn:disabled{{opacity:.6;cursor:not-allowed;transform:none}}
    .btn-outline{{
        background:transparent;border:1px solid rgba(108,99,255,.5);
        color:var(--primary);border-radius:50px;padding:.6rem 1.4rem;
        cursor:pointer;font-weight:600;transition:all .3s;
    }}
    .btn-outline:hover{{background:rgba(108,99,255,.1)}}
    .btn-danger{{background:linear-gradient(135deg,#ef4444,#b91c1c)}}
    .btn-success{{background:linear-gradient(135deg,#10b981,#065f46)}}
    .btn-warn{{background:linear-gradient(135deg,#f59e0b,#d97706)}}
    .btn-sm{{padding:.4rem 1rem;font-size:.78rem}}
    .neon{{
        color:var(--primary);
        text-shadow:0 0 10px rgba(108,99,255,.8),0 0 30px rgba(108,99,255,.5);
    }}
    .progress{{height:6px;border-radius:3px;background:rgba(255,255,255,.1);overflow:hidden}}
    .progress-fill{{
        height:100%;border-radius:3px;
        background:linear-gradient(90deg,var(--primary),var(--secondary));
        transition:width .5s ease;
    }}
    .badge{{
        font-size:.6rem;padding:2px 8px;border-radius:20px;font-weight:800;
        letter-spacing:.05em;display:inline-block;
    }}
    .badge-owner{{background:linear-gradient(135deg,#f59e0b,#d97706)}}
    .badge-admin{{background:linear-gradient(135deg,#6C63FF,#8B5CF6)}}
    .badge-user{{background:rgba(255,255,255,.1)}}
    .badge-online{{color:#10b981}}
    .badge-offline{{color:#ef4444}}
    .inp{{
        width:100%;padding:.75rem 1rem;border-radius:12px;
        background:rgba(255,255,255,.05);border:1px solid rgba(108,99,255,.25);
        color:var(--text);font-size:.9rem;transition:border-color .2s;outline:none;
        font-family:var(--font);
    }}
    .inp:focus{{border-color:var(--primary)}}
    .inp::placeholder{{color:rgba(255,255,255,.3)}}
    select.inp{{background:rgba(26,26,46,.95)}}
    textarea.inp{{resize:vertical}}
    .label{{display:block;font-size:.8rem;color:rgba(255,255,255,.6);margin-bottom:.4rem;font-weight:500}}
    .form-group{{margin-bottom:1rem}}
    #toast-wrap{{
        position:fixed;top:1rem;right:1rem;z-index:9999;
        display:flex;flex-direction:column;gap:.5rem;pointer-events:none;
    }}
    .toast{{
        padding:.85rem 1.25rem;border-radius:12px;font-weight:500;font-size:.85rem;
        animation:toastIn .3s ease;max-width:340px;pointer-events:all;
        display:flex;align-items:center;gap:.5rem;
    }}
    .toast-s{{background:#064e3b;border:1px solid #10b981;color:#d1fae5}}
    .toast-e{{background:#7f1d1d;border:1px solid #ef4444;color:#fee2e2}}
    .toast-i{{background:#1e3a5f;border:1px solid #3b82f6;color:#dbeafe}}
    @keyframes toastIn{{from{{transform:translateX(110%);opacity:0}}to{{transform:none;opacity:1}}}}
    .spin{{
        width:18px;height:18px;border:2px solid rgba(255,255,255,.2);
        border-top-color:var(--primary);border-radius:50%;
        animation:spinning .7s linear infinite;display:inline-block;
    }}
    @keyframes spinning{{to{{transform:rotate(360deg)}}}}
    #music-btn{{
        position:fixed;bottom:70px;right:1rem;z-index:99;
        background:rgba(26,26,46,.9);backdrop-filter:blur(20px);
        border:1px solid rgba(108,99,255,.35);border-radius:50px;
        padding:.45rem 1rem;display:flex;align-items:center;gap:.5rem;
        cursor:pointer;font-size:.75rem;color:rgba(255,255,255,.7);
        transition:all .2s;
    }}
    #music-btn:hover{{border-color:var(--primary);color:#fff}}
    .mobile-nav{{
        position:fixed;bottom:0;left:0;right:0;
        background:rgba(26,26,46,.97);backdrop-filter:blur(20px);
        border-top:1px solid rgba(108,99,255,.2);z-index:100;padding:.4rem 0;
        display:grid;grid-template-columns:repeat(5,1fr);
    }}
    .mn-tab{{
        display:flex;flex-direction:column;align-items:center;padding:.35rem;
        font-size:.6rem;color:rgba(255,255,255,.45);cursor:pointer;
        border-radius:8px;transition:color .2s;border:none;background:none;
    }}
    .mn-tab i{{font-size:1.1rem;margin-bottom:2px}}
    .mn-tab.active,.mn-tab:hover{{color:var(--primary)}}
    .sidebar{{
        width:220px;position:fixed;left:0;top:0;height:100%;
        padding:5rem 1rem 1rem;overflow-y:auto;
        background:rgba(15,15,26,.5);border-right:1px solid rgba(108,99,255,.08);
    }}
    .sb-section{{
        font-size:.65rem;font-weight:800;color:rgba(255,255,255,.35);
        letter-spacing:.1em;text-transform:uppercase;
        padding:.5rem .75rem .25rem;margin-top:.5rem;
    }}
    .sb-btn{{
        width:100%;display:flex;align-items:center;gap:.6rem;
        padding:.6rem .75rem;border-radius:10px;font-size:.82rem;
        color:rgba(255,255,255,.6);cursor:pointer;border:none;background:none;
        transition:all .2s;text-align:left;
    }}
    .sb-btn:hover,.sb-btn.active{{
        background:rgba(108,99,255,.12);color:#fff;
    }}
    .sb-btn.active{{font-weight:600}}
    .main-content{{margin-left:220px;padding:5rem 2rem 2rem}}
    .section{{display:none}}
    .section.active{{display:block}}
    .grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}
    .grid-4{{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem}}
    .stat-card{{padding:1.25rem;text-align:center}}
    .stat-val{{font-size:2rem;font-weight:900;line-height:1}}
    .stat-lbl{{font-size:.72rem;color:rgba(255,255,255,.5);margin-top:.3rem;text-transform:uppercase;letter-spacing:.05em}}
    .worker-row{{
        display:flex;align-items:center;gap:.75rem;padding:.85rem;
        border-radius:12px;border:1px solid rgba(255,255,255,.05);
        background:rgba(255,255,255,.02);transition:background .2s;
    }}
    .worker-row:hover{{background:rgba(255,255,255,.04)}}
    .user-row{{
        display:flex;align-items:center;gap:.75rem;padding:.85rem;
        border-radius:12px;border:1px solid rgba(255,255,255,.05);
        background:rgba(255,255,255,.02);
    }}
    .log-row{{
        display:flex;align-items:flex-start;gap:.6rem;padding:.65rem;
        border-radius:10px;border:1px solid rgba(255,255,255,.04);
        background:rgba(255,255,255,.01);font-size:.8rem;
    }}
    .topbar{{
        position:fixed;top:0;left:0;right:0;z-index:50;
        display:flex;align-items:center;justify-content:space-between;
        padding:.85rem 2rem;
        background:rgba(15,15,26,.9);backdrop-filter:blur(20px);
        border-bottom:1px solid rgba(108,99,255,.12);
    }}
    .color-row{{display:flex;align-items:center;gap:.75rem;margin-bottom:.75rem}}
    code{{
        background:rgba(108,99,255,.15);padding:1px 6px;border-radius:4px;
        font-family:monospace;font-size:.82em;color:var(--primary);
    }}
    ::-webkit-scrollbar{{width:5px}}
    ::-webkit-scrollbar-track{{background:var(--bg)}}
    ::-webkit-scrollbar-thumb{{background:var(--primary);border-radius:3px}}
    @media(max-width:768px){{
        .sidebar{{display:none}}
        .main-content{{margin-left:0;padding:4.5rem 1rem 5rem}}
        .grid-4{{grid-template-columns:1fr 1fr}}
        .grid-2{{grid-template-columns:1fr}}
        .topbar{{padding:.75rem 1rem}}
        .hide-mobile{{display:none}}
    }}
    {ui.get('custom_css', '')}
    </style>
    """

BASE_JS = """
<script>
const API = {
    token: getCookie('access_token'),
    async req(method, url, data=null) {
        const opts = {
            method,
            headers: {
                'Content-Type': 'application/json',
                ...(this.token ? {'Authorization': `Bearer ${this.token}`} : {})
            }
        };
        if (data) opts.body = JSON.stringify(data);
        const res  = await fetch(url, opts);
        const json = await res.json();
        if (!res.ok) throw new Error(json.detail || 'Request failed');
        return json;
    },
    get:    (u)    => API.req('GET',    u),
    post:   (u, d) => API.req('POST',   u, d),
    put:    (u, d) => API.req('PUT',    u, d),
    delete: (u)    => API.req('DELETE', u),
};

function getCookie(n) {
    const v = `; ${document.cookie}`;
    const p = v.split(`; ${n}=`);
    if (p.length === 2) return p.pop().split(';').shift();
    return null;
}

function toast(msg, type='s', dur=4000) {
    const c = document.getElementById('toast-wrap');
    const t = document.createElement('div');
    const icons = {s:'✅', e:'❌', i:'ℹ️'};
    t.className = `toast toast-${type}`;
    t.innerHTML = `<span>${icons[type]||'📢'}</span><span>${msg}</span>`;
    c.appendChild(t);
    setTimeout(() => {
        t.style.animation = 'toastIn .3s ease reverse';
        setTimeout(() => t.remove(), 300);
    }, dur);
}

function setLoading(btn, loading) {
    if (loading) {
        btn._orig = btn.innerHTML;
        btn.innerHTML = '<span class="spin"></span> Loading...';
        btn.disabled = true;
    } else {
        btn.innerHTML = btn._orig || btn.innerHTML;
        btn.disabled = false;
    }
}

let musicOn = false;
function toggleMusic() {
    const a = document.getElementById('bg-audio');
    if (!a) return;
    const ic = document.getElementById('micon');
    const st = document.getElementById('mstat');
    if (musicOn) {
        a.pause();
        if(ic) ic.className = 'fas fa-music';
        if(st) st.textContent = 'Music';
    } else {
        a.play().catch(()=>{});
        if(ic) ic.className = 'fas fa-pause';
        if(st) st.textContent = 'Playing';
    }
    musicOn = !musicOn;
}

function showSec(id) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    const t = document.getElementById(id);
    if (t) { t.classList.add('active'); window.scrollTo({top:0}); }
    document.querySelectorAll('.sb-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.sec === id);
    });
    const loaders = {
        'sec-overview': loadOverview,
        'sec-db':       loadWorkers,
        'sec-users':    loadUsers,
        'sec-logs':     loadLogs,
        'sec-profile':  loadProfile,
    };
    if (loaders[id]) loaders[id]();
    history.pushState(null, '', '#' + id);
}
</script>
"""

def render_maintenance_page(ui: dict) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Maintenance - {ui.get('logo_text','RUHI-VIG QNR')}</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
{build_base_styles(ui)}
</head><body>
<div id="toast-wrap"></div>
{BASE_JS}
<div style="min-height:100vh;display:flex;align-items:center;justify-content:center;padding:1rem">
  <div class="glass" style="padding:3rem;text-align:center;max-width:480px;width:100%">
    <div style="font-size:5rem;margin-bottom:1.5rem">🔧</div>
    <div style="font-family:Orbitron,sans-serif;font-size:1.8rem;font-weight:900;margin-bottom:.5rem" class="neon">
      {ui.get('logo_text','RUHI-VIG QNR')}
    </div>
    <h1 style="font-size:1.4rem;font-weight:700;margin-bottom:1rem">System Maintenance</h1>
    <p style="color:rgba(255,255,255,.6);line-height:1.7;margin-bottom:2rem">
      We are performing scheduled database maintenance.<br>
      The system will return shortly. Thank you!
    </p>
    <div style="display:flex;justify-content:center;gap:.5rem;margin-bottom:2rem">
      {''.join(['<div style="width:10px;height:10px;border-radius:50%;background:var(--primary);animation:spinning 1.2s ease-in-out infinite;animation-delay:'+str(i*.2)+'s"></div>' for i in range(3)])}
    </div>
    <a href="/login" class="btn-outline" style="font-size:.85rem">
      <i class="fas fa-sign-in-alt"></i> Admin Login
    </a>
  </div>
</div>
<script>
setInterval(async()=>{{
  try{{
    const r = await fetch('/api/ping');
    const d = await r.json();
    if(!d.maintenance) location.reload();
  }}catch{{}}
}}, 30000);
</script>
</body></html>"""

def render_login_page(ui: dict, error: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Login - {ui.get('logo_text','RUHI-VIG QNR')}</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<script src="https://cdn.tailwindcss.com"></script>
{build_base_styles(ui)}
</head><body>
<div id="toast-wrap"></div>
{BASE_JS}

<div style="min-height:100vh;display:flex;align-items:center;justify-content:center;padding:1rem">
  <div class="glass" style="padding:2.5rem;width:100%;max-width:420px">

    <!-- Logo -->
    <div style="text-align:center;margin-bottom:2rem">
      <div style="font-family:Orbitron,sans-serif;font-size:2rem;font-weight:900" class="neon">
        {ui.get('logo_text','RUHI-VIG QNR')}
      </div>
      <p style="color:rgba(255,255,255,.5);font-size:.82rem;margin-top:.4rem">
        Distributed Database Cloud System
      </p>
      <div style="display:flex;justify-content:center;gap:4px;margin-top:.75rem">
        <div style="height:3px;width:30px;border-radius:2px;background:var(--primary)"></div>
        <div style="height:3px;width:16px;border-radius:2px;background:var(--secondary)"></div>
        <div style="height:3px;width:8px;border-radius:2px;background:var(--primary)"></div>
      </div>
    </div>

    <!-- Form -->
    <form id="lform" onsubmit="doLogin(event)">
      <div class="form-group">
        <label class="label">
          <i class="fas fa-user" style="color:var(--primary)"></i> Username
        </label>
        <input id="lu" type="text" class="inp" placeholder="Enter username"
               autocomplete="username" required>
      </div>
      <div class="form-group">
        <label class="label">
          <i class="fas fa-lock" style="color:var(--secondary)"></i> Password
        </label>
        <div style="position:relative">
          <input id="lp" type="password" class="inp" placeholder="Enter password"
                 autocomplete="current-password" required style="padding-right:3rem">
          <button type="button" onclick="togglePwd()" style="
            position:absolute;right:.75rem;top:50%;transform:translateY(-50%);
            background:none;border:none;color:rgba(255,255,255,.5);cursor:pointer;
          "><i id="eye" class="fas fa-eye"></i></button>
        </div>
      </div>

      {'<div style="color:#f87171;font-size:.82rem;text-align:center;padding:.6rem;background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);border-radius:10px;margin-bottom:1rem">'+error+'</div>' if error else ''}

      <button type="submit" id="lbtn" class="btn" style="width:100%;justify-content:center;padding:.85rem">
        <i class="fas fa-sign-in-alt"></i> Sign In
      </button>
    </form>

    <!-- Status -->
    <div style="margin-top:1.5rem;padding-top:1.5rem;border-top:1px solid rgba(255,255,255,.07);text-align:center">
      <div id="sys-status" style="font-size:.78rem;color:rgba(255,255,255,.4)">
        <span class="spin"></span> Checking system...
      </div>
    </div>
    <div style="text-align:center;margin-top:.75rem;font-size:.7rem;color:rgba(255,255,255,.2)">
      v2.0.0 © {datetime.utcnow().year} RUHI-VIG QNR
    </div>
  </div>
</div>

<script>
async function doLogin(e) {{
  e.preventDefault();
  const btn = document.getElementById('lbtn');
  setLoading(btn, true);
  try {{
    const r = await API.post('/api/auth/login', {{
      username: document.getElementById('lu').value.trim(),
      password: document.getElementById('lp').value
    }});
    if (r.success) {{
      toast(`Welcome, ${{r.username}}! 🎉`);
      setTimeout(() => location.href = '/dashboard', 700);
    }}
  }} catch(err) {{
    toast(err.message, 'e');
  }} finally {{
    setLoading(btn, false);
  }}
}}

function togglePwd() {{
  const i = document.getElementById('lp');
  const e = document.getElementById('eye');
  i.type = i.type === 'password' ? 'text' : 'password';
  e.className = i.type === 'password' ? 'fas fa-eye' : 'fas fa-eye-slash';
}}

async function checkSys() {{
  const d = document.getElementById('sys-status');
  try {{
    const r = await API.get('/api/ping');
    d.innerHTML = r.maintenance
      ? '<span style="color:#f59e0b"><i class="fas fa-wrench"></i> Maintenance Active</span>'
      : '<span style="color:#10b981"><i class="fas fa-circle" style="font-size:.5rem"></i> System Online</span>';
  }} catch {{
    d.innerHTML = '<span style="color:#ef4444"><i class="fas fa-circle" style="font-size:.5rem"></i> Offline</span>';
  }}
}}
checkSys();
</script>
</body></html>"""

def render_dashboard(ui: dict, user: dict) -> str:
    role = user.get("role", "user")
    username = user.get("sub", "")
    is_admin_or_owner = role in ("admin", "owner")
    is_owner = role == "owner"

    sidebar_items = [
        ("sec-overview", "fa-th-large",    "Overview",    "var(--primary)",  True),
    ]
    if is_admin_or_owner:
        sidebar_items += [
            ("sec-db",      "fa-database",   "DB Manager",  "var(--secondary)", True),
            ("sec-data",    "fa-search",     "Data Explorer","#60a5fa",         True),
        ]
    sidebar_items += [
        ("sec-users",   "fa-users",      "Users",       "#34d399",         is_admin_or_owner),
        ("sec-logs",    "fa-history",    "Activity Log","#fbbf24",         True),
    ]
    if is_admin_or_owner:
        sidebar_items += [
            ("sec-ui",    "fa-paint-brush","UI Editor",   "#f472b6",         True),
            ("sec-media", "fa-film",       "Media",       "#a78bfa",         True),
        ]
    if is_owner:
        sidebar_items += [
            ("sec-sys",   "fa-cog",        "System",      "#f87171",         True),
        ]
    sidebar_items += [
        ("sec-profile","fa-user-circle","Profile",     "#22d3ee",         True),
    ]

    sidebar_html = ""
    prev_group   = ""
    groups = {
        "sec-overview": "Main",
        "sec-db":       "Database",
        "sec-data":     "Database",
        "sec-users":    "Management",
        "sec-logs":     "Management",
        "sec-ui":       "Design",
        "sec-media":    "Design",
        "sec-sys":      "Owner",
        "sec-profile":  "Account",
    }
    for sec_id, icon, label, color, visible in sidebar_items:
        if not visible:
            continue
        grp = groups.get(sec_id, "")
        if grp != prev_group:
            sidebar_html += f'<div class="sb-section">{grp}</div>'
            prev_group = grp
        sidebar_html += f"""
        <button class="sb-btn" data-sec="{sec_id}" onclick="showSec('{sec_id}')">
          <i class="fas {icon}" style="color:{color};width:16px"></i>
          {label}
        </button>"""

    mobile_nav_html = ""
    mobile_tabs = [
        ("sec-overview","fa-th-large","Home"),
        ("sec-db","fa-database","DB") if is_admin_or_owner else ("sec-profile","fa-user-circle","Profile"),
        ("sec-data","fa-search","Data") if is_admin_or_owner else ("sec-logs","fa-history","Logs"),
        ("sec-users","fa-users","Users"),
        ("sec-profile","fa-user-circle","Me"),
    ]
    for sec_id, icon, label in mobile_tabs:
        mobile_nav_html += f"""
        <button class="mn-tab" data-sec="{sec_id}" onclick="showSec('{sec_id}')">
          <i class="fas {icon}"></i>{label}
        </button>"""

    maintenance_banner = ""
    if db_router.is_maintenance():
        maintenance_banner = f"""
        <div style="margin:.75rem;padding:1rem;border-radius:12px;
          background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.4);
          display:flex;align-items:center;gap:.75rem;flex-wrap:wrap">
          <i class="fas fa-wrench" style="color:#f59e0b;font-size:1.2rem"></i>
          <div style="flex:1">
            <div style="font-weight:700;color:#f59e0b">Maintenance Mode Active</div>
            <div style="font-size:.78rem;color:rgba(255,255,255,.5)">
              Regular users cannot access the system.
            </div>
          </div>
          {'<button class="btn btn-success btn-sm" onclick="toggleMaint(false)"><i class="fas fa-lock-open"></i> Disable</button>' if is_owner else ''}
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dashboard - {ui.get('logo_text','RUHI-VIG QNR')}</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
{build_base_styles(ui)}
</head><body>
<div id="toast-wrap"></div>
{BASE_JS}

<!-- Background Video -->
{f'<div id="bg-vid-wrap"><video id="bg-vid" autoplay muted loop playsinline><source src="{db_router.get_config("bg_video_url","")}" type="video/mp4"></video></div><div class="vid-overlay"></div>' if db_router.get_config("bg_video_url","") else ""}

<!-- Background Music -->
{f'<audio id="bg-audio" loop {"autoplay" if db_router.get_config("bg_music_autoplay","false")=="true" else ""}><source src="{db_router.get_config("bg_music_url","")}" type="audio/mpeg"></audio><div id="music-btn" onclick="toggleMusic()"><i class="fas fa-music" id="micon" style="color:var(--primary)"></i><span id="mstat">Music</span></div>' if db_router.get_config("bg_music_url","") else ""}

<!-- Top Bar -->
<div class="topbar">
  <div style="display:flex;align-items:center;gap:.75rem">
    <span style="font-family:Orbitron,sans-serif;font-weight:900;font-size:1.1rem" class="neon">
      {ui.get('logo_text','RUHI-VIG QNR')}
    </span>
    <span class="badge badge-{role}">{role.upper()}</span>
  </div>
  <div style="display:flex;align-items:center;gap:1rem">
    <span style="font-size:.82rem;color:rgba(255,255,255,.5)" class="hide-mobile">{username}</span>
    <a href="/logout" style="font-size:.82rem;color:rgba(255,255,255,.4)" title="Logout">
      <i class="fas fa-sign-out-alt"></i>
      <span class="hide-mobile"> Logout</span>
    </a>
  </div>
</div>

<!-- Maintenance Banner -->
{maintenance_banner}

<!-- Sidebar (desktop) -->
<div class="sidebar">
  {sidebar_html}
</div>

<!-- Main Content -->
<div class="main-content">

<!-- ═══ OVERVIEW ═══ -->
<div id="sec-overview" class="section active">
  <h2 style="font-size:1.5rem;font-weight:800;margin-bottom:1.5rem">
    <i class="fas fa-th-large" style="color:var(--primary)"></i> System Overview
  </h2>
  <div class="grid-4" style="margin-bottom:1.5rem">
    <div class="glass stat-card">
      <div class="stat-val neon" id="ov-dbs">—</div>
      <div class="stat-lbl">Active DBs</div>
    </div>
    <div class="glass stat-card">
      <div class="stat-val" style="color:var(--secondary)" id="ov-storage">—</div>
      <div class="stat-lbl">Storage</div>
    </div>
    <div class="glass stat-card">
      <div class="stat-val" style="color:#34d399" id="ov-records">—</div>
      <div class="stat-lbl">Records</div>
    </div>
    <div class="glass stat-card">
      <div class="stat-val" style="color:#fbbf24" id="ov-users">—</div>
      <div class="stat-lbl">Users</div>
    </div>
  </div>
  <div class="glass" style="padding:1.5rem;margin-bottom:1.5rem">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.75rem">
      <span style="font-weight:600">Global Storage Usage</span>
      <span id="ov-pct" style="color:var(--primary);font-weight:800">—%</span>
    </div>
    <div class="progress" style="margin-bottom:.5rem">
      <div class="progress-fill" id="ov-bar" style="width:0%"></div>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:.75rem;color:rgba(255,255,255,.4)">
      <span id="ov-used">Used: —</span>
      <span id="ov-cap">Capacity: —</span>
    </div>
  </div>
  <div class="glass" style="padding:1.25rem">
    <div style="font-weight:600;margin-bottom:.75rem">
      <i class="fas fa-pen-nib" style="color:#fbbf24"></i> Current Write Target
    </div>
    <div id="ov-writer" style="color:rgba(255,255,255,.5)">Loading...</div>
  </div>
</div>

<!-- ═══ DB MANAGER ═══ -->
{'<div id="sec-db" class="section">' if is_admin_or_owner else '<div id="sec-db" class="section" style="display:none">'}
  <h2 style="font-size:1.5rem;font-weight:800;margin-bottom:1.5rem">
    <i class="fas fa-database" style="color:var(--secondary)"></i> Database Pool Manager
  </h2>
  <!-- Add DB Form -->
  <div class="glass" style="padding:1.5rem;margin-bottom:1.5rem">
    <h3 style="font-weight:700;margin-bottom:1rem">
      <i class="fas fa-plus-circle" style="color:#34d399"></i> Add New Worker Database
    </h3>
    <div class="grid-2" style="margin-bottom:1rem">
      <div class="form-group" style="margin:0">
        <label class="label">Database Name *</label>
        <input id="db-name" type="text" class="inp" placeholder="e.g. Worker-DB-001">
      </div>
      <div class="form-group" style="margin:0">
        <label class="label">Notes (Optional)</label>
        <input id="db-notes" type="text" class="inp" placeholder="e.g. Render Free Tier US-West">
      </div>
    </div>
    <div class="form-group">
      <label class="label">PostgreSQL Connection URL *</label>
      <div style="position:relative">
        <input id="db-url" type="password" class="inp"
               placeholder="postgresql://user:pass@host/dbname"
               style="padding-right:3rem;font-family:monospace">
        <button type="button" onclick="toggleDbUrl()" style="
          position:absolute;right:.75rem;top:50%;transform:translateY(-50%);
          background:none;border:none;color:rgba(255,255,255,.5);cursor:pointer">
          <i id="db-eye" class="fas fa-eye"></i>
        </button>
      </div>
      <div style="font-size:.72rem;color:rgba(255,255,255,.3);margin-top:.3rem">
        URL is validated before being stored securely in the master database.
      </div>
    </div>
    <div style="display:flex;gap:.75rem">
      <button id="add-db-btn" class="btn" onclick="addWorkerDB()">
        <i class="fas fa-plus"></i> Add Database
      </button>
      <button class="btn btn-outline" onclick="testDBConn()">
        <i class="fas fa-plug"></i> Test Connection
      </button>
    </div>
  </div>
  <!-- Worker List -->
  <div class="glass" style="padding:1.5rem">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem">
      <h3 style="font-weight:700">Active Worker Pool</h3>
      <div style="display:flex;gap:.5rem">
        <button class="btn btn-success btn-sm" onclick="pingAll()">
          <i class="fas fa-heartbeat"></i> Ping All
        </button>
        <button class="btn-outline btn-sm" style="padding:.38rem .9rem;font-size:.78rem;border-radius:30px" onclick="loadWorkers()">
          <i class="fas fa-sync"></i> Refresh
        </button>
      </div>
    </div>
    <div id="workers-list">
      <div style="text-align:center;padding:3rem;color:rgba(255,255,255,.3)">
        <span class="spin"></span> Loading...
      </div>
    </div>
  </div>
</div>

<!-- ═══ DATA EXPLORER ═══ -->
{'<div id="sec-data" class="section">' if is_admin_or_owner else '<div id="sec-data" style="display:none">'}
  <h2 style="font-size:1.5rem;font-weight:800;margin-bottom:1.5rem">
    <i class="fas fa-search" style="color:#60a5fa"></i> Data Explorer
  </h2>
  <div class="glass" style="padding:1.5rem;margin-bottom:1.5rem">
    <h3 style="font-weight:700;margin-bottom:1rem">
      <i class="fas fa-pen" style="color:#34d399"></i> Write / Read Record
    </h3>
    <div class="grid-2" style="margin-bottom:1rem">
      <div>
        <label class="label">Shard Key (Unique ID)</label>
        <input id="w-key" type="text" class="inp" placeholder="e.g. user-001-data">
      </div>
      <div>
        <label class="label">Record Type</label>
        <select id="w-type" class="inp">
          <option value="generic">Generic</option>
          <option value="user">User Data</option>
          <option value="file">File Metadata</option>
          <option value="config">Configuration</option>
        </select>
      </div>
    </div>
    <div style="margin-bottom:1rem">
      <label class="label">JSON Data</label>
      <textarea id="w-data" class="inp" rows="5"
                placeholder='{{"key": "value", "name": "example"}}' style="font-family:monospace"></textarea>
    </div>
    <div style="display:flex;gap:.75rem">
      <button class="btn" onclick="writeRec()"><i class="fas fa-save"></i> Write to Pool</button>
      <button class="btn btn-outline" onclick="readRec()"><i class="fas fa-download"></i> Read</button>
    </div>
  </div>
  <div class="glass" style="padding:1.5rem">
    <div style="display:flex;gap:.75rem;margin-bottom:1rem;flex-wrap:wrap">
      <select id="s-type" class="inp" style="width:auto;flex:1;min-width:140px">
        <option value="">All Types</option>
        <option value="generic">Generic</option>
        <option value="user">User</option>
        <option value="file">File</option>
      </select>
      <button class="btn" onclick="searchRecs()"><i class="fas fa-search"></i> Search All DBs</button>
    </div>
    <div id="search-res" style="color:rgba(255,255,255,.3);text-align:center;padding:2rem">
      Results appear here
    </div>
  </div>
</div>

<!-- ═══ USERS ═══ -->
<div id="sec-users" class="section">
  <h2 style="font-size:1.5rem;font-weight:800;margin-bottom:1.5rem">
    <i class="fas fa-users" style="color:#34d399"></i> User Management
  </h2>
  {'<div class="glass" style="padding:1.5rem;margin-bottom:1.5rem"><h3 style="font-weight:700;margin-bottom:1rem"><i class="fas fa-user-plus" style="color:#34d399"></i> Create Account</h3><div class="grid-2" style="margin-bottom:1rem"><div><label class="label">Username *</label><input id="nu-name" type="text" class="inp" placeholder="username"></div><div><label class="label">Email</label><input id="nu-email" type="email" class="inp" placeholder="email@example.com"></div><div><label class="label">Password *</label><input id="nu-pass" type="password" class="inp" placeholder="password"></div><div><label class="label">Role</label><select id="nu-role" class="inp"><option value="user">User</option>' + ('<option value="admin">Admin</option>' if is_owner else '') + '</select></div></div><button class="btn" onclick="createUser()"><i class="fas fa-user-plus"></i> Create User</button></div>' if is_admin_or_owner else ''}
  <div class="glass" style="padding:1.5rem">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem">
      <h3 style="font-weight:700">All Accounts</h3>
      <button class="btn-outline btn-sm" style="padding:.38rem .9rem;font-size:.78rem;border-radius:30px" onclick="loadUsers()">
        <i class="fas fa-sync"></i> Refresh
      </button>
    </div>
    <div id="users-list"><span class="spin"></span></div>
  </div>
</div>

<!-- ═══ ACTIVITY LOG ═══ -->
<div id="sec-logs" class="section">
  <h2 style="font-size:1.5rem;font-weight:800;margin-bottom:1.5rem">
    <i class="fas fa-history" style="color:#fbbf24"></i> Activity Log
  </h2>
  <div class="glass" style="padding:1.5rem">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem">
      <h3 style="font-weight:700">Recent Events</h3>
      <button class="btn-outline btn-sm" style="padding:.38rem .9rem;font-size:.78rem;border-radius:30px" onclick="loadLogs()">
        <i class="fas fa-sync"></i> Refresh
      </button>
    </div>
    <div id="logs-list"><span class="spin"></span></div>
  </div>
</div>

<!-- ═══ UI EDITOR ═══ -->
{'<div id="sec-ui" class="section">' if is_admin_or_owner else '<div id="sec-ui" style="display:none">'}
  <h2 style="font-size:1.5rem;font-weight:800;margin-bottom:1.5rem">
    <i class="fas fa-paint-brush" style="color:#f472b6"></i> Live UI Editor
  </h2>
  <p style="color:rgba(255,255,255,.5);font-size:.83rem;margin-bottom:1.5rem">
    All changes are saved to the master database and applied instantly site-wide.
  </p>
  <div class="grid-2">
    <div class="glass" style="padding:1.5rem">
      <h3 style="font-weight:700;margin-bottom:1rem">
        <i class="fas fa-palette" style="color:var(--primary)"></i> Color Theme
      </h3>
      <div id="color-rows"></div>
      <button class="btn" style="margin-top:.5rem;width:100%;justify-content:center" onclick="saveAllColors()">
        <i class="fas fa-save"></i> Save All Colors
      </button>
    </div>
    <div class="glass" style="padding:1.5rem">
      <h3 style="font-weight:700;margin-bottom:1rem">
        <i class="fas fa-font" style="color:#60a5fa"></i> Site Content
      </h3>
      <div id="text-fields"></div>
    </div>
    <div class="glass" style="padding:1.5rem">
      <h3 style="font-weight:700;margin-bottom:1rem">
        <i class="fas fa-code" style="color:#fbbf24"></i> Custom CSS
      </h3>
      <textarea id="cust-css" class="inp" rows="10" placeholder="/* your CSS */"
                style="font-family:monospace;font-size:.78rem"></textarea>
      <button class="btn" style="margin-top:.75rem;width:100%;justify-content:center"
              onclick="saveUIKey('custom_css', document.getElementById('cust-css').value)">
        <i class="fas fa-save"></i> Apply CSS
      </button>
    </div>
    <div class="glass" style="padding:1.5rem">
      <h3 style="font-weight:700;margin-bottom:1rem">
        <i class="fas fa-code" style="color:#a78bfa"></i> Custom HTML (Header)
      </h3>
      <textarea id="cust-html" class="inp" rows="10" placeholder="<!-- injected in head -->"
                style="font-family:monospace;font-size:.78rem"></textarea>
      <button class="btn btn-warn" style="margin-top:.75rem;width:100%;justify-content:center"
              onclick="saveUIKey('custom_html_header', document.getElementById('cust-html').value)">
        <i class="fas fa-save"></i> Apply HTML
      </button>
      <div style="font-size:.72rem;color:#fbbf24;margin-top:.5rem;padding:.5rem;background:rgba(245,158,11,.08);border-radius:8px">
        ⚠️ Custom HTML/CSS - reload page after saving.
      </div>
    </div>
  </div>
</div>

<!-- ═══ MEDIA ═══ -->
{'<div id="sec-media" class="section">' if is_admin_or_owner else '<div id="sec-media" style="display:none">'}
  <h2 style="font-size:1.5rem;font-weight:800;margin-bottom:1.5rem">
    <i class="fas fa-film" style="color:#a78bfa"></i> Media Settings
  </h2>
  <div class="glass" style="padding:1.5rem">
    <div class="form-group">
      <label class="label"><i class="fas fa-video" style="color:#a78bfa"></i> Background Video URL</label>
      <input id="m-video" type="url" class="inp" placeholder="https://example.com/bg.mp4">
    </div>
    <div class="form-group">
      <label class="label"><i class="fas fa-music" style="color:#f472b6"></i> Background Music URL</label>
      <input id="m-music" type="url" class="inp" placeholder="https://example.com/music.mp3">
    </div>
    <div style="display:flex;align-items:center;gap:.75rem;margin-bottom:1.25rem">
      <input type="checkbox" id="m-auto" style="width:18px;height:18px;accent-color:var(--primary)">
      <label for="m-auto" style="font-size:.85rem;cursor:pointer">Autoplay music on page load</label>
    </div>
    <button class="btn" onclick="saveMedia()">
      <i class="fas fa-save"></i> Save Media Settings
    </button>
  </div>
</div>

<!-- ═══ SYSTEM CONFIG (OWNER) ═══ -->
{'<div id="sec-sys" class="section">' if is_owner else '<div id="sec-sys" style="display:none">'}
  <h2 style="font-size:1.5rem;font-weight:800;margin-bottom:1.5rem">
    <i class="fas fa-cog" style="color:#f87171"></i> System Configuration
  </h2>
  <div class="grid-2">
    <div class="glass" style="padding:1.5rem">
      <h3 style="font-weight:700;margin-bottom:.75rem">
        <i class="fas fa-wrench" style="color:#fbbf24"></i> Maintenance Mode
      </h3>
      <p style="color:rgba(255,255,255,.5);font-size:.82rem;margin-bottom:1rem">
        Enable before monthly database resets. Only Owner can access during maintenance.
      </p>
      <div style="display:flex;gap:.75rem">
        <button class="btn btn-warn" style="flex:1;justify-content:center" onclick="toggleMaint(true)">
          <i class="fas fa-lock"></i> Enable
        </button>
        <button class="btn btn-success" style="flex:1;justify-content:center" onclick="toggleMaint(false)">
          <i class="fas fa-lock-open"></i> Disable
        </button>
      </div>
    </div>
    <div class="glass" style="padding:1.5rem">
      <h3 style="font-weight:700;margin-bottom:.75rem">
        <i class="fas fa-heartbeat" style="color:#34d399"></i> Anti-Sleep Engine
      </h3>
      <p style="color:rgba(255,255,255,.5);font-size:.82rem;margin-bottom:1rem">
        Pings all worker DBs every 10 minutes. Click to trigger manually.
      </p>
      <button class="btn btn-success" style="width:100%;justify-content:center" onclick="manualPing()">
        <i class="fas fa-play"></i> Run Manual Ping
      </button>
    </div>
    <div class="glass" style="padding:1.5rem">
      <h3 style="font-weight:700;margin-bottom:1rem">
        <i class="fas fa-globe" style="color:#60a5fa"></i> Site Settings
      </h3>
      <div class="form-group">
        <label class="label">Site Name</label>
        <div style="display:flex;gap:.5rem">
          <input id="cfg-site-name" type="text" class="inp" placeholder="RUHI-VIG QNR Cloud">
          <button class="btn btn-sm" onclick="saveCfg('site_name', document.getElementById('cfg-site-name').value)">
            <i class="fas fa-save"></i>
          </button>
        </div>
      </div>
      <div class="form-group">
        <label class="label">Site Tagline</label>
        <div style="display:flex;gap:.5rem">
          <input id="cfg-tagline" type="text" class="inp" placeholder="Tagline">
          <button class="btn btn-sm" onclick="saveCfg('site_tagline', document.getElementById('cfg-tagline').value)">
            <i class="fas fa-save"></i>
          </button>
        </div>
      </div>
    </div>
    <div class="glass" style="padding:1.5rem">
      <h3 style="font-weight:700;margin-bottom:1rem">
        <i class="fas fa-chart-bar" style="color:var(--primary)"></i> God-View Stats
      </h3>
      <div id="god-view" style="color:rgba(255,255,255,.5);font-size:.82rem">
        Click refresh to load live stats.
      </div>
      <button class="btn btn-sm" style="margin-top:.75rem" onclick="loadGodView()">
        <i class="fas fa-sync"></i> Refresh Stats
      </button>
    </div>
  </div>
</div>

<!-- ═══ PROFILE ═══ -->
<div id="sec-profile" class="section">
  <h2 style="font-size:1.5rem;font-weight:800;margin-bottom:1.5rem">
    <i class="fas fa-user-circle" style="color:#22d3ee"></i> My Profile
  </h2>
  <div class="glass" style="padding:2rem">
    <div style="display:flex;align-items:center;gap:1.5rem;margin-bottom:2rem;flex-wrap:wrap">
      <div style="
        width:72px;height:72px;border-radius:50%;
        background:linear-gradient(135deg,var(--primary),var(--secondary));
        display:flex;align-items:center;justify-content:center;
        font-size:2rem;font-weight:900;flex-shrink:0
      ">{username[0].upper() if username else "?"}</div>
      <div>
        <div style="font-size:1.4rem;font-weight:800">{username}</div>
        <span class="badge badge-{role}" style="margin-top:.3rem">{role.upper()}</span>
      </div>
    </div>
    <div id="profile-data" style="color:rgba(255,255,255,.5)"><span class="spin"></span></div>
  </div>
</div>

</div><!-- end main-content -->

<!-- Mobile Nav -->
<nav class="mobile-nav" style="display:none;display:grid">
  {mobile_nav_html}
</nav>

<script>
// ─── Page Init ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {{
  const hash = location.hash.replace('#','') || 'sec-overview';
  showSec(hash);
  initUIEditor();
  loadMediaInputs();
  loadSysInputs();
}});

// ─── Show only on mobile ────────────────────────────────────────────────────
if (window.innerWidth <= 768) {{
  document.querySelector('.mobile-nav').style.display = 'grid';
}}

// ─── Overview ───────────────────────────────────────────────────────────────
async function loadOverview() {{
  try {{
    const r = await API.get('/api/system/stats');
    const s = r.stats;
    document.getElementById('ov-dbs').textContent     = s.active_workers || 0;
    document.getElementById('ov-storage').textContent =
      (s.total_size_gb||0).toFixed(3)+' GB';
    document.getElementById('ov-records').textContent =
      (s.total_records||0).toLocaleString();
    document.getElementById('ov-users').textContent   = s.user_count || 0;
    const pct = s.usage_percent || 0;
    document.getElementById('ov-pct').textContent     = pct.toFixed(1)+'%';
    document.getElementById('ov-bar').style.width     = pct+'%';
    document.getElementById('ov-used').textContent    =
      'Used: '+(s.total_size_mb||0).toFixed(0)+' MB';
    document.getElementById('ov-cap').textContent     =
      'Capacity: '+(s.total_cap_gb||0)+' GB';
    const cw = s.current_write_db;
    document.getElementById('ov-writer').innerHTML = cw
      ? `<span style="color:#34d399;font-weight:700">
           <i class="fas fa-circle" style="font-size:.55rem"></i> DB #${{cw.id}}: ${{cw.name}}
         </span>
         <span style="color:rgba(255,255,255,.4);font-size:.8rem;margin-left:.5rem">
           ${{cw.size_mb}} MB used
         </span>`
      : '<span style="color:#f87171">No active write DB — add one from DB Manager</span>';
  }} catch(e) {{ toast('Stats error: '+e.message,'e'); }}
}}

// ─── Workers ─────────────────────────────────────────────────────────────────
async function loadWorkers() {{
  const c = document.getElementById('workers-list');
  if(!c) return;
  c.innerHTML = '<div style="text-align:center;padding:2rem"><span class="spin"></span></div>';
  try {{
    const r = await API.get('/api/worker-db/list');
    if (!r.workers.length) {{
      c.innerHTML = `<div style="text-align:center;padding:3rem;color:rgba(255,255,255,.3)">
        <i class="fas fa-database" style="font-size:2.5rem;opacity:.2;display:block;margin-bottom:.75rem"></i>
        No worker databases yet. Add your first Render PostgreSQL URL above.
      </div>`;
      return;
    }}
    c.innerHTML = r.workers.map(w => `
      <div class="worker-row">
        <div style="
          width:38px;height:38px;border-radius:10px;flex-shrink:0;
          display:flex;align-items:center;justify-content:center;font-weight:800;font-size:.85rem;
          background:${{w.is_current_write?'rgba(245,158,11,.2)':'rgba(108,99,255,.15)'}};
          color:${{w.is_current_write?'#f59e0b':'var(--primary)'}};
        ">#${{w.id}}</div>
        <div style="flex:1;min-width:0">
          <div style="display:flex;align-items:center;gap:.5rem;flex-wrap:wrap">
            <span style="font-weight:700;color:#fff">${{w.name}}</span>
            ${{w.is_current_write?'<span style="font-size:.65rem;padding:1px 7px;border-radius:10px;background:rgba(245,158,11,.15);color:#f59e0b">✏️ WRITING</span>':''}}
            <span class="badge-${{w.ping_status==='online'?'online':'offline'}}" style="font-size:.72rem">
              ● ${{w.ping_status}}
            </span>
          </div>
          <div class="progress" style="margin:.35rem 0;max-width:280px">
            <div class="progress-fill" style="width:${{w.usage_percent}}%"></div>
          </div>
          <div style="font-size:.72rem;color:rgba(255,255,255,.4)">
            ${{w.size_used_mb}} MB / ${{w.max_size_mb}} MB (${{w.usage_percent}}%) •
            ${{w.record_count.toLocaleString()}} records
            ${{w.notes?'• '+w.notes:''}}
          </div>
        </div>
        <div style="display:flex;gap:.4rem;flex-shrink:0">
          ${{w.usage_percent>=95?'<span style="color:#f87171;font-size:.72rem">⚠️Full</span>':''}}
          {'<button onclick="removeWorker('+'"'+'+w.id+'+'"'+')" class="btn btn-danger btn-sm" style="padding:.3rem .7rem"><i class="fas fa-trash"></i></button>' if is_owner else ''}
        </div>
      </div>
    `).join('');
  }} catch(e) {{
    c.innerHTML = `<div style="color:#f87171;text-align:center;padding:2rem">${{e.message}}</div>`;
  }}
}}

async function addWorkerDB() {{
  const btn = document.getElementById('add-db-btn');
  const url  = document.getElementById('db-url').value.trim();
  const name = document.getElementById('db-name').value.trim();
  const notes= document.getElementById('db-notes').value.trim();
  if (!url||!name) {{ toast('Name and URL required','i'); return; }}
  setLoading(btn, true);
  try {{
    const r = await API.post('/api/worker-db/add',
      {{connection_url:url, name, notes}});
    toast(r.message);
    document.getElementById('db-url').value='';
    document.getElementById('db-name').value='';
    document.getElementById('db-notes').value='';
    loadWorkers();
  }} catch(e) {{ toast(e.message,'e'); }}
  finally {{ setLoading(btn,false); }}
}}

function toggleDbUrl() {{
  const i = document.getElementById('db-url');
  const e = document.getElementById('db-eye');
  i.type  = i.type==='password'?'text':'password';
  e.className = i.type==='password'?'fas fa-eye':'fas fa-eye-slash';
}}

async function testDBConn() {{
  const url  = document.getElementById('db-url').value.trim();
  const name = document.getElementById('db-name').value.trim()||'Test-'+Date.now();
  if (!url) {{ toast('Enter URL to test','i'); return; }}
  try {{
    await API.post('/api/worker-db/add',{{connection_url:url,name}});
    toast('Connection valid ✅');
  }} catch(e) {{
    if (e.message.includes('already exists')) toast('Connection valid (already in pool) ✅','i');
    else toast('Connection failed: '+e.message,'e');
  }}
}}

async function removeWorker(id) {{
  if (!confirm('Deactivate this worker DB? Data remains but new writes stop.')) return;
  try {{
    await API.delete('/api/worker-db/'+id);
    toast('Worker DB deactivated');
    loadWorkers();
  }} catch(e) {{ toast(e.message,'e'); }}
}}

async function pingAll() {{
  toast('Pinging all worker databases...','i');
  try {{
    const r = await API.post('/api/worker-db/ping');
    toast(`Ping: ${{r.results.success}} online, ${{r.results.failed}} offline`,
          r.results.failed>0?'e':'s');
    loadWorkers();
  }} catch(e) {{ toast(e.message,'e'); }}
}}

// ─── Data Explorer ─────────────────────────────────────────────────────────
async function writeRec() {{
  const key  = document.getElementById('w-key').value.trim();
  const type = document.getElementById('w-type').value;
  const raw  = document.getElementById('w-data').value.trim();
  if (!key) {{ toast('Shard key required','i'); return; }}
  let data;
  try {{ data = JSON.parse(raw||'{{}}'); }} catch {{ toast('Invalid JSON','e'); return; }}
  try {{
    const r = await API.post('/api/data/write',
      {{shard_key:key,record_type:type,data}});
    toast(r.message);
  }} catch(e) {{ toast(e.message,'e'); }}
}}

async function readRec() {{
  const key = document.getElementById('w-key').value.trim();
  if (!key) {{ toast('Enter shard key','i'); return; }}
  try {{
    const r = await API.get('/api/data/read/'+encodeURIComponent(key));
    document.getElementById('w-data').value =
      JSON.stringify(r.record.data, null, 2);
    toast('Found in: '+r.record.worker_db,'i');
  }} catch(e) {{ toast(e.message,'e'); }}
}}

async function searchRecs() {{
  const type = document.getElementById('s-type').value;
  const c    = document.getElementById('search-res');
  c.innerHTML = '<span class="spin"></span>';
  try {{
    const url = '/api/data/search'+(type?'?record_type='+type:'');
    const r   = await API.get(url);
    if (!r.records.length) {{
      c.innerHTML = '<div style="text-align:center;color:rgba(255,255,255,.3);padding:2rem">No records found.</div>';
      return;
    }}
    c.innerHTML = r.records.map(rec=>`
      <div style="display:flex;align-items:center;gap:.75rem;padding:.65rem;
        border-radius:10px;border:1px solid rgba(255,255,255,.05);
        background:rgba(255,255,255,.02);margin-bottom:.4rem">
        <div style="flex:1;min-width:0">
          <div style="font-family:monospace;font-size:.82rem;color:#fff;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
            ${{rec.shard_key}}
          </div>
          <div style="font-size:.72rem;color:rgba(255,255,255,.4)">
            ${{rec.record_type}} • ${{rec.worker_db}} •
            ${{new Date(rec.created_at).toLocaleDateString()}}
          </div>
        </div>
        <button onclick="document.getElementById('w-key').value='${{rec.shard_key}}';readRec()"
          class="btn btn-sm" style="flex-shrink:0;padding:.3rem .7rem">
          <i class="fas fa-eye"></i>
        </button>
      </div>
    `).join('');
  }} catch(e) {{ c.innerHTML = '<div style="color:#f87171">'+e.message+'</div>'; }}
}}

// ─── Users ──────────────────────────────────────────────────────────────────
async function createUser() {{
  const uname = document.getElementById('nu-name')?.value.trim();
  const pass  = document.getElementById('nu-pass')?.value;
  const email = document.getElementById('nu-email')?.value.trim();
  const role  = document.getElementById('nu-role')?.value;
  if (!uname||!pass) {{ toast('Username & password required','i'); return; }}
  try {{
    const r = await API.post('/api/users/create',
      {{username:uname,password:pass,email,role}});
    toast(r.message);
    if(document.getElementById('nu-name')) document.getElementById('nu-name').value='';
    if(document.getElementById('nu-pass')) document.getElementById('nu-pass').value='';
    loadUsers();
  }} catch(e) {{ toast(e.message,'e'); }}
}}

async function loadUsers() {{
  const c = document.getElementById('users-list');
  if (!c) return;
  c.innerHTML = '<span class="spin"></span>';
  try {{
    const r = await API.get('/api/users/list');
    if (!r.users.length) {{
      c.innerHTML = '<div style="text-align:center;color:rgba(255,255,255,.3);padding:2rem">No users found.</div>';
      return;
    }}
    c.innerHTML = r.users.map(u=>`
      <div class="user-row">
        <div style="
          width:38px;height:38px;border-radius:50%;flex-shrink:0;
          display:flex;align-items:center;justify-content:center;font-weight:800;
          background:linear-gradient(135deg,var(--primary),var(--secondary))
        ">${{u.username[0].toUpperCase()}}</div>
        <div style="flex:1;min-width:0">
          <div style="display:flex;align-items:center;gap:.5rem;flex-wrap:wrap">
            <span style="font-weight:700">${{u.username}}</span>
            <span class="badge badge-${{u.role}}">${{u.role}}</span>
            ${{!u.is_active?'<span style="color:#f87171;font-size:.72rem">INACTIVE</span>':''}}
          </div>
          <div style="font-size:.72rem;color:rgba(255,255,255,.4)">
            ${{u.email||'No email'}} •
            Balance: ₹${{(u.balance||0).toFixed(2)}} •
            Last: ${{u.last_login?new Date(u.last_login).toLocaleDateString():'Never'}}
          </div>
        </div>
        ${{u.username!=='RUHIVIGQNR@QNR'?`
          <div style="display:flex;gap:.4rem">
            <button onclick="editBal('${{u.username}}',${{u.balance||0}})"
              class="btn btn-success btn-sm" title="Edit Balance">
              <i class="fas fa-coins"></i>
            </button>
            <button onclick="toggleUsr('${{u.username}}')"
              class="btn ${{u.is_active?'btn-warn':'btn-success'}} btn-sm" title="Toggle">
              <i class="fas fa-${{u.is_active?'pause':'play'}}"></i>
            </button>
            {'<button onclick="delUser(\'"+u.username+"\')" class="btn btn-danger btn-sm"><i class="fas fa-trash"></i></button>' if is_owner else ''}
          </div>
        `:''}}
      </div>
    `).join('');
  }} catch(e) {{
    c.innerHTML = '<div style="color:#f87171">'+e.message+'</div>';
  }}
}}

async function editBal(username, current) {{
  const nb = prompt(`New balance for ${{username}}:`, current);
  if (nb===null) return;
  const val = parseFloat(nb);
  if (isNaN(val)) {{ toast('Invalid number','e'); return; }}
  try {{
    await API.put('/api/users/balance',{{username,new_balance:val}});
    toast('Balance updated');
    loadUsers();
  }} catch(e) {{ toast(e.message,'e'); }}
}}

async function toggleUsr(username) {{
  try {{
    const r = await API.put('/api/users/'+username+'/toggle');
    toast(r.is_active?'User activated':'User deactivated');
    loadUsers();
  }} catch(e) {{ toast(e.message,'e'); }}
}}

async function delUser(username) {{
  if (!confirm('Delete "'+username+'" permanently?')) return;
  try {{
    await API.delete('/api/users/'+username);
    toast('User deleted');
    loadUsers();
  }} catch(e) {{ toast(e.message,'e'); }}
}}

// ─── Logs ─────────────────────────────────────────────────────────────────
async function loadLogs() {{
  const c = document.getElementById('logs-list');
  if (!c) return;
  c.innerHTML = '<span class="spin"></span>';
  try {{
    const r = await API.get('/api/system/logs?limit=50');
    const colors = {{
      LOGIN:'#60a5fa',ADD_WORKER_DB:'#34d399',REMOVE_WORKER_DB:'#f87171',
      CREATE_USER:'#a78bfa',DELETE_USER:'#f87171',UI_UPDATE:'#f472b6',
      MAINTENANCE_TOGGLE:'#fbbf24',AUTO_DB_SWITCH:'#fb923c',
    }};
    c.innerHTML = r.logs.map(l=>`
      <div class="log-row">
        <span>${{l.level==='ERROR'?'❌':l.level==='WARNING'?'⚠️':'ℹ️'}}</span>
        <div style="flex:1;min-width:0">
          <div style="display:flex;gap:.5rem;flex-wrap:wrap;align-items:center">
            <span style="font-weight:700;font-size:.82rem">${{l.user||'SYSTEM'}}</span>
            <span style="font-size:.72rem;font-family:monospace;
              color:${{colors[l.action]||'rgba(255,255,255,.5)'}}">
              ${{l.action}}
            </span>
          </div>
          ${{l.details?`<div style="font-size:.72rem;color:rgba(255,255,255,.4);margin-top:2px;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${{l.details}}</div>`:''}}}
          <div style="font-size:.68rem;color:rgba(255,255,255,.25)">
            ${{new Date(l.timestamp).toLocaleString()}}
          </div>
        </div>
      </div>
    `).join('');
  }} catch(e) {{ c.innerHTML = '<div style="color:#f87171">'+e.message+'</div>'; }}
}}

// ─── UI Editor ──────────────────────────────────────────────────────────────
const UI_COLORS = [
  ['primary_color',   'Primary Color',    '#6C63FF'],
  ['secondary_color', 'Secondary Color',  '#FF6584'],
  ['background_color','Background Color', '#0F0F1A'],
  ['card_color',      'Card Color',       '#1A1A2E'],
  ['text_color',      'Text Color',       '#FFFFFF'],
];
const UI_TEXTS = [
  ['logo_text',    'Logo Text'],
  ['hero_title',   'Hero Title'],
  ['hero_subtitle','Hero Subtitle'],
];

async function initUIEditor() {{
  try {{
    const r = await API.get('/api/ui/config');
    const cfg = r.config;

    // Colors
    const cr = document.getElementById('color-rows');
    if (cr) cr.innerHTML = UI_COLORS.map(([k,l,def])=>`
      <div class="color-row">
        <input type="color" id="col-${{k}}" value="${{cfg[k]||def}}"
          style="width:40px;height:40px;border:none;border-radius:8px;cursor:pointer;background:transparent"
          onchange="previewColor('${{k}}',this.value)">
        <div style="flex:1">
          <div style="font-size:.82rem;font-weight:500">${{l}}</div>
          <div style="font-size:.7rem;color:rgba(255,255,255,.35)" id="cv-${{k}}">${{cfg[k]||def}}</div>
        </div>
        <button class="btn btn-sm"
          onclick="saveUIKey('${{k}}',document.getElementById('col-${{k}}').value)">
          Save
        </button>
      </div>
    `).join('');

    // Texts
    const tf = document.getElementById('text-fields');
    if (tf) tf.innerHTML = UI_TEXTS.map(([k,l])=>`
      <div class="form-group">
        <label class="label">${{l}}</label>
        <div style="display:flex;gap:.5rem">
          <textarea id="txt-${{k}}" class="inp" rows="2">${{cfg[k]||''}}</textarea>
          <button class="btn btn-sm"
            onclick="saveUIKey('${{k}}',document.getElementById('txt-${{k}}').value)"
            style="flex-shrink:0">
            <i class="fas fa-save"></i>
          </button>
        </div>
      </div>
    `).join('');

    // CSS / HTML
    const cc = document.getElementById('cust-css');
    if (cc) cc.value = cfg.custom_css||'';
    const ch = document.getElementById('cust-html');
    if (ch) ch.value = cfg.custom_html_header||'';
  }} catch(e) {{ console.log('UI init error:',e); }}
}}

function previewColor(key, val) {{
  const map = {{
    primary_color:'--primary', secondary_color:'--secondary',
    background_color:'--bg', card_color:'--card', text_color:'--text'
  }};
  if (map[key]) document.documentElement.style.setProperty(map[key], val);
  const cv = document.getElementById('cv-'+key);
  if (cv) cv.textContent = val;
}}

async function saveUIKey(key, value) {{
  try {{
    await API.put('/api/ui/update',{{design_key:key,design_value:value}});
    toast(`'${{key}}' saved ✅`);
  }} catch(e) {{ toast(e.message,'e'); }}
}}

async function saveAllColors() {{
  const updates = {{}};
  UI_COLORS.forEach(([k])=>{{
    const el = document.getElementById('col-'+k);
    if (el) updates[k] = el.value;
  }});
  try {{
    await API.put('/api/ui/bulk-update',{{updates}});
    toast('All colors saved ✅');
  }} catch(e) {{ toast(e.message,'e'); }}
}}

// ─── Media ──────────────────────────────────────────────────────────────────
async function loadMediaInputs() {{
  try {{
    const r = await API.get('/api/ui/config');
    const v = document.getElementById('m-video');
    const m = document.getElementById('m-music');
    const a = document.getElementById('m-auto');
    if (v) v.value = r.config.bg_video_url||'';
    if (m) m.value = r.config.bg_music_url||'';
    if (a) a.checked = r.config.bg_music_autoplay==='true';
  }} catch {{}}
}}

async function saveMedia() {{
  const v = document.getElementById('m-video')?.value.trim();
  const m = document.getElementById('m-music')?.value.trim();
  const a = document.getElementById('m-auto')?.checked;
  try {{
    await API.post('/api/system/media',{{
      bg_video_url:v||null, bg_music_url:m||null, bg_music_autoplay:a
    }});
    toast('Media settings saved! Reload to see changes.');
  }} catch(e) {{ toast(e.message,'e'); }}
}}

// ─── System ──────────────────────────────────────────────────────────────────
async function loadSysInputs() {{
  try {{
    const r = await API.get('/api/system/stats');
    const cfg = r.stats;
  }} catch {{}}
}}

async function toggleMaint(enabled) {{
  if (!confirm((enabled?'ENABLE':'DISABLE')+' maintenance mode?')) return;
  try {{
    const r = await API.post('/api/system/maintenance',{{enabled}});
    toast(r.message);
    setTimeout(()=>location.reload(), 800);
  }} catch(e) {{ toast(e.message,'e'); }}
}}

async function manualPing() {{
  toast('Pinging all DBs...','i');
  try {{
    const r = await API.post('/api/worker-db/ping');
    toast(`Ping: ${{r.results.success}} online, ${{r.results.failed}} offline`);
  }} catch(e) {{ toast(e.message,'e'); }}
}}

async function saveCfg(key, value) {{
  try {{
    await API.put('/api/system/config',{{config_key:key,config_value:value}});
    toast('Config saved ✅');
  }} catch(e) {{ toast(e.message,'e'); }}
}}

async function loadGodView() {{
  const el = document.getElementById('god-view');
  if (!el) return;
  try {{
    const r = await API.get('/api/system/stats');
    const s = r.stats;
    el.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem">
        ${{[
          ['Total Workers',s.total_workers],
          ['Active Workers',s.active_workers],
          ['Total Records',(s.total_records||0).toLocaleString()],
          ['Total Users',s.user_count],
          ['Admins',s.admin_count],
          ['Storage Used',s.total_size_gb+'GB'],
          ['Capacity',s.total_cap_gb+' GB'],
          ['Usage',s.usage_percent+'%'],
        ].map(([l,v])=>`
          <div style="padding:.5rem;background:rgba(255,255,255,.04);border-radius:8px">
            <div style="font-size:.65rem;color:rgba(255,255,255,.4);text-transform:uppercase">${{l}}</div>
            <div style="font-weight:700;color:#fff">${{v}}</div>
          </div>
        `).join('')}}
      </div>`;
  }} catch(e) {{ el.innerHTML = '<span style="color:#f87171">'+e.message+'</span>'; }}
}}

// ─── Profile ─────────────────────────────────────────────────────────────────
async function loadProfile() {{
  const c = document.getElementById('profile-data');
  if (!c) return;
  try {{
    const u = await API.get('/api/profile/me');
    c.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.75rem">
        ${{[
          ['Username',u.username],
          ['Email',u.email||'Not set'],
          ['Role',u.role.toUpperCase()],
          ['Balance','₹'+(u.balance||0).toFixed(2)],
          ['Member Since',new Date(u.created_at).toLocaleDateString()],
          ['Last Login',u.last_login?new Date(u.last_login).toLocaleString():'First time!'],
        ].map(([l,v])=>`
          <div style="padding:.85rem;background:rgba(255,255,255,.04);border-radius:10px">
            <div style="font-size:.68rem;color:rgba(255,255,255,.35);text-transform:uppercase;
              letter-spacing:.05em;margin-bottom:.2rem">${{l}}</div>
            <div style="font-weight:600;color:#fff">${{v}}</div>
          </div>
        `).join('')}}
      </div>
      ${{u.contact_info?`<div style="margin-top:.75rem;padding:.85rem;background:rgba(255,255,255,.04);border-radius:10px">
        <div style="font-size:.68rem;color:rgba(255,255,255,.35);text-transform:uppercase;margin-bottom:.2rem">Contact</div>
        <div style="color:#fff">${{u.contact_info}}</div>
      </div>`:''}}`;
  }} catch(e) {{ c.innerHTML = '<span style="color:#f87171">'+e.message+'</span>'; }}
}}

// ─── Auto-refresh ─────────────────────────────────────────────────────────
setInterval(()=>{{
  if (document.getElementById('sec-overview')?.classList.contains('active')) {{
    loadOverview();
  }}
}}, 30000);
</script>
</body></html>"""

def render_home_page(ui: dict, user: dict = None, stats: dict = None) -> str:
    logged_in = user is not None
    role = user.get("role","") if user else ""
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{ui.get('logo_text','RUHI-VIG QNR')} - Cloud Storage</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
{build_base_styles(ui)}
</head><body>
<div id="toast-wrap"></div>
{BASE_JS}

<!-- Background Video -->
{f'<div id="bg-vid-wrap"><video id="bg-vid" autoplay muted loop playsinline><source src="{db_router.get_config("bg_video_url","")}" type="video/mp4"></video></div><div class="vid-overlay"></div>' if db_router.get_config("bg_video_url","") else ""}

<!-- Background Music -->
{f'<audio id="bg-audio" loop {"autoplay" if db_router.get_config("bg_music_autoplay","false")=="true" else ""}><source src="{db_router.get_config("bg_music_url","")}" type="audio/mpeg"></audio><div id="music-btn" onclick="toggleMusic()"><i class="fas fa-music" id="micon" style="color:var(--primary)"></i><span id="mstat">Music</span></div>' if db_router.get_config("bg_music_url","") else ""}

<!-- Navbar -->
<nav style="
  position:fixed;top:0;left:0;right:0;z-index:50;
  display:flex;align-items:center;justify-content:space-between;
  padding:.9rem 2rem;
  background:rgba(15,15,26,.82);backdrop-filter:blur(20px);
  border-bottom:1px solid rgba(108,99,255,.1);
">
  <div style="font-family:Orbitron,sans-serif;font-weight:900;font-size:1.2rem" class="neon">
    {ui.get('logo_text','RUHI-VIG QNR')}
  </div>
  <div style="display:flex;align-items:center;gap:1.5rem;font-size:.85rem;color:rgba(255,255,255,.6)">
    <a href="#features" style="transition:color .2s" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='rgba(255,255,255,.6)'">Features</a>
    <a href="#stats" style="transition:color .2s" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='rgba(255,255,255,.6)'">Stats</a>
    {'<a href="/dashboard" class="btn btn-sm"><i class="fas fa-th-large"></i> Dashboard</a><a href="/logout" style="color:rgba(255,255,255,.4);font-size:.8rem" onmouseover="this.style.color=\'#f87171\'" onmouseout="this.style.color=\'rgba(255,255,255,.4)\'">Logout</a>' if logged_in else '<a href="/login" class="btn btn-sm"><i class="fas fa-sign-in-alt"></i> Sign In</a>'}
  </div>
</nav>

<!-- Hero -->
<section style="min-height:100vh;display:flex;align-items:center;justify-content:center;padding:6rem 1.5rem 3rem;text-align:center">
  <div style="max-width:800px">
    <div style="
      display:inline-flex;align-items:center;gap:.6rem;
      padding:.4rem 1rem;border-radius:50px;margin-bottom:2rem;font-size:.82rem;
      background:rgba(108,99,255,.12);border:1px solid rgba(108,99,255,.3)
    ">
      <span style="display:flex;align-items:center">
        <span style="
          width:8px;height:8px;border-radius:50%;background:var(--primary);
          box-shadow:0 0 8px var(--primary);display:inline-block
        "></span>
      </span>
      <span style="color:var(--primary);font-weight:600">Live System</span>
      <span style="color:rgba(255,255,255,.4)">• v2.0.0</span>
    </div>

    <h1 style="font-family:Orbitron,sans-serif;font-size:clamp(2.2rem,6vw,4.5rem);
      font-weight:900;line-height:1.1;margin-bottom:1.25rem">
      <span class="neon">{ui.get('hero_title','Virtual Database')}</span><br>
      <span style="color:#fff">Cloud System</span>
    </h1>

    <p style="color:rgba(255,255,255,.55);font-size:1.05rem;max-width:560px;
      margin:0 auto 2.5rem;line-height:1.7">
      {ui.get('hero_subtitle','Aggregating 1000+ PostgreSQL databases into one unified 1TB+ storage pool.')}
    </p>

    <div style="display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;margin-bottom:3.5rem">
      {'<a href="/dashboard" class="btn" style="padding:.9rem 2rem;font-size:1rem"><i class="fas fa-th-large"></i> Open Dashboard</a>' if logged_in else '<a href="/login" class="btn" style="padding:.9rem 2rem;font-size:1rem"><i class="fas fa-rocket"></i> Get Started</a>'}
      <a href="#features" class="btn-outline" style="padding:.9rem 2rem;font-size:1rem">
        <i class="fas fa-info-circle"></i> Learn More
      </a>
    </div>

    <!-- Live Stats Row -->
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem" id="hero-stats">
      {''.join([f'<div class="glass" style="padding:1rem;text-align:center"><div style="font-size:1.8rem;font-weight:900;color:var(--primary)" id="hs-{k}">—</div><div style="font-size:.7rem;color:rgba(255,255,255,.4);margin-top:.2rem">{l}</div></div>' for k,l in [("dbs","Worker DBs"),("size","Storage"),("recs","Records"),("users","Users")]])}
    </div>
  </div>
</section>

<!-- Features -->
<section id="features" style="padding:5rem 1.5rem">
  <div style="max-width:1100px;margin:0 auto">
    <h2 style="font-family:Orbitron,sans-serif;font-size:2.2rem;font-weight:900;
      text-align:center;margin-bottom:.5rem">
      <span class="neon">System</span> Features
    </h2>
    <p style="text-align:center;color:rgba(255,255,255,.4);margin-bottom:3rem">
      Built for scale, designed for simplicity
    </p>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1.25rem">
      {''.join([f'<div class="glass" style="padding:1.5rem"><div style="width:44px;height:44px;border-radius:12px;background:rgba(108,99,255,.15);display:flex;align-items:center;justify-content:center;margin-bottom:1rem"><i class="fas {ic}" style="color:{col};font-size:1.1rem"></i></div><h3 style="font-weight:700;margin-bottom:.5rem">{title}</h3><p style="color:rgba(255,255,255,.5);font-size:.83rem;line-height:1.6">{desc}</p></div>' for ic,col,title,desc in [("fa-database","var(--primary)","Distributed Sharding","Automatically distributes data across 1000+ PostgreSQL databases with intelligent shard-key routing."),("fa-robot","var(--secondary)","Auto-Switching","Seamlessly switches to the next worker DB when the current one reaches 950MB — zero downtime."),("fa-shield-alt","var(--primary)","RBAC Security","Owner, Admin, and User hierarchy with JWT-based authentication and granular permissions."),("fa-paint-brush","var(--secondary)","Live UI Editor","Edit HTML, CSS, colors and media from the dashboard. Changes persist in DB and apply instantly."),("fa-heartbeat","var(--primary)","Anti-Sleep Engine","Pings all worker databases every 10 minutes to keep Render free-tier instances awake."),("fa-wrench","var(--secondary)","Maintenance Mode","One-click toggle for safe monthly database resets. Only Owner retains access."),]])}
    </div>
  </div>
</section>

<!-- Stats Section -->
<section id="stats" style="padding:5rem 1.5rem">
  <div style="max-width:700px;margin:0 auto">
    <h2 style="font-family:Orbitron,sans-serif;font-size:2.2rem;font-weight:900;
      text-align:center;margin-bottom:2.5rem">
      <span class="neon">Real-Time</span> Metrics
    </h2>
    <div class="glass" style="padding:2rem">
      <div style="display:flex;justify-content:space-between;margin-bottom:.5rem;font-size:.83rem">
        <span style="color:rgba(255,255,255,.5)">Global Storage Usage</span>
        <span id="s-pct" style="color:var(--primary);font-weight:800">—%</span>
      </div>
      <div class="progress" style="margin-bottom:2rem">
        <div class="progress-fill" id="s-bar" style="width:0%"></div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem" id="stat-grid">
        {''.join(['<div style="text-align:center;padding:.75rem;background:rgba(255,255,255,.04);border-radius:10px"><div style="font-size:.68rem;color:rgba(255,255,255,.35);text-transform:uppercase;margin-bottom:.25rem">'+l+'</div><div style="font-weight:800;color:#fff" id="sg-'+k+'">—</div></div>' for k,l in [("active","Active DBs"),("cap","Capacity"),("admins","Admins")]])}
      </div>
    </div>
  </div>
</section>

<!-- Footer -->
<footer style="padding:2.5rem 1.5rem;text-align:center;color:rgba(255,255,255,.25);font-size:.8rem;padding-bottom:5rem">
  <div style="font-family:Orbitron,sans-serif;font-size:1.1rem;margin-bottom:.4rem" class="neon">
    {ui.get('logo_text','RUHI-VIG QNR')}
  </div>
  <div>Distributed Database Cloud System v2.0</div>
  <div style="margin-top:.3rem">© {datetime.utcnow().year} All Rights Reserved</div>
</footer>

<script>
async function loadStats() {{
  try {{
    const r = await API.get('/api/system/stats');
    const s = r.stats;
    const hs = id => document.getElementById(id);
    if(hs('hs-dbs'))  hs('hs-dbs').textContent  = s.active_workers||0;
    if(hs('hs-size')) hs('hs-size').textContent  = (s.total_size_gb||0).toFixed(2)+' GB';
    if(hs('hs-recs')) hs('hs-recs').textContent  = (s.total_records||0).toLocaleString();
    if(hs('hs-users'))hs('hs-users').textContent = s.user_count||0;
    const pct = s.usage_percent||0;
    const sp  = hs('s-pct'); if(sp) sp.textContent = pct.toFixed(1)+'%';
    const sb  = hs('s-bar'); if(sb) sb.style.width = pct+'%';
    const sga = hs('sg-active'); if(sga) sga.textContent = s.active_workers||0;
    const sgc = hs('sg-cap');    if(sgc) sgc.textContent = (s.total_cap_gb||0)+' GB';
    const sgd = hs('sg-admins');  if(sgd) sgd.textContent = s.admin_count||0;
  }} catch {{
    ['hs-dbs','hs-size','hs-recs','hs-users'].forEach(id=>{{
      const el=document.getElementById(id);
      if(el) el.textContent='🔒';
    }});
  }}
}}
loadStats();
setInterval(loadStats, 60000);
</script>
</body></html>"""

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9: APP LIFECYCLE & ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 RUHI-VIG QNR Starting...")
    db_router.initialize_master()
    start_scheduler()
    logger.info("✅ System Ready!")
    yield
    stop_scheduler()
    pool_manager.dispose_all()
    logger.info("System shutdown complete.")

app = FastAPI(
    title="RUHI-VIG QNR",
    version="2.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Maintenance Middleware ────────────────────────────────────────────────────
@app.middleware("http")
async def maintenance_check(request: Request, call_next):
    skip = ["/api/auth/login", "/login", "/api/ping", "/logout"]
    if any(request.url.path.startswith(p) for p in skip):
        return await call_next(request)
    if db_router.is_maintenance():
        token = request.cookies.get("access_token")
        if token:
            u = decode_token(token)
            if u and u.get("role") == "owner":
                return await call_next(request)
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=503,
                content={"error": "Maintenance mode active", "maintenance": True}
            )
        ui = db_router.get_ui_config()
        return HTMLResponse(render_maintenance_page(ui), status_code=503)
    return await call_next(request)

# ── Page Routes ───────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    ui   = db_router.get_ui_config()
    user = get_user_from_request(request)
    return HTMLResponse(render_home_page(ui, user))

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    token = request.cookies.get("access_token")
    if token and decode_token(token):
        return RedirectResponse("/dashboard")
    ui = db_router.get_ui_config()
    return HTMLResponse(render_login_page(ui))

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    token = request.cookies.get("access_token")
    user  = decode_token(token) if token else None
    if not user:
        return RedirectResponse("/login")
    ui = db_router.get_ui_config()
    return HTMLResponse(render_dashboard(ui, user))

@app.get("/logout")
async def logout():
    response = RedirectResponse("/login")
    response.delete_cookie("access_token")
    return response

# ── Auth API ──────────────────────────────────────────────────────────────────
@app.post("/api/auth/login")
async def api_login(request: Request, data: LoginRequest):
    user = authenticate_user(data.username, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token({
        "sub":  user.username,
        "role": user.role,
        "uid":  user.id
    })
    db_router.log_activity(user.username, "LOGIN",
                           f"Login successful - role: {user.role}",
                           ip=request.client.host if request.client else None)
    resp = JSONResponse({
        "success":  True,
        "token":    token,
        "username": user.username,
        "role":     user.role,
    })
    resp.set_cookie("access_token", token, max_age=86400,
                    httponly=True, samesite="lax")
    return resp

# ── Worker DB API ─────────────────────────────────────────────────────────────
@app.post("/api/worker-db/add")
async def add_worker(data: AddWorkerRequest,
                     u: dict = Depends(require_admin)):
    ok, msg, worker = db_router.validate_and_add_worker(
        data.connection_url, data.name, u["sub"], data.notes
    )
    db_router.log_activity(u["sub"], "ADD_WORKER_DB",
                           f"Name:{data.name} OK:{ok} Msg:{msg}")
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg,
            "worker_id": worker.id if worker else None}

@app.get("/api/worker-db/list")
async def list_workers(u: dict = Depends(require_admin)):
    session = pool_manager.get_master_session()
    try:
        workers = session.query(WorkerDatabase).order_by(
            WorkerDatabase.id
        ).all()
        return {"workers": [{
            "id":               w.id,
            "name":             w.name,
            "is_active":        w.is_active,
            "is_current_write": w.is_current_write,
            "size_used_mb":     round(w.size_used_mb, 2),
            "max_size_mb":      w.max_size_mb,
            "usage_percent":    round(
                (w.size_used_mb / w.max_size_mb * 100)
                if w.max_size_mb > 0 else 0, 1
            ),
            "record_count":     w.record_count,
            "ping_status":      w.ping_status,
            "last_pinged":      str(w.last_pinged) if w.last_pinged else None,
            "added_by":         w.added_by,
            "notes":            w.notes,
            "created_at":       str(w.created_at),
        } for w in workers]}
    finally:
        session.close()

@app.delete("/api/worker-db/{worker_id}")
async def remove_worker(worker_id: int, u: dict = Depends(require_owner)):
    session = pool_manager.get_master_session()
    try:
        w = session.query(WorkerDatabase).get(worker_id)
        if not w:
            raise HTTPException(status_code=404, detail="Worker not found")
        w.is_active = False
        w.is_current_write = False
        session.commit()
        pool_manager.remove_pool(worker_id)
        db_router.log_activity(u["sub"], "REMOVE_WORKER_DB",
                               f"Deactivated DB #{worker_id}: {w.name}")
        return {"success": True, "message": f"Worker '{w.name}' deactivated"}
    finally:
        session.close()

@app.post("/api/worker-db/ping")
async def manual_ping(u: dict = Depends(require_admin)):
    results = db_router.ping_all_workers()
    db_router.log_activity(u["sub"], "MANUAL_PING",
                           f"Success:{results['success']} Failed:{results['failed']}")
    return {"success": True, "results": results}

# ── Data API ──────────────────────────────────────────────────────────────────
@app.post("/api/data/write")
async def write_data(data: WriteRecordRequest,
                     u: dict = Depends(require_auth)):
    ok, msg = db_router.write_record(
        data.shard_key, data.record_type, data.data, u["sub"]
    )
    if not ok:
        raise HTTPException(status_code=500, detail=msg)
    return {"success": True, "message": msg, "shard_key": data.shard_key}

@app.get("/api/data/read/{shard_key}")
async def read_data(shard_key: str, u: dict = Depends(require_auth)):
    ok, record, msg = db_router.read_record(shard_key)
    if not ok:
        raise HTTPException(status_code=404, detail=msg)
    return {"success": True, "record": record}

@app.get("/api/data/search")
async def search_data(
    record_type: Optional[str] = None,
    page: int = 1, limit: int = 50,
    u: dict = Depends(require_auth)
):
    owner = None if u.get("role") in ("owner","admin") else u["sub"]
    results = db_router.search_records(record_type, owner, page, limit)
    return {"success": True, "records": results, "count": len(results)}

@app.delete("/api/data/{shard_key}")
async def delete_data(shard_key: str, u: dict = Depends(require_admin)):
    ok, msg = db_router.delete_record(shard_key, u["sub"])
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

# ── User API ──────────────────────────────────────────────────────────────────
@app.post("/api/users/create")
async def create_user_route(data: CreateUserRequest,
                            u: dict = Depends(require_admin)):
    if data.role == "owner":
        raise HTTPException(status_code=403, detail="Cannot create owner accounts")
    if data.role == "admin" and u.get("role") != "owner":
        raise HTTPException(status_code=403,
                            detail="Only Owner can create Admins")
    ok, msg = create_user_account(
        data.username, data.password, data.role, data.email, u["sub"]
    )
    db_router.log_activity(u["sub"], "CREATE_USER",
                           f"Created '{data.username}' role:{data.role}")
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

@app.get("/api/users/list")
async def list_users_route(u: dict = Depends(require_admin)):
    session = pool_manager.get_master_session()
    try:
        users = session.query(UserAccount).order_by(
            UserAccount.created_at.desc()
        ).all()
        return {"users": [{
            "id":           usr.id,
            "username":     usr.username,
            "email":        usr.email,
            "role":         usr.role,
            "balance":      usr.balance,
            "is_active":    usr.is_active,
            "contact_info": usr.contact_info,
            "created_at":   str(usr.created_at),
            "last_login":   str(usr.last_login) if usr.last_login else None,
            "created_by":   usr.created_by,
        } for usr in users]}
    finally:
        session.close()

@app.put("/api/users/balance")
async def update_balance(data: UpdateBalanceRequest,
                         u: dict = Depends(require_admin)):
    session = pool_manager.get_master_session()
    try:
        usr = session.query(UserAccount).filter_by(
            username=data.username
        ).first()
        if not usr:
            raise HTTPException(status_code=404, detail="User not found")
        old = usr.balance
        usr.balance = data.new_balance
        session.commit()
        db_router.log_activity(u["sub"], "UPDATE_BALANCE",
                               f"{data.username}: {old}→{data.new_balance}")
        return {"success": True, "message": "Balance updated"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.put("/api/users/contact")
async def update_contact(data: UpdateContactRequest,
                         u: dict = Depends(require_admin)):
    session = pool_manager.get_master_session()
    try:
        usr = session.query(UserAccount).filter_by(
            username=data.username
        ).first()
        if not usr:
            raise HTTPException(status_code=404, detail="User not found")
        usr.contact_info = data.contact_info
        session.commit()
        return {"success": True, "message": "Contact updated"}
    finally:
        session.close()

@app.put("/api/users/{username}/toggle")
async def toggle_user(username: str, u: dict = Depends(require_admin)):
    session = pool_manager.get_master_session()
    try:
        usr = session.query(UserAccount).filter_by(username=username).first()
        if not usr:
            raise HTTPException(status_code=404, detail="User not found")
        usr.is_active = not usr.is_active
        session.commit()
        db_router.log_activity(u["sub"], "TOGGLE_USER",
                               f"{username} → {'active' if usr.is_active else 'inactive'}")
        return {"success": True, "is_active": usr.is_active}
    finally:
        session.close()

@app.delete("/api/users/{username}")
async def delete_user_route(username: str, u: dict = Depends(require_owner)):
    if username == "RUHIVIGQNR@QNR":
        raise HTTPException(status_code=403, detail="Cannot delete Owner account")
    session = pool_manager.get_master_session()
    try:
        usr = session.query(UserAccount).filter_by(username=username).first()
        if not usr:
            raise HTTPException(status_code=404, detail="User not found")
        session.delete(usr)
        session.commit()
        db_router.log_activity(u["sub"], "DELETE_USER", f"Deleted: {username}")
        return {"success": True, "message": f"User '{username}' deleted"}
    finally:
        session.close()

# ── UI API ────────────────────────────────────────────────────────────────────
@app.put("/api/ui/update")
async def update_ui(data: UpdateUIRequest, u: dict = Depends(require_admin)):
    db_router.set_ui_config(data.design_key, data.design_value, u["sub"])
    db_router.log_activity(u["sub"], "UI_UPDATE", f"Key: {data.design_key}")
    return {"success": True, "message": f"UI '{data.design_key}' updated"}

@app.put("/api/ui/bulk-update")
async def bulk_update_ui(data: BulkUIRequest, u: dict = Depends(require_admin)):
    for k, v in data.updates.items():
        db_router.set_ui_config(k, v, u["sub"])
    db_router.log_activity(u["sub"], "UI_BULK_UPDATE",
                           f"Updated {len(data.updates)} keys")
    return {"success": True, "message": f"Updated {len(data.updates)} settings"}

@app.get("/api/ui/config")
async def get_ui_config_api():
    return {"config": db_router.get_ui_config()}

# ── System API ────────────────────────────────────────────────────────────────
@app.post("/api/system/maintenance")
async def set_maintenance(data: MaintenanceRequest,
                          u: dict = Depends(require_owner)):
    db_router.toggle_maintenance(data.enabled, u["sub"])
    status_str = "ENABLED" if data.enabled else "DISABLED"
    return {"success": True,
            "message": f"Maintenance {status_str}",
            "maintenance": data.enabled}

@app.put("/api/system/config")
async def update_config(data: UpdateConfigRequest,
                        u: dict = Depends(require_owner)):
    db_router.set_config(data.config_key, data.config_value, u["sub"])
    return {"success": True, "message": "Config updated"}

@app.post("/api/system/media")
async def update_media(data: MediaRequest, u: dict = Depends(require_admin)):
    if data.bg_video_url is not None:
        db_router.set_config("bg_video_url", data.bg_video_url, u["sub"])
    if data.bg_music_url is not None:
        db_router.set_config("bg_music_url", data.bg_music_url, u["sub"])
    if data.bg_music_autoplay is not None:
        db_router.set_config("bg_music_autoplay",
                             str(data.bg_music_autoplay).lower(), u["sub"])
    db_router.log_activity(u["sub"], "MEDIA_UPDATE", "Updated media config")
    return {"success": True, "message": "Media settings saved"}

@app.get("/api/system/stats")
async def get_stats(u: dict = Depends(require_admin)):
    return {"success": True, "stats": db_router.get_stats()}

@app.get("/api/system/logs")
async def get_logs(limit: int = 50, u: dict = Depends(require_admin)):
    session = pool_manager.get_master_session()
    try:
        logs = session.query(ActivityLog).order_by(
            ActivityLog.timestamp.desc()
        ).limit(limit).all()
        return {"logs": [{
            "id":        l.id,
            "user":      l.user,
            "action":    l.action,
            "details":   l.details,
            "timestamp": str(l.timestamp),
            "level":     l.level,
            "ip":        l.ip_address,
        } for l in logs]}
    finally:
        session.close()

@app.get("/api/ping")
async def health_ping():
    return {
        "status":      "online",
        "system":      "RUHI-VIG QNR",
        "version":     "2.0.0",
        "timestamp":   datetime.utcnow().isoformat(),
        "maintenance": db_router.is_maintenance(),
    }

@app.get("/api/profile/me")
async def get_profile(u: dict = Depends(require_auth)):
    session = pool_manager.get_master_session()
    try:
        usr = session.query(UserAccount).filter_by(
            username=u["sub"]
        ).first()
        if not usr:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "username":     usr.username,
            "email":        usr.email,
            "role":         usr.role,
            "balance":      usr.balance,
            "contact_info": usr.contact_info,
            "created_at":   str(usr.created_at),
            "last_login":   str(usr.last_login) if usr.last_login else None,
        }
    finally:
        session.close()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 10: ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False,
        workers=1,
        log_level="info",
    )