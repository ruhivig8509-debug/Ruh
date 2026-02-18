# ============================================================
# RUHI-VIG QNR v3.0 - Distributed Database Cloud System
# Single File: main.py
# ============================================================

import os
import io
import re
import json
import uuid
import time
import base64
import hashlib
import secrets
import logging
import datetime
import threading
from typing import Optional, List, Dict, Any, Union
from contextlib import contextmanager

# ── FastAPI & Web ────────────────────────────────────────────
import httpx
from fastapi import (
    FastAPI, Request, Response, Depends, HTTPException,
    status, Form, UploadFile, File, BackgroundTasks
)
from fastapi.responses import (
    HTMLResponse, JSONResponse, RedirectResponse,
    StreamingResponse
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ── Database ─────────────────────────────────────────────────
import psycopg2
from sqlalchemy import (
    create_engine, Column, String, Integer, Float,
    Boolean, Text, DateTime, BigInteger, JSON,
    text, inspect, MetaData, Table, select,
    and_, or_, func, Index
)
from sqlalchemy.orm import (
    declarative_base, sessionmaker, Session
)
from sqlalchemy.pool import NullPool

# ── Auth & Security ──────────────────────────────────────────
import bcrypt
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

# ── Scheduling ───────────────────────────────────────────────
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# ── Pydantic ─────────────────────────────────────────────────
from pydantic import BaseModel, validator, Field

# ── Standard Extras ──────────────────────────────────────────
import urllib.parse

# ════════════════════════════════════════════════════════════
# LOGGING SETUP
# ════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("RUHI-VIG-QNR")

# ════════════════════════════════════════════════════════════
# CONSTANTS & CONFIG
# ════════════════════════════════════════════════════════════
VERSION          = "3.0"
APP_NAME         = "RUHI-VIG QNR"
SECRET_KEY       = os.getenv("SECRET_KEY", "RUHIVIGQNR-SUPER-SECRET-KEY-v3-2024")
JWT_ALGORITHM    = "HS256"
JWT_EXPIRE_HOURS = 24
SHARD_LIMIT_MB   = 950          # 950 MB soft cap per worker
SHARD_LIMIT_BYTES= SHARD_LIMIT_MB * 1024 * 1024
OWNER_USERNAME   = "RUHIVIGQNR@QNR"
OWNER_PASSWORD   = "RUHIVIGQNR"
MASTER_DB_URL    = os.getenv("DATABASE_URL", "")

# ════════════════════════════════════════════════════════════
# SQLALCHEMY BASES
# ════════════════════════════════════════════════════════════
MasterBase = declarative_base()
WorkerBase = declarative_base()

# ════════════════════════════════════════════════════════════
# MASTER DB MODELS
# ════════════════════════════════════════════════════════════

class User(MasterBase):
    __tablename__ = "users"
    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username      = Column(String(120), unique=True, nullable=False, index=True)
    email         = Column(String(200), unique=True, nullable=True)
    password_hash = Column(String(256), nullable=False)
    role          = Column(String(20),  nullable=False, default="user")   # owner/admin/user
    is_active     = Column(Boolean,     default=True)
    api_key       = Column(String(64),  unique=True, nullable=True, index=True)
    balance       = Column(Float,       default=0.0)
    theme         = Column(String(20),  default="dark")
    created_at    = Column(DateTime,    default=datetime.datetime.utcnow)
    last_login    = Column(DateTime,    nullable=True)
    preferences   = Column(JSON,        default=dict)

class WorkerDB(MasterBase):
    __tablename__ = "worker_dbs"
    id          = Column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    name        = Column(String(120), unique=True, nullable=False)
    db_url      = Column(Text,    nullable=False)
    is_active   = Column(Boolean, default=True)
    is_healthy  = Column(Boolean, default=True)
    size_bytes  = Column(BigInteger, default=0)
    record_count= Column(Integer, default=0)
    latency_ms  = Column(Float,   default=0.0)
    created_at  = Column(DateTime, default=datetime.datetime.utcnow)
    last_ping   = Column(DateTime, nullable=True)
    meta_info   = Column(JSON,    default=dict)

class DataMapping(MasterBase):
    __tablename__ = "data_mappings"
    id          = Column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    record_id   = Column(String,  nullable=False, index=True)
    worker_id   = Column(String,  nullable=False, index=True)
    collection  = Column(String(120), nullable=False, default="default")
    created_at  = Column(DateTime, default=datetime.datetime.utcnow)
    user_id     = Column(String,  nullable=True)

class SystemConfig(MasterBase):
    __tablename__ = "system_config"
    key   = Column(String(120), primary_key=True)
    value = Column(Text,        nullable=False)

class ActivityLog(MasterBase):
    __tablename__ = "activity_logs"
    id         = Column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id    = Column(String,  nullable=True)
    username   = Column(String(120), nullable=True)
    action     = Column(String(200), nullable=False)
    details    = Column(Text,    nullable=True)
    ip_address = Column(String(60), nullable=True)
    level      = Column(String(20), default="info")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Transaction(MasterBase):
    __tablename__ = "transactions"
    id          = Column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id     = Column(String,  nullable=False, index=True)
    amount      = Column(Float,   nullable=False)
    tx_type     = Column(String(50), nullable=False)   # credit/debit/transfer
    description = Column(Text,    nullable=True)
    balance_after = Column(Float, nullable=False)
    created_at  = Column(DateTime, default=datetime.datetime.utcnow)

class Notification(MasterBase):
    __tablename__ = "notifications"
    id         = Column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id    = Column(String,  nullable=True)        # None = broadcast
    title      = Column(String(200), nullable=False)
    message    = Column(Text,    nullable=False)
    level      = Column(String(20), default="info")    # info/warning/danger
    is_read    = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class JsonSchema(MasterBase):
    __tablename__ = "json_schemas"
    id          = Column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    name        = Column(String(120), unique=True, nullable=False)
    schema_def  = Column(JSON,    nullable=False)
    collection  = Column(String(120), nullable=True)
    created_by  = Column(String,  nullable=True)
    created_at  = Column(DateTime, default=datetime.datetime.utcnow)

# ════════════════════════════════════════════════════════════
# WORKER DB MODEL (each shard)
# ════════════════════════════════════════════════════════════

class DataRecord(WorkerBase):
    __tablename__ = "data_records"
    id          = Column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    collection  = Column(String(120), nullable=False, default="default", index=True)
    data        = Column(JSON,    nullable=False)
    owner_id    = Column(String,  nullable=True,  index=True)
    schema_name = Column(String(120), nullable=True)
    size_bytes  = Column(Integer, default=0)
    created_at  = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.datetime.utcnow,
                         onupdate=datetime.datetime.utcnow)
    tags        = Column(JSON,    default=list)

class FileRecord(WorkerBase):
    __tablename__ = "file_records"
    id          = Column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    filename    = Column(String(300), nullable=False)
    mime_type   = Column(String(120), nullable=True)
    data_b64    = Column(Text,    nullable=False)       # Base64 encoded
    owner_id    = Column(String,  nullable=True)
    size_bytes  = Column(Integer, default=0)
    collection  = Column(String(120), default="files")
    created_at  = Column(DateTime, default=datetime.datetime.utcnow)

# ════════════════════════════════════════════════════════════
# ENGINE MANAGER
# ════════════════════════════════════════════════════════════

_master_engine  = None
_MasterSession  = None
_worker_engines : Dict[str, Any] = {}
_worker_sessions: Dict[str, Any] = {}

def _make_engine(url: str, pool: bool = True):
    """Create a SQLAlchemy engine with safe options."""
    kw = dict(
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"connect_timeout": 10},
        echo=False,
    )
    if not pool:
        return create_engine(url, poolclass=NullPool,
                             connect_args={"connect_timeout": 10}, echo=False)
    return create_engine(url, **kw)

def get_master_engine():
    global _master_engine
    if _master_engine is None:
        _master_engine = _make_engine(MASTER_DB_URL)
    return _master_engine

def get_master_session() -> Session:
    global _MasterSession
    if _MasterSession is None:
        _MasterSession = sessionmaker(bind=get_master_engine(), expire_on_commit=False)
    return _MasterSession()

def get_worker_session(db_url: str, worker_id: str) -> Session:
    if worker_id not in _worker_sessions:
        eng = _make_engine(db_url)
        _worker_engines[worker_id] = eng
        _worker_sessions[worker_id] = sessionmaker(bind=eng, expire_on_commit=False)
        # ensure tables exist
        WorkerBase.metadata.create_all(eng)
    return _worker_sessions[worker_id]()

@contextmanager
def master_session_ctx():
    s = get_master_session()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()

@contextmanager
def worker_session_ctx(db_url: str, worker_id: str):
    s = get_worker_session(db_url, worker_id)
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()

# ════════════════════════════════════════════════════════════
# DB INITIALISATION
# ════════════════════════════════════════════════════════════

def init_master_db():
    """Create all master tables and seed owner + defaults."""
    try:
        engine = get_master_engine()
        MasterBase.metadata.create_all(engine)
        log.info("Master DB tables created/verified.")

        with master_session_ctx() as s:
            # ── Owner account ────────────────────────────
            owner = s.query(User).filter_by(username=OWNER_USERNAME).first()
            if not owner:
                pw_bytes  = OWNER_PASSWORD.encode("utf-8")
                pw_hash   = bcrypt.hashpw(pw_bytes, bcrypt.gensalt(rounds=12))
                owner     = User(
                    id            = str(uuid.uuid4()),
                    username      = OWNER_USERNAME,
                    email         = "owner@ruhivigqnr.system",
                    password_hash = pw_hash.decode("utf-8"),
                    role          = "owner",
                    is_active     = True,
                    api_key       = secrets.token_hex(32),
                    balance       = 9999.99,
                )
                s.add(owner)
                log.info("Owner account created.")

            # ── Default config ───────────────────────────
            defaults = {
                "allow_registration"  : "true",
                "maintenance_mode"    : "false",
                "site_title"          : APP_NAME,
                "site_subtitle"       : "Distributed Database Cloud v3.0",
                "primary_color"       : "#6c63ff",
                "secondary_color"     : "#f64f59",
                "accent_color"        : "#43e97b",
                "bg_color"            : "#0d0d1a",
                "card_color"          : "#1a1a2e",
                "text_color"          : "#e0e0ff",
                "custom_css"          : "",
                "custom_html_header"  : "",
                "custom_html_footer"  : "",
                "bg_video_url"        : "",
                "bg_music_url"        : "",
                "bg_music_autoplay"   : "false",
                "bg_video_autoplay"   : "true",
                "anti_sleep_enabled"  : "true",
                "anti_sleep_urls"     : "",
                "shard_limit_mb"      : str(SHARD_LIMIT_MB),
                "max_file_size_mb"    : "5",
                "default_schema"      : "{}",
                "system_version"      : VERSION,
            }
            for k, v in defaults.items():
                if not s.query(SystemConfig).filter_by(key=k).first():
                    s.add(SystemConfig(key=k, value=v))

        log.info("Master DB initialised successfully.")
    except Exception as exc:
        log.error(f"Master DB init failed: {exc}")
        raise

def get_config(key: str, default: str = "") -> str:
    try:
        with master_session_ctx() as s:
            row = s.query(SystemConfig).filter_by(key=key).first()
            return row.value if row else default
    except Exception:
        return default

def set_config(key: str, value: str):
    with master_session_ctx() as s:
        row = s.query(SystemConfig).filter_by(key=key).first()
        if row:
            row.value = value
        else:
            s.add(SystemConfig(key=key, value=value))

# ════════════════════════════════════════════════════════════
# PASSWORD HELPERS (bcrypt direct)
# ════════════════════════════════════════════════════════════

def hash_password(plain: str) -> str:
    pw = plain.encode("utf-8")
    # bcrypt silently truncates at 72 bytes – guard against it
    if len(pw) > 72:
        pw = hashlib.sha256(pw).hexdigest().encode("utf-8")
    hashed = bcrypt.hashpw(pw, bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        pw = plain.encode("utf-8")
        if len(pw) > 72:
            pw = hashlib.sha256(pw).hexdigest().encode("utf-8")
        return bcrypt.checkpw(pw, hashed.encode("utf-8"))
    except Exception:
        return False

# ════════════════════════════════════════════════════════════
# JWT HELPERS
# ════════════════════════════════════════════════════════════

def create_token(user_id: str, username: str, role: str) -> str:
    payload = {
        "sub"      : user_id,
        "username" : username,
        "role"     : role,
        "exp"      : datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRE_HOURS),
        "iat"      : datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> Dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])

# ════════════════════════════════════════════════════════════
# ACTIVITY LOGGING
# ════════════════════════════════════════════════════════════

def log_activity(action: str, details: str = "", user_id: str = None,
                 username: str = "system", ip: str = None, level: str = "info"):
    try:
        with master_session_ctx() as s:
            s.add(ActivityLog(
                user_id    = user_id,
                username   = username,
                action     = action,
                details    = details,
                ip_address = ip,
                level      = level,
            ))
    except Exception as exc:
        log.warning(f"Activity log failed: {exc}")

# ════════════════════════════════════════════════════════════
# NOTIFICATION HELPERS
# ════════════════════════════════════════════════════════════

def push_notification(title: str, message: str, level: str = "info",
                      user_id: str = None):
    try:
        with master_session_ctx() as s:
            s.add(Notification(
                user_id = user_id,
                title   = title,
                message = message,
                level   = level,
            ))
    except Exception as exc:
        log.warning(f"Notification push failed: {exc}")

# ════════════════════════════════════════════════════════════
# SHARD ROUTER
# ════════════════════════════════════════════════════════════

def get_available_worker() -> Optional[WorkerDB]:
    """Return the worker with the most space that is still below limit."""
    try:
        limit = int(get_config("shard_limit_mb", str(SHARD_LIMIT_MB))) * 1024 * 1024
        with master_session_ctx() as s:
            workers = (s.query(WorkerDB)
                       .filter_by(is_active=True, is_healthy=True)
                       .filter(WorkerDB.size_bytes < limit)
                       .order_by(WorkerDB.size_bytes.asc())
                       .all())
            return workers[0] if workers else None
    except Exception as exc:
        log.error(f"get_available_worker: {exc}")
        return None

def get_worker_by_id(worker_id: str) -> Optional[WorkerDB]:
    try:
        with master_session_ctx() as s:
            return s.query(WorkerDB).filter_by(id=worker_id).first()
    except Exception:
        return None

def update_worker_stats(worker_id: str, delta_bytes: int = 0, delta_records: int = 0):
    try:
        with master_session_ctx() as s:
            w = s.query(WorkerDB).filter_by(id=worker_id).first()
            if w:
                w.size_bytes   = max(0, (w.size_bytes or 0) + delta_bytes)
                w.record_count = max(0, (w.record_count or 0) + delta_records)
                limit = int(get_config("shard_limit_mb", str(SHARD_LIMIT_MB))) * 1024 * 1024
                pct = (w.size_bytes / limit * 100) if limit else 0
                if pct >= 90:
                    push_notification(
                        f"⚠ Shard '{w.name}' at {pct:.1f}% capacity",
                        f"Worker {w.name} has used {w.size_bytes/(1024*1024):.1f} MB",
                        level="warning"
                    )
    except Exception as exc:
        log.warning(f"update_worker_stats: {exc}")

# ════════════════════════════════════════════════════════════
# JSON SCHEMA VALIDATOR
# ════════════════════════════════════════════════════════════

def validate_against_schema(data: dict, schema: dict) -> tuple[bool, str]:
    """Simple structural JSON schema validator."""
    if not schema:
        return True, ""
    required = schema.get("required", [])
    properties = schema.get("properties", {})
    for field in required:
        if field not in data:
            return False, f"Missing required field: '{field}'"
    for field, rules in properties.items():
        if field in data:
            expected_type = rules.get("type")
            value = data[field]
            type_map = {
                "string" : str,
                "integer": int,
                "number" : (int, float),
                "boolean": bool,
                "array"  : list,
                "object" : dict,
            }
            if expected_type and expected_type in type_map:
                if not isinstance(value, type_map[expected_type]):
                    return False, (f"Field '{field}' must be "
                                   f"type '{expected_type}'")
            max_len = rules.get("maxLength")
            if max_len and isinstance(value, str) and len(value) > max_len:
                return False, f"Field '{field}' exceeds maxLength {max_len}"
            min_val = rules.get("minimum")
            if min_val is not None and isinstance(value, (int, float)):
                if value < min_val:
                    return False, f"Field '{field}' below minimum {min_val}"
    return True, ""

# ════════════════════════════════════════════════════════════
# ANTI-SLEEP ENGINE
# ════════════════════════════════════════════════════════════

def anti_sleep_ping():
    if get_config("anti_sleep_enabled", "true") != "true":
        return
    urls_raw = get_config("anti_sleep_urls", "")
    urls = [u.strip() for u in urls_raw.split(",") if u.strip()]
    # always ping self
    self_url = os.getenv("RENDER_EXTERNAL_URL", "")
    if self_url:
        urls.append(self_url.rstrip("/") + "/api/health")
    # ping worker DBs via their stored URLs (just connect)
    try:
        with master_session_ctx() as s:
            workers = s.query(WorkerDB).filter_by(is_active=True).all()
        for w in workers:
            try:
                start = time.time()
                eng = _make_engine(w.db_url, pool=False)
                with eng.connect() as conn:
                    conn.execute(text("SELECT 1"))
                eng.dispose()
                ms = (time.time() - start) * 1000
                with master_session_ctx() as s2:
                    wrow = s2.query(WorkerDB).filter_by(id=w.id).first()
                    if wrow:
                        wrow.latency_ms = round(ms, 2)
                        wrow.last_ping  = datetime.datetime.utcnow()
                        wrow.is_healthy = True
            except Exception:
                with master_session_ctx() as s2:
                    wrow = s2.query(WorkerDB).filter_by(id=w.id).first()
                    if wrow:
                        wrow.is_healthy = False
    except Exception as exc:
        log.warning(f"Anti-sleep worker ping error: {exc}")

    for url in urls:
        try:
            with httpx.Client(timeout=8) as c:
                c.get(url)
        except Exception:
            pass

# ════════════════════════════════════════════════════════════
# SCHEDULER
# ════════════════════════════════════════════════════════════

scheduler = BackgroundScheduler(daemon=True)

def start_scheduler():
    scheduler.add_job(anti_sleep_ping, IntervalTrigger(minutes=4),
                      id="anti_sleep", replace_existing=True)
    scheduler.start()
    log.info("Background scheduler started.")

# ════════════════════════════════════════════════════════════
# FASTAPI APP
# ════════════════════════════════════════════════════════════

app = FastAPI(
    title  = f"{APP_NAME} v{VERSION}",
    version= VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ════════════════════════════════════════════════════════════
# AUTH DEPENDENCY
# ════════════════════════════════════════════════════════════

security = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = None
) -> Optional[Dict]:
    """Try cookie → Bearer → API-Key."""
    token = None

    # 1. Cookie
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        token = cookie_token

    # 2. Bearer header
    if not token and credentials:
        token = credentials.credentials

    # 3. API-Key header / query
    api_key = (request.headers.get("X-API-Key")
               or request.query_params.get("api_key"))
    if api_key and not token:
        try:
            with master_session_ctx() as s:
                user = s.query(User).filter_by(api_key=api_key, is_active=True).first()
                if user:
                    return {
                        "id"      : user.id,
                        "username": user.username,
                        "role"    : user.role,
                        "theme"   : user.theme,
                    }
        except Exception:
            pass
        return None

    if not token:
        return None
    try:
        payload = decode_token(token)
        return {
            "id"      : payload["sub"],
            "username": payload["username"],
            "role"    : payload["role"],
            "theme"   : "dark",
        }
    except (ExpiredSignatureError, InvalidTokenError):
        return None

def require_auth(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def require_admin(user=Depends(require_auth)):
    if user["role"] not in ("admin", "owner"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

def require_owner(user=Depends(require_auth)):
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access required")
    return user

def maintenance_check(user: Optional[Dict] = Depends(get_current_user)):
    if get_config("maintenance_mode", "false") == "true":
        if not user or user["role"] not in ("owner", "admin"):
            raise HTTPException(status_code=503,
                                detail="System under maintenance. Try later.")
    return user

# ════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    username: str
    password: str

class SignupRequest(BaseModel):
    username: str
    password: str
    email   : Optional[str] = None

class WorkerAddRequest(BaseModel):
    name  : str
    db_url: str

class DataWriteRequest(BaseModel):
    collection : str = "default"
    data       : Dict[str, Any]
    schema_name: Optional[str] = None
    tags       : List[str] = []

class BulkWriteRequest(BaseModel):
    collection : str = "default"
    records    : List[Dict[str, Any]]
    schema_name: Optional[str] = None

class BulkDeleteRequest(BaseModel):
    record_ids: List[str]

class ConfigUpdateRequest(BaseModel):
    configs: Dict[str, str]

class TransactionRequest(BaseModel):
    user_id    : str
    amount     : float
    tx_type    : str   # credit / debit
    description: Optional[str] = ""

class SchemaCreateRequest(BaseModel):
    name      : str
    schema_def: Dict[str, Any]
    collection: Optional[str] = None

class RebalanceRequest(BaseModel):
    record_ids       : List[str]
    target_worker_id : str

class SearchRequest(BaseModel):
    query      : str
    collection : Optional[str] = None
    limit      : int = 50

class NotificationMarkRequest(BaseModel):
    notification_ids: List[str]

# ════════════════════════════════════════════════════════════
# ██████████████████  HTML PAGES  ███████████████████████████
# ════════════════════════════════════════════════════════════

def base_styles(cfg: dict) -> str:
    return f"""
:root {{
  --primary   : {cfg.get('primary_color','#6c63ff')};
  --secondary : {cfg.get('secondary_color','#f64f59')};
  --accent    : {cfg.get('accent_color','#43e97b')};
  --bg        : {cfg.get('bg_color','#0d0d1a')};
  --card      : {cfg.get('card_color','#1a1a2e')};
  --text      : {cfg.get('text_color','#e0e0ff')};
  --border    : rgba(108,99,255,0.25);
  --radius    : 12px;
  --shadow    : 0 8px 32px rgba(0,0,0,0.4);
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth}}
body{{
  font-family:'Segoe UI',system-ui,sans-serif;
  background:var(--bg);color:var(--text);
  min-height:100vh;overflow-x:hidden;
}}
a{{color:var(--primary);text-decoration:none}}
a:hover{{text-decoration:underline}}
/* ── Scrollbar ── */
::-webkit-scrollbar{{width:6px;height:6px}}
::-webkit-scrollbar-track{{background:var(--bg)}}
::-webkit-scrollbar-thumb{{background:var(--primary);border-radius:3px}}
/* ── Cards ── */
.card{{
  background:var(--card);border:1px solid var(--border);
  border-radius:var(--radius);padding:1.5rem;
  box-shadow:var(--shadow);
}}
/* ── Buttons ── */
.btn{{
  display:inline-flex;align-items:center;gap:.4rem;
  padding:.55rem 1.2rem;border-radius:8px;border:none;
  cursor:pointer;font-size:.9rem;font-weight:600;
  transition:all .2s;
}}
.btn-primary{{background:var(--primary);color:#fff}}
.btn-primary:hover{{opacity:.85;transform:translateY(-1px)}}
.btn-danger{{background:var(--secondary);color:#fff}}
.btn-danger:hover{{opacity:.85}}
.btn-success{{background:var(--accent);color:#000}}
.btn-success:hover{{opacity:.85}}
.btn-sm{{padding:.35rem .75rem;font-size:.8rem}}
.btn-outline{{background:transparent;border:1px solid var(--primary);color:var(--primary)}}
.btn-outline:hover{{background:var(--primary);color:#fff}}
/* ── Form ── */
.form-group{{margin-bottom:1rem}}
.form-group label{{display:block;margin-bottom:.35rem;font-size:.85rem;opacity:.8}}
input,select,textarea{{
  width:100%;padding:.65rem .9rem;
  background:rgba(255,255,255,.05);
  border:1px solid var(--border);border-radius:8px;
  color:var(--text);font-size:.9rem;
  transition:border-color .2s;
}}
input:focus,select:focus,textarea:focus{{
  outline:none;border-color:var(--primary);
  box-shadow:0 0 0 3px rgba(108,99,255,.15);
}}
textarea{{resize:vertical;min-height:80px}}
/* ── Table ── */
.table-wrap{{overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:.85rem}}
th,td{{padding:.65rem .9rem;text-align:left;border-bottom:1px solid var(--border)}}
th{{background:rgba(108,99,255,.15);font-weight:600}}
tr:hover{{background:rgba(255,255,255,.03)}}
/* ── Badge ── */
.badge{{
  display:inline-block;padding:.2rem .55rem;
  border-radius:20px;font-size:.75rem;font-weight:700;
}}
.badge-success{{background:rgba(67,233,123,.2);color:#43e97b}}
.badge-danger{{background:rgba(246,79,89,.2);color:#f64f59}}
.badge-warning{{background:rgba(255,200,0,.2);color:#ffc800}}
.badge-info{{background:rgba(108,99,255,.2);color:var(--primary)}}
/* ── Alerts ── */
.alert{{padding:.85rem 1rem;border-radius:8px;margin-bottom:1rem;font-size:.9rem}}
.alert-danger{{background:rgba(246,79,89,.15);border:1px solid rgba(246,79,89,.4);color:#f64f59}}
.alert-success{{background:rgba(67,233,123,.15);border:1px solid rgba(67,233,123,.4);color:#43e97b}}
.alert-warning{{background:rgba(255,200,0,.15);border:1px solid rgba(255,200,0,.4);color:#ffc800}}
/* ── Sidebar ── */
.layout{{display:flex;min-height:100vh}}
.sidebar{{
  width:240px;min-width:240px;background:var(--card);
  border-right:1px solid var(--border);
  display:flex;flex-direction:column;
  position:sticky;top:0;height:100vh;overflow-y:auto;
}}
.sidebar-logo{{
  padding:1.5rem 1rem;font-size:1.1rem;font-weight:800;
  color:var(--primary);border-bottom:1px solid var(--border);
  line-height:1.3;
}}
.sidebar-logo small{{display:block;font-size:.7rem;color:var(--text);opacity:.6;font-weight:400}}
.nav-section{{padding:.75rem 1rem .25rem;font-size:.7rem;
  text-transform:uppercase;letter-spacing:.1em;opacity:.5}}
.nav-link{{
  display:flex;align-items:center;gap:.6rem;
  padding:.6rem 1rem;color:var(--text);border-radius:8px;
  margin:.1rem .5rem;font-size:.875rem;
  transition:all .18s;
}}
.nav-link:hover,.nav-link.active{{
  background:rgba(108,99,255,.2);color:var(--primary);
  text-decoration:none;
}}
.nav-link svg{{width:16px;height:16px;flex-shrink:0}}
/* ── Main content ── */
.main{{flex:1;padding:2rem;overflow-y:auto}}
.page-title{{
  font-size:1.6rem;font-weight:800;margin-bottom:1.5rem;
  background:linear-gradient(135deg,var(--primary),var(--secondary));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}}
/* ── Grid ── */
.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:1.25rem}}
.grid-3{{display:grid;grid-template-columns:repeat(3,1fr);gap:1.25rem}}
.grid-4{{display:grid;grid-template-columns:repeat(4,1fr);gap:1.25rem}}
@media(max-width:900px){{
  .grid-4,.grid-3{{grid-template-columns:1fr 1fr}}
  .grid-2{{grid-template-columns:1fr}}
}}
@media(max-width:600px){{
  .sidebar{{display:none}}
  .grid-4,.grid-3,.grid-2{{grid-template-columns:1fr}}
  .main{{padding:1rem}}
}}
/* ── Stat card ── */
.stat-card{{
  background:var(--card);border:1px solid var(--border);
  border-radius:var(--radius);padding:1.25rem;
  display:flex;flex-direction:column;gap:.4rem;
}}
.stat-card .label{{font-size:.78rem;opacity:.6;text-transform:uppercase;letter-spacing:.05em}}
.stat-card .value{{font-size:1.9rem;font-weight:800;color:var(--primary)}}
.stat-card .sub{{font-size:.78rem;opacity:.65}}
/* ── Progress ── */
.progress{{height:8px;background:rgba(255,255,255,.1);border-radius:4px;overflow:hidden}}
.progress-bar{{height:100%;border-radius:4px;transition:width .5s;
  background:linear-gradient(90deg,var(--primary),var(--secondary))}}
/* ── Toggle ── */
.toggle{{position:relative;display:inline-block;width:44px;height:24px}}
.toggle input{{opacity:0;width:0;height:0}}
.toggle-slider{{
  position:absolute;inset:0;border-radius:24px;
  background:rgba(255,255,255,.15);cursor:pointer;
  transition:.3s;
}}
.toggle-slider::before{{
  content:'';position:absolute;
  height:18px;width:18px;border-radius:50%;
  left:3px;bottom:3px;background:#fff;
  transition:.3s;
}}
.toggle input:checked+.toggle-slider{{background:var(--primary)}}
.toggle input:checked+.toggle-slider::before{{transform:translateX(20px)}}
/* ── Modal ── */
.modal-overlay{{
  display:none;position:fixed;inset:0;
  background:rgba(0,0,0,.7);z-index:1000;
  align-items:center;justify-content:center;
}}
.modal-overlay.active{{display:flex}}
.modal{{
  background:var(--card);border:1px solid var(--border);
  border-radius:var(--radius);padding:2rem;
  width:min(560px,95vw);max-height:90vh;overflow-y:auto;
  box-shadow:var(--shadow);
}}
.modal-title{{font-size:1.2rem;font-weight:700;margin-bottom:1.25rem}}
/* ── Top bar ── */
.topbar{{
  display:flex;align-items:center;justify-content:space-between;
  padding:.75rem 1.5rem;background:var(--card);
  border-bottom:1px solid var(--border);
  position:sticky;top:0;z-index:100;
}}
/* ── Light mode overrides ── */
body.light{{
  --bg:#f0f2ff;--card:#ffffff;--text:#1a1a2e;
  --border:rgba(108,99,255,.2);
}}
/* ── Code block ── */
pre{{
  background:rgba(0,0,0,.3);border-radius:8px;
  padding:1rem;overflow-x:auto;font-size:.8rem;
  border:1px solid var(--border);
}}
/* ── Notification dot ── */
.notif-dot{{
  display:inline-block;width:8px;height:8px;
  background:var(--secondary);border-radius:50%;
  margin-left:4px;vertical-align:middle;
}}
{cfg.get('custom_css','')}
"""

def get_all_config() -> dict:
    try:
        with master_session_ctx() as s:
            rows = s.query(SystemConfig).all()
            return {r.key: r.value for r in rows}
    except Exception:
        return {}

def sidebar_html(active: str, role: str, unread_notifs: int = 0) -> str:
    notif_dot = f'<span class="notif-dot"></span>' if unread_notifs > 0 else ""
    owner_links = ""
    if role == "owner":
        owner_links = """
        <div class="nav-section">Owner</div>
        <a class="nav-link {oc}" href="/dashboard/config">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/>
          </svg> Config & Branding</a>
        <a class="nav-link {mc}" href="/dashboard/media">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/>
          </svg> Media Suite</a>
        <a class="nav-link {sc}" href="/dashboard/schemas">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg> JSON Schemas</a>
        """.format(
            oc="active" if active=="config" else "",
            mc="active" if active=="media" else "",
            sc="active" if active=="schemas" else "",
        )
    admin_links = ""
    if role in ("owner", "admin"):
        admin_links = """
        <div class="nav-section">Admin</div>
        <a class="nav-link {uc}" href="/dashboard/users">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
          </svg> Users</a>
        <a class="nav-link {wc}" href="/dashboard/workers">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="3" width="20" height="14" rx="2"/>
            <path d="M8 21h8M12 17v4"/>
          </svg> Worker DBs</a>
        <a class="nav-link {hc}" href="/dashboard/health">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg> Health Monitor</a>
        <a class="nav-link {lc}" href="/dashboard/logs">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg> Activity Logs</a>
        <a class="nav-link {txc}" href="/dashboard/transactions">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="1" x2="12" y2="23"/>
            <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
          </svg> Transactions</a>
        <a class="nav-link {rbc}" href="/dashboard/rebalance">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="16 3 21 3 21 8"/>
            <line x1="4" y1="20" x2="21" y2="3"/>
            <polyline points="21 16 21 21 16 21"/>
            <line x1="15" y1="15" x2="21" y2="21"/>
          </svg> Rebalancing</a>
        """.format(
            uc ="active" if active=="users"        else "",
            wc ="active" if active=="workers"      else "",
            hc ="active" if active=="health"       else "",
            lc ="active" if active=="logs"         else "",
            txc="active" if active=="transactions" else "",
            rbc="active" if active=="rebalance"    else "",
        )
    return f"""
<nav class="sidebar">
  <div class="sidebar-logo">
    ⬡ {APP_NAME}<small>v{VERSION} Cloud System</small>
  </div>
  <div style="flex:1;padding:.5rem 0">
    <div class="nav-section">Main</div>
    <a class="nav-link {'active' if active=='dashboard' else ''}" href="/dashboard">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
        <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
      </svg> Dashboard</a>
    <a class="nav-link {'active' if active=='data' else ''}" href="/dashboard/data">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <ellipse cx="12" cy="5" rx="9" ry="3"/>
        <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
        <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
      </svg> Data Explorer</a>
    <a class="nav-link {'active' if active=='search' else ''}" href="/dashboard/search">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg> Smart Search</a>
    <a class="nav-link {'active' if active=='files' else ''}" href="/dashboard/files">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
        <polyline points="13 2 13 9 20 9"/>
      </svg> Files</a>
    <a class="nav-link {'active' if active=='wallet' else ''}" href="/dashboard/wallet">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="2" y="7" width="20" height="14" rx="2"/>
        <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
      </svg> Wallet</a>
    <a class="nav-link {'active' if active=='notifications' else ''}" href="/dashboard/notifications">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
        <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
      </svg> Notifications{notif_dot}</a>
    <a class="nav-link {'active' if active=='apikeys' else ''}" href="/dashboard/apikeys">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
      </svg> API Keys</a>
    <a class="nav-link {'active' if active=='profile' else ''}" href="/dashboard/profile">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
        <circle cx="12" cy="7" r="4"/>
      </svg> Profile</a>
    {admin_links}
    {owner_links}
  </div>
  <div style="padding:1rem;border-top:1px solid var(--border)">
    <a href="/logout" class="btn btn-danger btn-sm" style="width:100%;justify-content:center">
      ⏻ Logout</a>
  </div>
</nav>
"""

def page_shell(title: str, content: str, active: str,
               role: str, cfg: dict, unread: int = 0,
               extra_js: str = "") -> str:
    theme_class = "light" if cfg.get("theme","dark") == "light" else ""
    bg_video    = cfg.get("bg_video_url","")
    bg_music    = cfg.get("bg_music_url","")
    music_auto  = cfg.get("bg_music_autoplay","false") == "true"
    video_auto  = cfg.get("bg_video_autoplay","true")  == "true"

    video_html = ""
    if bg_video:
        video_html = f"""
        <video id="bgVideo" autoplay="{str(video_auto).lower()}" muted loop playsinline
          style="position:fixed;top:0;left:0;width:100%;height:100%;
                 object-fit:cover;z-index:-1;opacity:.18;pointer-events:none">
          <source src="{bg_video}" type="video/mp4">
        </video>"""

    music_html = ""
    if bg_music:
        music_html = f"""
        <audio id="bgMusic" {"autoplay" if music_auto else ""} loop
          style="display:none">
          <source src="{bg_music}" type="audio/mpeg">
        </audio>
        <button onclick="toggleMusic()" id="musicBtn"
          style="position:fixed;bottom:1rem;right:1rem;z-index:500;
                 background:var(--card);border:1px solid var(--border);
                 color:var(--text);border-radius:50%;width:40px;height:40px;
                 cursor:pointer;font-size:1rem">🎵</button>
        <script>
        function toggleMusic(){{
          var a=document.getElementById('bgMusic');
          if(a.paused){{a.play();document.getElementById('musicBtn').textContent='🔇'}}
          else{{a.pause();document.getElementById('musicBtn').textContent='🎵'}}
        }}
        </script>"""

    return f"""<!DOCTYPE html>
<html lang="en" class="{theme_class}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} – {APP_NAME}</title>
<style>{base_styles(cfg)}</style>
</head>
<body class="{theme_class}">
{video_html}
{music_html}
<div class="layout">
  {sidebar_html(active, role, unread)}
  <div style="flex:1;display:flex;flex-direction:column;overflow:hidden">
    <div class="topbar">
      <span style="font-weight:700">{title}</span>
      <div style="display:flex;align-items:center;gap:1rem">
        <span class="badge badge-info">{role.upper()}</span>
        <a href="/dashboard/notifications" style="position:relative">
          🔔{'<span class="notif-dot"></span>' if unread>0 else ''}
        </a>
      </div>
    </div>
    <div class="main">
      {cfg.get('custom_html_header','')}
      {content}
      {cfg.get('custom_html_footer','')}
    </div>
  </div>
</div>
<script>
// Theme toggle helper
function setTheme(t){{
  document.body.className = t==='light'?'light':'';
  fetch('/api/user/theme',{{method:'POST',
    headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify({{theme:t}})}});
}}
// Toast notifications
function showToast(msg, type='info'){{
  var d=document.createElement('div');
  d.style.cssText='position:fixed;bottom:1.5rem;left:50%;transform:translateX(-50%);'+
    'padding:.75rem 1.5rem;border-radius:8px;font-size:.9rem;font-weight:600;'+
    'z-index:9999;box-shadow:0 4px 20px rgba(0,0,0,.4);transition:opacity .5s';
  var colors={{info:'#6c63ff',success:'#43e97b',danger:'#f64f59',warning:'#ffc800'}};
  d.style.background=colors[type]||colors.info;
  d.style.color=type==='success'||type==='warning'?'#000':'#fff';
  d.textContent=msg;
  document.body.appendChild(d);
  setTimeout(()=>{{d.style.opacity='0';setTimeout(()=>d.remove(),600)}},3000);
}}
{extra_js}
</script>
</body>
</html>"""

# ════════════════════════════════════════════════════════════
# AUTH PAGES
# ════════════════════════════════════════════════════════════

LOGIN_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Login – RUHI-VIG QNR v3.0</title>
<style>
:root{{--primary:#6c63ff;--secondary:#f64f59;--accent:#43e97b;
  --bg:#0d0d1a;--card:#1a1a2e;--text:#e0e0ff;--border:rgba(108,99,255,.25)}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',system-ui,sans-serif;
  background:var(--bg);color:var(--text);
  min-height:100vh;display:flex;align-items:center;justify-content:center;
  background-image:radial-gradient(ellipse at 20% 50%,rgba(108,99,255,.15) 0,transparent 50%),
    radial-gradient(ellipse at 80% 20%,rgba(246,79,89,.1) 0,transparent 50%);}}
.box{{background:var(--card);border:1px solid var(--border);border-radius:16px;
  padding:2.5rem;width:min(400px,95vw);box-shadow:0 20px 60px rgba(0,0,0,.5)}}
.logo{{text-align:center;margin-bottom:2rem}}
.logo h1{{font-size:1.8rem;font-weight:900;
  background:linear-gradient(135deg,#6c63ff,#f64f59);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.logo p{{font-size:.8rem;opacity:.6;margin-top:.3rem}}
.form-group{{margin-bottom:1rem}}
label{{display:block;margin-bottom:.35rem;font-size:.85rem;opacity:.8}}
input{{width:100%;padding:.7rem 1rem;background:rgba(255,255,255,.05);
  border:1px solid var(--border);border-radius:8px;color:var(--text);
  font-size:.9rem;transition:border-color .2s}}
input:focus{{outline:none;border-color:var(--primary);
  box-shadow:0 0 0 3px rgba(108,99,255,.15)}}
.btn{{width:100%;padding:.75rem;border:none;border-radius:8px;
  background:linear-gradient(135deg,var(--primary),var(--secondary));
  color:#fff;font-size:1rem;font-weight:700;cursor:pointer;
  transition:opacity .2s;margin-top:.5rem}}
.btn:hover{{opacity:.85}}
.err{{background:rgba(246,79,89,.15);border:1px solid rgba(246,79,89,.4);
  color:#f64f59;padding:.75rem;border-radius:8px;margin-bottom:1rem;
  font-size:.875rem;display:none}}
.links{{text-align:center;margin-top:1rem;font-size:.85rem;opacity:.7}}
.links a{{color:var(--primary)}}
</style>
</head>
<body>
<div class="box">
  <div class="logo">
    <h1>⬡ RUHI-VIG QNR</h1>
    <p>Distributed Database Cloud System v3.0</p>
  </div>
  <div class="err" id="err"></div>
  <form id="loginForm">
    <div class="form-group">
      <label>Username</label>
      <input type="text" id="username" placeholder="Enter username" required>
    </div>
    <div class="form-group">
      <label>Password</label>
      <input type="password" id="password" placeholder="Enter password" required>
    </div>
    <button type="submit" class="btn">Sign In</button>
  </form>
  <div class="links">
    <a href="/signup">Create account</a> &nbsp;·&nbsp;
    <a href="/api/health">System Status</a>
  </div>
</div>
<script>
document.getElementById('loginForm').addEventListener('submit',async e=>{
  e.preventDefault();
  var err=document.getElementById('err');
  err.style.display='none';
  var btn=e.target.querySelector('button');
  btn.textContent='Signing in…';btn.disabled=true;
  var res=await fetch('/api/auth/login',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      username:document.getElementById('username').value,
      password:document.getElementById('password').value
    })
  });
  var data=await res.json();
  if(res.ok){
    document.cookie='access_token='+data.token+';path=/;max-age=86400';
    window.location.href='/dashboard';
  }else{
    err.textContent=data.detail||'Login failed';
    err.style.display='block';
    btn.textContent='Sign In';btn.disabled=false;
  }
});
</script>
</body>
</html>"""

SIGNUP_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sign Up – RUHI-VIG QNR v3.0</title>
<style>
:root{{--primary:#6c63ff;--secondary:#f64f59;--accent:#43e97b;
  --bg:#0d0d1a;--card:#1a1a2e;--text:#e0e0ff;--border:rgba(108,99,255,.25)}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',system-ui,sans-serif;
  background:var(--bg);color:var(--text);min-height:100vh;
  display:flex;align-items:center;justify-content:center;
  background-image:radial-gradient(ellipse at 80% 50%,rgba(108,99,255,.15) 0,transparent 50%)}}
.box{{background:var(--card);border:1px solid var(--border);border-radius:16px;
  padding:2.5rem;width:min(420px,95vw);box-shadow:0 20px 60px rgba(0,0,0,.5)}}
.logo{{text-align:center;margin-bottom:2rem}}
.logo h1{{font-size:1.6rem;font-weight:900;
  background:linear-gradient(135deg,#6c63ff,#43e97b);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.form-group{{margin-bottom:1rem}}
label{{display:block;margin-bottom:.35rem;font-size:.85rem;opacity:.8}}
input{{width:100%;padding:.7rem 1rem;background:rgba(255,255,255,.05);
  border:1px solid var(--border);border-radius:8px;color:var(--text);
  font-size:.9rem}}
input:focus{{outline:none;border-color:var(--primary)}}
.btn{{width:100%;padding:.75rem;border:none;border-radius:8px;
  background:linear-gradient(135deg,var(--primary),var(--accent));
  color:#000;font-size:1rem;font-weight:700;cursor:pointer;margin-top:.5rem}}
.msg{{padding:.75rem;border-radius:8px;margin-bottom:1rem;
  font-size:.875rem;display:none}}
.err{{background:rgba(246,79,89,.15);border:1px solid rgba(246,79,89,.4);color:#f64f59}}
.ok{{background:rgba(67,233,123,.15);border:1px solid rgba(67,233,123,.4);color:#43e97b}}
.links{{text-align:center;margin-top:1rem;font-size:.85rem;opacity:.7}}
.links a{{color:var(--primary)}}
</style>
</head>
<body>
<div class="box">
  <div class="logo">
    <h1>⬡ Create Account</h1>
    <p style="font-size:.8rem;opacity:.6;margin-top:.3rem">RUHI-VIG QNR v3.0</p>
  </div>
  <div class="msg err" id="err"></div>
  <div class="msg ok"  id="ok"></div>
  <form id="signupForm">
    <div class="form-group">
      <label>Username</label>
      <input type="text" id="username" placeholder="Choose a username" required>
    </div>
    <div class="form-group">
      <label>Email (optional)</label>
      <input type="email" id="email" placeholder="you@example.com">
    </div>
    <div class="form-group">
      <label>Password</label>
      <input type="password" id="password" placeholder="Strong password" required>
    </div>
    <button type="submit" class="btn">Create Account</button>
  </form>
  <div class="links"><a href="/login">Already have an account? Sign In</a></div>
</div>
<script>
document.getElementById('signupForm').addEventListener('submit',async e=>{
  e.preventDefault();
  var err=document.getElementById('err'),ok=document.getElementById('ok');
  err.style.display='none';ok.style.display='none';
  var btn=e.target.querySelector('button');
  btn.textContent='Creating…';btn.disabled=true;
  var res=await fetch('/api/auth/signup',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      username:document.getElementById('username').value,
      password:document.getElementById('password').value,
      email:document.getElementById('email').value||null
    })
  });
  var data=await res.json();
  if(res.ok){
    ok.textContent='Account created! Redirecting to login…';
    ok.style.display='block';
    setTimeout(()=>window.location.href='/login',2000);
  }else{
    err.textContent=data.detail||'Signup failed';
    err.style.display='block';
    btn.textContent='Create Account';btn.disabled=false;
  }
});
</script>
</body>
</html>"""

# ════════════════════════════════════════════════════════════
# DASHBOARD PAGE GENERATORS
# ════════════════════════════════════════════════════════════

def render_dashboard(user: dict, cfg: dict) -> str:
    try:
        with master_session_ctx() as s:
            total_users   = s.query(User).count()
            total_workers = s.query(WorkerDB).filter_by(is_active=True).count()
            healthy_w     = s.query(WorkerDB).filter_by(is_active=True, is_healthy=True).count()
            total_records = s.query(func.sum(WorkerDB.record_count)).scalar() or 0
            total_size    = s.query(func.sum(WorkerDB.size_bytes)).scalar()  or 0
            total_logs    = s.query(ActivityLog).count()
            recent_logs   = (s.query(ActivityLog)
                             .order_by(ActivityLog.created_at.desc())
                             .limit(8).all())
            workers       = s.query(WorkerDB).filter_by(is_active=True).all()

        limit_bytes = int(cfg.get("shard_limit_mb", str(SHARD_LIMIT_MB))) * 1024 * 1024
        size_mb     = total_size / (1024*1024)

        worker_cards = ""
        for w in workers:
            pct = min(100, int((w.size_bytes / limit_bytes * 100) if limit_bytes else 0))
            health_cls = "badge-success" if w.is_healthy else "badge-danger"
            health_txt = "Healthy" if w.is_healthy else "Down"
            worker_cards += f"""
            <tr>
              <td><b>{w.name}</b></td>
              <td>{w.size_bytes//(1024*1024)} MB</td>
              <td>{w.record_count}</td>
              <td>{w.latency_ms:.0f} ms</td>
              <td>
                <div class="progress"><div class="progress-bar" style="width:{pct}%"></div></div>
                <small>{pct}%</small>
              </td>
              <td><span class="badge {health_cls}">{health_txt}</span></td>
            </tr>"""

        log_rows = ""
        for l in recent_logs:
            lvl_cls = {"info":"badge-info","warning":"badge-warning",
                       "error":"badge-danger"}.get(l.level,"badge-info")
            ts = l.created_at.strftime("%H:%M:%S") if l.created_at else ""
            log_rows += f"""
            <tr>
              <td><span class="badge {lvl_cls}">{l.level}</span></td>
              <td>{l.username or 'system'}</td>
              <td>{l.action}</td>
              <td style="opacity:.6;font-size:.78rem">{ts}</td>
            </tr>"""

        content = f"""
        <h1 class="page-title">⬡ System Dashboard</h1>
        <div class="grid-4" style="margin-bottom:1.5rem">
          <div class="stat-card">
            <div class="label">Total Users</div>
            <div class="value">{total_users}</div>
            <div class="sub">Registered accounts</div>
          </div>
          <div class="stat-card">
            <div class="label">Worker DBs</div>
            <div class="value">{healthy_w}/{total_workers}</div>
            <div class="sub">Healthy / Total shards</div>
          </div>
          <div class="stat-card">
            <div class="label">Total Records</div>
            <div class="value">{total_records:,}</div>
            <div class="sub">Across all shards</div>
          </div>
          <div class="stat-card">
            <div class="label">Storage Used</div>
            <div class="value">{size_mb:.1f} MB</div>
            <div class="sub">Total across workers</div>
          </div>
        </div>

        <div class="grid-2">
          <div class="card">
            <h3 style="margin-bottom:1rem">🗄 Worker DB Status</h3>
            <div class="table-wrap">
              <table>
                <thead><tr><th>Name</th><th>Size</th><th>Records</th>
                  <th>Latency</th><th>Usage</th><th>Status</th></tr></thead>
                <tbody>{worker_cards or '<tr><td colspan="6" style="opacity:.5;text-align:center">No workers yet</td></tr>'}</tbody>
              </table>
            </div>
          </div>
          <div class="card">
            <h3 style="margin-bottom:1rem">📋 Recent Activity</h3>
            <div class="table-wrap">
              <table>
                <thead><tr><th>Level</th><th>User</th><th>Action</th><th>Time</th></tr></thead>
                <tbody>{log_rows or '<tr><td colspan="4" style="opacity:.5;text-align:center">No activity</td></tr>'}</tbody>
              </table>
            </div>
          </div>
        </div>

        <div class="card" style="margin-top:1.25rem">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem">
            <h3>⚡ Quick Actions</h3>
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:.75rem">
            <a href="/dashboard/data" class="btn btn-primary">+ New Record</a>
            <a href="/dashboard/search" class="btn btn-outline">🔍 Search Data</a>
            <a href="/dashboard/files" class="btn btn-outline">📁 Upload File</a>
            <a href="/dashboard/workers" class="btn btn-outline">🗄 Add Worker</a>
            <a href="/api/export/all" class="btn btn-outline">💾 Export Backup</a>
          </div>
        </div>
        """
        return content
    except Exception as exc:
        return f'<div class="alert alert-danger">Dashboard error: {exc}</div>'

def render_workers_page(cfg: dict) -> str:
    try:
        with master_session_ctx() as s:
            workers = s.query(WorkerDB).order_by(WorkerDB.created_at.desc()).all()

        limit_bytes = int(cfg.get("shard_limit_mb", str(SHARD_LIMIT_MB))) * 1024 * 1024
        rows = ""
        for w in workers:
            pct = min(100, int((w.size_bytes / limit_bytes * 100) if limit_bytes else 0))
            bar_color = "#f64f59" if pct>=90 else "#ffc800" if pct>=70 else "var(--accent)"
            health_cls = "badge-success" if w.is_healthy else "badge-danger"
            active_cls = "badge-success" if w.is_active  else "badge-warning"
            rows += f"""
            <tr>
              <td><b>{w.name}</b><br><small style="opacity:.5">{w.id[:8]}…</small></td>
              <td><code style="font-size:.75rem">{w.db_url[:45]}…</code></td>
              <td>
                <div class="progress" style="margin-bottom:.25rem">
                  <div class="progress-bar" style="width:{pct}%;background:{bar_color}"></div>
                </div>
                {w.size_bytes//(1024*1024)} MB / {cfg.get('shard_limit_mb',str(SHARD_LIMIT_MB))} MB ({pct}%)
              </td>
              <td>{w.record_count:,}</td>
              <td>{w.latency_ms:.0f} ms</td>
              <td>
                <span class="badge {health_cls}">{'● Healthy' if w.is_healthy else '● Down'}</span>
                <span class="badge {active_cls}" style="margin-top:.25rem">
                  {'Active' if w.is_active else 'Inactive'}</span>
              </td>
              <td>
                <button class="btn btn-sm btn-outline"
                  onclick="toggleWorker('{w.id}',{'false' if w.is_active else 'true'})">
                  {'Disable' if w.is_active else 'Enable'}</button>
                <button class="btn btn-sm btn-danger"
                  onclick="deleteWorker('{w.id}')">Remove</button>
              </td>
            </tr>"""

        return f"""
        <h1 class="page-title">🗄 Worker Databases</h1>
        <div class="card" style="margin-bottom:1.5rem">
          <h3 style="margin-bottom:1rem">➕ Add Worker DB</h3>
          <div style="display:flex;gap:1rem;flex-wrap:wrap">
            <div class="form-group" style="flex:1;min-width:180px;margin:0">
              <input type="text" id="wName" placeholder="Shard name (e.g. shard-01)">
            </div>
            <div class="form-group" style="flex:2;min-width:260px;margin:0">
              <input type="text" id="wUrl"
                placeholder="postgresql://user:pass@host:5432/dbname">
            </div>
            <button class="btn btn-primary" onclick="addWorker()">Add Worker</button>
          </div>
        </div>
        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem">
            <h3>Connected Shards ({len(workers)})</h3>
            <button class="btn btn-outline btn-sm" onclick="pingAll()">⚡ Ping All</button>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Name</th><th>URL</th><th>Storage</th>
                  <th>Records</th><th>Latency</th><th>Status</th><th>Actions</th></tr>
              </thead>
              <tbody id="workerTable">
                {rows or '<tr><td colspan="7" style="opacity:.5;text-align:center;padding:2rem">No worker DBs added yet</td></tr>'}
              </tbody>
            </table>
          </div>
        </div>"""
    except Exception as exc:
        return f'<div class="alert alert-danger">Workers page error: {exc}</div>'

def render_data_page(user: dict, cfg: dict) -> str:
    try:
        with master_session_ctx() as s:
            workers   = s.query(WorkerDB).filter_by(is_active=True).all()
            schemas   = s.query(JsonSchema).all()
            worker_opts = "".join(f'<option value="{w.id}">{w.name}</option>'
                                  for w in workers)
            schema_opts = '<option value="">No schema validation</option>' + \
                          "".join(f'<option value="{sc.name}">{sc.name}</option>'
                                  for sc in schemas)
    except Exception:
        worker_opts = ""
        schema_opts = ""

    return f"""
    <h1 class="page-title">🗃 Data Explorer</h1>
    <div class="grid-2">
      <div class="card">
        <h3 style="margin-bottom:1rem">✏ Write Record</h3>
        <div class="form-group">
          <label>Collection</label>
          <input type="text" id="collection" value="default" placeholder="Collection name">
        </div>
        <div class="form-group">
          <label>JSON Schema (optional)</label>
          <select id="schemaName">{schema_opts}</select>
        </div>
        <div class="form-group">
          <label>Tags (comma-separated)</label>
          <input type="text" id="tags" placeholder="tag1, tag2">
        </div>
        <div class="form-group">
          <label>JSON Data</label>
          <textarea id="jsonData" rows="8"
            placeholder='{{"name":"Alice","age":30,"email":"alice@example.com"}}'></textarea>
        </div>
        <button class="btn btn-primary" onclick="writeRecord()">💾 Write Record</button>

        <hr style="border-color:var(--border);margin:1.5rem 0">

        <h3 style="margin-bottom:1rem">📦 Bulk Write</h3>
        <div class="form-group">
          <label>Collection</label>
          <input type="text" id="bulkCollection" value="default">
        </div>
        <div class="form-group">
          <label>JSON Array of Records</label>
          <textarea id="bulkData" rows="5"
            placeholder='[{{"name":"Bob"}},{{"name":"Carol"}}]'></textarea>
        </div>
        <button class="btn btn-outline" onclick="bulkWrite()">📦 Bulk Write</button>
      </div>

      <div class="card">
        <h3 style="margin-bottom:1rem">🔎 Query Records</h3>
        <div class="form-group">
          <label>Worker DB</label>
          <select id="queryWorker"><option value="">Auto (all)</option>
            {worker_opts}</select>
        </div>
        <div class="form-group">
          <label>Collection</label>
          <input type="text" id="queryCollection" placeholder="Leave empty for all">
        </div>
        <div class="form-group">
          <label>Limit</label>
          <input type="number" id="queryLimit" value="20" min="1" max="500">
        </div>
        <button class="btn btn-primary" onclick="queryRecords()">🔍 Query</button>
        <button class="btn btn-outline" style="margin-left:.5rem"
          onclick="clearResults()">Clear</button>

        <div id="queryResults" style="margin-top:1rem;max-height:400px;overflow-y:auto"></div>

        <hr style="border-color:var(--border);margin:1.5rem 0">
        <h3 style="margin-bottom:1rem">🗑 Bulk Delete</h3>
        <div class="form-group">
          <label>Record IDs (comma-separated)</label>
          <textarea id="deleteIds" rows="3"
            placeholder="id1, id2, id3"></textarea>
        </div>
        <button class="btn btn-danger" onclick="bulkDelete()">🗑 Bulk Delete</button>
      </div>
    </div>"""

def render_search_page() -> str:
    return """
    <h1 class="page-title">🔍 Smart Search</h1>
    <div class="card" style="margin-bottom:1.5rem">
      <div style="display:flex;gap:1rem;flex-wrap:wrap;align-items:flex-end">
        <div class="form-group" style="flex:2;min-width:200px;margin:0">
          <label>Search Query</label>
          <input type="text" id="searchQuery"
            placeholder="Search across all worker DBs…"
            onkeypress="if(event.key==='Enter')doSearch()">
        </div>
        <div class="form-group" style="flex:1;min-width:140px;margin:0">
          <label>Collection (optional)</label>
          <input type="text" id="searchCollection" placeholder="all collections">
        </div>
        <div class="form-group" style="min-width:80px;margin:0">
          <label>Limit</label>
          <input type="number" id="searchLimit" value="50" min="1" max="500">
        </div>
        <button class="btn btn-primary" onclick="doSearch()">🔍 Search</button>
      </div>
    </div>
    <div class="card">
      <div id="searchInfo" style="margin-bottom:1rem;opacity:.7;font-size:.875rem"></div>
      <div class="table-wrap">
        <table id="searchTable">
          <thead>
            <tr><th>ID</th><th>Collection</th><th>Worker</th>
              <th>Data Preview</th><th>Created</th><th>Actions</th></tr>
          </thead>
          <tbody id="searchResults">
            <tr><td colspan="6" style="text-align:center;opacity:.5;padding:2rem">
              Enter a search query above</td></tr>
          </tbody>
        </table>
      </div>
    </div>"""

def render_files_page() -> str:
    return """
    <h1 class="page-title">📁 File Storage</h1>
    <div class="grid-2">
      <div class="card">
        <h3 style="margin-bottom:1rem">⬆ Upload File</h3>
        <p style="font-size:.85rem;opacity:.7;margin-bottom:1rem">
          Files are stored as Base64 in worker DB shards.
          Max size per file: configured in settings.
        </p>
        <div class="form-group">
          <label>Collection</label>
          <input type="text" id="fileCollection" value="files">
        </div>
        <div class="form-group">
          <label>Select File</label>
          <input type="file" id="fileInput"
            accept="image/*,.pdf,.doc,.docx,.txt,.json,.csv">
        </div>
        <button class="btn btn-primary" onclick="uploadFile()">⬆ Upload</button>
        <div id="uploadProgress" style="margin-top:1rem"></div>
      </div>
      <div class="card">
        <h3 style="margin-bottom:1rem">📂 Stored Files</h3>
        <button class="btn btn-outline btn-sm"
          onclick="loadFiles()" style="margin-bottom:1rem">🔄 Refresh</button>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Name</th><th>Type</th><th>Size</th>
              <th>Date</th><th>Actions</th></tr></thead>
            <tbody id="filesList">
              <tr><td colspan="5" style="text-align:center;opacity:.5;padding:1.5rem">
                Click Refresh to load files</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>"""

def render_wallet_page(user: dict) -> str:
    try:
        with master_session_ctx() as s:
            u  = s.query(User).filter_by(id=user["id"]).first()
            balance = u.balance if u else 0
            txs = (s.query(Transaction)
                   .filter_by(user_id=user["id"])
                   .order_by(Transaction.created_at.desc())
                   .limit(20).all())

        tx_rows = ""
        for t in txs:
            color = "var(--accent)" if t.tx_type == "credit" else "var(--secondary)"
            sign  = "+" if t.tx_type == "credit" else "-"
            ts    = t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else ""
            tx_rows += f"""
            <tr>
              <td>{ts}</td>
              <td><span class="badge {'badge-success' if t.tx_type=='credit' else 'badge-danger'}">
                {t.tx_type.upper()}</span></td>
              <td style="color:{color};font-weight:700">{sign}${abs(t.amount):.2f}</td>
              <td>${t.balance_after:.2f}</td>
              <td>{t.description or '—'}</td>
            </tr>"""

        admin_section = ""
        if user["role"] in ("owner", "admin"):
            try:
                with master_session_ctx() as s:
                    users_list = s.query(User).filter(User.role != "owner").all()
                user_opts = "".join(
                    f'<option value="{u2.id}">{u2.username}</option>'
                    for u2 in users_list)
                admin_section = f"""
                <div class="card" style="margin-top:1.5rem">
                  <h3 style="margin-bottom:1rem">💸 Admin: Credit/Debit User</h3>
                  <div style="display:flex;gap:1rem;flex-wrap:wrap">
                    <div class="form-group" style="flex:1;min-width:150px;margin:0">
                      <label>User</label>
                      <select id="txUser">{user_opts}</select>
                    </div>
                    <div class="form-group" style="flex:1;min-width:120px;margin:0">
                      <label>Amount ($)</label>
                      <input type="number" id="txAmount" value="10.00" min="0.01" step="0.01">
                    </div>
                    <div class="form-group" style="flex:1;min-width:120px;margin:0">
                      <label>Type</label>
                      <select id="txType">
                        <option value="credit">Credit (+)</option>
                        <option value="debit">Debit (-)</option>
                      </select>
                    </div>
                    <div class="form-group" style="flex:2;min-width:160px;margin:0">
                      <label>Description</label>
                      <input type="text" id="txDesc" placeholder="Reason…">
                    </div>
                    <div style="display:flex;align-items:flex-end">
                      <button class="btn btn-primary" onclick="sendTx()">💸 Submit</button>
                    </div>
                  </div>
                </div>"""
            except Exception:
                admin_section = ""

        return f"""
        <h1 class="page-title">💰 Wallet & Credits</h1>
        <div class="grid-3" style="margin-bottom:1.5rem">
          <div class="stat-card" style="border-color:rgba(67,233,123,.3)">
            <div class="label">Current Balance</div>
            <div class="value" style="color:var(--accent)">${balance:.2f}</div>
            <div class="sub">Available credits</div>
          </div>
          <div class="stat-card">
            <div class="label">Total Transactions</div>
            <div class="value">{len(txs)}</div>
            <div class="sub">Recent history (last 20)</div>
          </div>
          <div class="stat-card">
            <div class="label">Account</div>
            <div class="value" style="font-size:1rem">{user['username'][:18]}</div>
            <div class="sub">{user['role'].upper()}</div>
          </div>
        </div>
        <div class="card">
          <h3 style="margin-bottom:1rem">📊 Transaction History</h3>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Date</th><th>Type</th><th>Amount</th>
                  <th>Balance After</th><th>Description</th></tr>
              </thead>
              <tbody>
                {tx_rows or '<tr><td colspan="5" style="text-align:center;opacity:.5;padding:2rem">No transactions yet</td></tr>'}
              </tbody>
            </table>
          </div>
        </div>
        {admin_section}"""
    except Exception as exc:
        return f'<div class="alert alert-danger">Wallet error: {exc}</div>'

def render_health_page(cfg: dict) -> str:
    try:
        with master_session_ctx() as s:
            workers = s.query(WorkerDB).all()
            total_users = s.query(User).count()
            total_logs  = s.query(ActivityLog).count()
            total_notifs= s.query(Notification).count()

        limit_bytes = int(cfg.get("shard_limit_mb", str(SHARD_LIMIT_MB))) * 1024 * 1024
        cards = ""
        total_size = 0
        total_records = 0
        for w in workers:
            total_size    += w.size_bytes or 0
            total_records += w.record_count or 0
            pct  = min(100, int((w.size_bytes / limit_bytes * 100) if limit_bytes else 0))
            bar  = "#f64f59" if pct>=90 else "#ffc800" if pct>=70 else "var(--accent)"
            last = w.last_ping.strftime("%H:%M:%S") if w.last_ping else "Never"
            status_icon = "🟢" if w.is_healthy else "🔴"
            cards += f"""
            <div class="card">
              <div style="display:flex;justify-content:space-between;margin-bottom:.75rem">
                <b>{status_icon} {w.name}</b>
                <span class="badge {'badge-success' if w.is_active else 'badge-warning'}">
                  {'Active' if w.is_active else 'Inactive'}</span>
              </div>
              <div class="progress" style="margin-bottom:.5rem">
                <div class="progress-bar" style="width:{pct}%;background:{bar}"></div>
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:.4rem;
                          font-size:.8rem;opacity:.8">
                <span>Storage: {w.size_bytes//(1024*1024)} MB</span>
                <span>Usage: {pct}%</span>
                <span>Records: {w.record_count:,}</span>
                <span>Latency: {w.latency_ms:.0f} ms</span>
                <span>Last ping: {last}</span>
                <span>Healthy: {'Yes' if w.is_healthy else 'No'}</span>
              </div>
            </div>"""

        maint = cfg.get("maintenance_mode","false") == "true"
        reg   = cfg.get("allow_registration","true") == "true"

        return f"""
        <h1 class="page-title">📊 System Health Monitor</h1>
        <div class="grid-4" style="margin-bottom:1.5rem">
          <div class="stat-card">
            <div class="label">Total Storage</div>
            <div class="value">{total_size//(1024*1024)} MB</div>
            <div class="sub">Across {len(workers)} shard(s)</div>
          </div>
          <div class="stat-card">
            <div class="label">Total Records</div>
            <div class="value">{total_records:,}</div>
            <div class="sub">All collections</div>
          </div>
          <div class="stat-card">
            <div class="label">System Users</div>
            <div class="value">{total_users}</div>
            <div class="sub">Registered</div>
          </div>
          <div class="stat-card">
            <div class="label">Activity Logs</div>
            <div class="value">{total_logs:,}</div>
            <div class="sub">{total_notifs} notifications</div>
          </div>
        </div>

        <div class="card" style="margin-bottom:1.5rem">
          <h3 style="margin-bottom:1rem">⚙ System Flags</h3>
          <div style="display:flex;gap:2rem;flex-wrap:wrap">
            <div>
              <div class="label" style="font-size:.8rem;opacity:.6;margin-bottom:.25rem">
                Maintenance Mode</div>
              <span class="badge {'badge-warning' if maint else 'badge-success'}">
                {'🔒 ACTIVE' if maint else '✓ OFF'}</span>
            </div>
            <div>
              <div class="label" style="font-size:.8rem;opacity:.6;margin-bottom:.25rem">
                Public Registration</div>
              <span class="badge {'badge-success' if reg else 'badge-danger'}">
                {'✓ Enabled' if reg else '✗ Disabled'}</span>
            </div>
            <div>
              <div class="label" style="font-size:.8rem;opacity:.6;margin-bottom:.25rem">
                Anti-Sleep Engine</div>
              <span class="badge {'badge-success' if cfg.get('anti_sleep_enabled','true')=='true' else 'badge-danger'}">
                {'✓ Running' if cfg.get('anti_sleep_enabled','true')=='true' else '✗ Off'}</span>
            </div>
            <div>
              <div class="label" style="font-size:.8rem;opacity:.6;margin-bottom:.25rem">
                System Version</div>
              <span class="badge badge-info">v{VERSION}</span>
            </div>
          </div>
        </div>

        <h3 style="margin-bottom:1rem">🗄 Shard Details</h3>
        <div class="grid-3">
          {cards or '<div class="card" style="opacity:.6">No workers configured yet</div>'}
        </div>

        <div class="card" style="margin-top:1.5rem">
          <h3 style="margin-bottom:1rem">🔄 Actions</h3>
          <div style="display:flex;gap:.75rem;flex-wrap:wrap">
            <button class="btn btn-primary" onclick="pingWorkers()">⚡ Ping All Workers</button>
            <a href="/api/export/all" class="btn btn-outline">💾 Export All Data</a>
            <button class="btn btn-outline" onclick="location.reload()">🔄 Refresh</button>
          </div>
        </div>"""
    except Exception as exc:
        return f'<div class="alert alert-danger">Health monitor error: {exc}</div>'

def render_logs_page() -> str:
    try:
        with master_session_ctx() as s:
            logs = (s.query(ActivityLog)
                    .order_by(ActivityLog.created_at.desc())
                    .limit(100).all())
        rows = ""
        for l in logs:
            lvl_cls = {"info":"badge-info","warning":"badge-warning",
                       "error":"badge-danger"}.get(l.level,"badge-info")
            ts = l.created_at.strftime("%Y-%m-%d %H:%M:%S") if l.created_at else ""
            rows += f"""
            <tr>
              <td><span class="badge {lvl_cls}">{l.level}</span></td>
              <td>{l.username or 'system'}</td>
              <td>{l.action}</td>
              <td style="font-size:.8rem;opacity:.7">{(l.details or '')[:80]}</td>
              <td style="font-size:.78rem;opacity:.6">{l.ip_address or '—'}</td>
              <td style="font-size:.78rem">{ts}</td>
            </tr>"""
        return f"""
        <h1 class="page-title">📋 Activity Logs</h1>
        <div class="card">
          <div style="display:flex;justify-content:space-between;margin-bottom:1rem">
            <h3>Last 100 Events</h3>
            <div style="display:flex;gap:.5rem">
              <button class="btn btn-outline btn-sm" onclick="location.reload()">🔄 Refresh</button>
              <button class="btn btn-danger btn-sm" onclick="clearLogs()">🗑 Clear All</button>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Level</th><th>User</th><th>Action</th>
                  <th>Details</th><th>IP</th><th>Timestamp</th></tr>
              </thead>
              <tbody>{rows or '<tr><td colspan="6" style="text-align:center;opacity:.5;padding:2rem">No logs</td></tr>'}</tbody>
            </table>
          </div>
        </div>"""
    except Exception as exc:
        return f'<div class="alert alert-danger">Logs error: {exc}</div>'

def render_users_page() -> str:
    try:
        with master_session_ctx() as s:
            users = s.query(User).order_by(User.created_at.desc()).all()
        rows = ""
        for u in users:
            role_cls = {"owner":"badge-danger","admin":"badge-warning",
                        "user":"badge-info"}.get(u.role,"badge-info")
            active_cls = "badge-success" if u.is_active else "badge-danger"
            ts = u.created_at.strftime("%Y-%m-%d") if u.created_at else ""
            rows += f"""
            <tr>
              <td><b>{u.username}</b><br>
                <small style="opacity:.5">{u.email or '—'}</small></td>
              <td><span class="badge {role_cls}">{u.role.upper()}</span></td>
              <td><span class="badge {active_cls}">{'Active' if u.is_active else 'Inactive'}</span></td>
              <td>${u.balance:.2f}</td>
              <td style="font-size:.78rem">{ts}</td>
              <td>
                <button class="btn btn-sm btn-outline"
                  onclick="changeRole('{u.id}','{u.role}')">Role</button>
                <button class="btn btn-sm btn-outline"
                  onclick="toggleUser('{u.id}',{str(not u.is_active).lower()})">
                  {'Enable' if not u.is_active else 'Disable'}</button>
                {'<button class="btn btn-sm btn-danger" onclick="deleteUser(\'' + u.id + '\')">Delete</button>' if u.role != 'owner' else ''}
              </td>
            </tr>"""
        return f"""
        <h1 class="page-title">👥 User Management</h1>
        <div class="card">
          <div style="display:flex;justify-content:space-between;margin-bottom:1rem">
            <h3>All Users ({len(users)})</h3>
            <a href="/signup" target="_blank" class="btn btn-primary btn-sm">+ New User</a>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Username</th><th>Role</th><th>Status</th>
                  <th>Balance</th><th>Created</th><th>Actions</th></tr>
              </thead>
              <tbody>{rows}</tbody>
            </table>
          </div>
        </div>"""
    except Exception as exc:
        return f'<div class="alert alert-danger">Users error: {exc}</div>'

def render_config_page(cfg: dict) -> str:
    def cv(k, d=""): return cfg.get(k, d)
    def checked(k): return "checked" if cv(k) == "true" else ""

    return f"""
    <h1 class="page-title">⚙ Config & Branding</h1>
    <div class="grid-2">
      <div class="card">
        <h3 style="margin-bottom:1rem">🎨 Colors & Theme</h3>
        <div class="form-group">
          <label>Primary Color</label>
          <div style="display:flex;gap:.5rem;align-items:center">
            <input type="color" id="primary_color" value="{cv('primary_color','#6c63ff')}"
              style="width:50px;height:40px;padding:2px;cursor:pointer">
            <input type="text"  id="primary_color_hex" value="{cv('primary_color','#6c63ff')}">
          </div>
        </div>
        <div class="form-group">
          <label>Secondary Color</label>
          <div style="display:flex;gap:.5rem;align-items:center">
            <input type="color" id="secondary_color" value="{cv('secondary_color','#f64f59')}"
              style="width:50px;height:40px;padding:2px">
            <input type="text"  id="secondary_color_hex" value="{cv('secondary_color','#f64f59')}">
          </div>
        </div>
        <div class="form-group">
          <label>Accent Color</label>
          <div style="display:flex;gap:.5rem;align-items:center">
            <input type="color" id="accent_color" value="{cv('accent_color','#43e97b')}"
              style="width:50px;height:40px;padding:2px">
            <input type="text"  id="accent_color_hex" value="{cv('accent_color','#43e97b')}">
          </div>
        </div>
        <div class="form-group">
          <label>Background Color</label>
          <div style="display:flex;gap:.5rem;align-items:center">
            <input type="color" id="bg_color" value="{cv('bg_color','#0d0d1a')}"
              style="width:50px;height:40px;padding:2px">
            <input type="text"  id="bg_color_hex" value="{cv('bg_color','#0d0d1a')}">
          </div>
        </div>
        <div class="form-group">
          <label>Card Color</label>
          <div style="display:flex;gap:.5rem;align-items:center">
            <input type="color" id="card_color" value="{cv('card_color','#1a1a2e')}"
              style="width:50px;height:40px;padding:2px">
            <input type="text"  id="card_color_hex" value="{cv('card_color','#1a1a2e')}">
          </div>
        </div>
        <div class="form-group">
          <label>Text Color</label>
          <div style="display:flex;gap:.5rem;align-items:center">
            <input type="color" id="text_color" value="{cv('text_color','#e0e0ff')}"
              style="width:50px;height:40px;padding:2px">
            <input type="text"  id="text_color_hex" value="{cv('text_color','#e0e0ff')}">
          </div>
        </div>
        <button class="btn btn-primary" onclick="saveColors()">💾 Save Colors</button>
        <button class="btn btn-outline" style="margin-left:.5rem"
          onclick="livePreview()">👁 Live Preview</button>
      </div>

      <div>
        <div class="card" style="margin-bottom:1.25rem">
          <h3 style="margin-bottom:1rem">🏷 Site Identity</h3>
          <div class="form-group">
            <label>Site Title</label>
            <input type="text" id="site_title" value="{cv('site_title', APP_NAME)}">
          </div>
          <div class="form-group">
            <label>Site Subtitle</label>
            <input type="text" id="site_subtitle"
              value="{cv('site_subtitle','Distributed Database Cloud v3.0')}">
          </div>
          <div class="form-group">
            <label>Shard Storage Limit (MB)</label>
            <input type="number" id="shard_limit_mb"
              value="{cv('shard_limit_mb',str(SHARD_LIMIT_MB))}">
          </div>
          <div class="form-group">
            <label>Max File Upload Size (MB)</label>
            <input type="number" id="max_file_size_mb"
              value="{cv('max_file_size_mb','5')}">
          </div>
          <button class="btn btn-primary" onclick="saveSiteInfo()">💾 Save Info</button>
        </div>

        <div class="card" style="margin-bottom:1.25rem">
          <h3 style="margin-bottom:1rem">🔒 System Toggles</h3>
          <div style="display:flex;flex-direction:column;gap:1rem">
            <label style="display:flex;align-items:center;justify-content:space-between;gap:1rem">
              <span>Allow Public Registration</span>
              <label class="toggle">
                <input type="checkbox" id="allow_registration" {checked('allow_registration')}
                  onchange="toggleCfg('allow_registration',this.checked)">
                <span class="toggle-slider"></span>
              </label>
            </label>
            <label style="display:flex;align-items:center;justify-content:space-between;gap:1rem">
              <span>🔒 Maintenance Mode</span>
              <label class="toggle">
                <input type="checkbox" id="maintenance_mode" {checked('maintenance_mode')}
                  onchange="toggleCfg('maintenance_mode',this.checked)">
                <span class="toggle-slider"></span>
              </label>
            </label>
            <label style="display:flex;align-items:center;justify-content:space-between;gap:1rem">
              <span>⚡ Anti-Sleep Engine</span>
              <label class="toggle">
                <input type="checkbox" id="anti_sleep_enabled" {checked('anti_sleep_enabled')}
                  onchange="toggleCfg('anti_sleep_enabled',this.checked)">
                <span class="toggle-slider"></span>
              </label>
            </label>
          </div>
          <div class="form-group" style="margin-top:1rem">
            <label>Anti-Sleep URLs (comma-separated)</label>
            <textarea id="anti_sleep_urls" rows="2"
              placeholder="https://myapp.onrender.com, …">{cv('anti_sleep_urls')}</textarea>
          </div>
          <button class="btn btn-primary" onclick="saveAntiSleep()">💾 Save</button>
        </div>
      </div>
    </div>

    <div class="card" style="margin-top:1.25rem">
      <h3 style="margin-bottom:1rem">✏ Custom CSS / HTML</h3>
      <div class="grid-2">
        <div class="form-group">
          <label>Custom CSS</label>
          <textarea id="custom_css" rows="8"
            placeholder="/* Your custom CSS */">{cv('custom_css')}</textarea>
        </div>
        <div>
          <div class="form-group">
            <label>Custom Header HTML</label>
            <textarea id="custom_html_header" rows="3"
              placeholder="<!-- Header HTML -->">{cv('custom_html_header')}</textarea>
          </div>
          <div class="form-group">
            <label>Custom Footer HTML</label>
            <textarea id="custom_html_footer" rows="3"
              placeholder="<!-- Footer HTML -->">{cv('custom_html_footer')}</textarea>
          </div>
        </div>
      </div>
      <button class="btn btn-primary" onclick="saveCustomCode()">💾 Save Custom Code</button>
    </div>"""

def render_media_page(cfg: dict) -> str:
    def cv(k, d=""): return cfg.get(k, d)
    def checked(k): return "checked" if cv(k) == "true" else ""

    return f"""
    <h1 class="page-title">🎬 Media Suite</h1>
    <div class="grid-2">
      <div class="card">
        <h3 style="margin-bottom:1rem">🎥 Background Video</h3>
        <div class="form-group">
          <label>Video URL (MP4)</label>
          <input type="text" id="bg_video_url" value="{cv('bg_video_url')}"
            placeholder="https://example.com/video.mp4">
        </div>
        <label style="display:flex;align-items:center;justify-content:space-between;
                       margin-bottom:1rem">
          <span>Autoplay Video</span>
          <label class="toggle">
            <input type="checkbox" id="bg_video_autoplay" {checked('bg_video_autoplay')}
              onchange="toggleCfg('bg_video_autoplay',this.checked)">
            <span class="toggle-slider"></span>
          </label>
        </label>
        <button class="btn btn-primary" onclick="saveMedia('video')">💾 Save Video</button>
        <button class="btn btn-danger btn-sm" style="margin-left:.5rem"
          onclick="clearMedia('video')">✕ Clear</button>
        <div style="margin-top:1rem" id="videoPreview">
          {f'<video src="{cv("bg_video_url")}" controls muted style="width:100%;border-radius:8px;max-height:160px"></video>' if cv("bg_video_url") else '<p style="opacity:.5;font-size:.85rem">No video set</p>'}
        </div>
      </div>

      <div class="card">
        <h3 style="margin-bottom:1rem">🎵 Background Music</h3>
        <div class="form-group">
          <label>Music URL (MP3)</label>
          <input type="text" id="bg_music_url" value="{cv('bg_music_url')}"
            placeholder="https://example.com/music.mp3">
        </div>
        <label style="display:flex;align-items:center;justify-content:space-between;
                       margin-bottom:1rem">
          <span>Autoplay Music</span>
          <label class="toggle">
            <input type="checkbox" id="bg_music_autoplay" {checked('bg_music_autoplay')}
              onchange="toggleCfg('bg_music_autoplay',this.checked)">
            <span class="toggle-slider"></span>
          </label>
        </label>
        <button class="btn btn-primary" onclick="saveMedia('music')">💾 Save Music</button>
        <button class="btn btn-danger btn-sm" style="margin-left:.5rem"
          onclick="clearMedia('music')">✕ Clear</button>
        <div style="margin-top:1rem" id="musicPreview">
          {f'<audio src="{cv("bg_music_url")}" controls style="width:100%"></audio>' if cv("bg_music_url") else '<p style="opacity:.5;font-size:.85rem">No music set</p>'}
        </div>
      </div>
    </div>"""

def render_apikeys_page(user: dict) -> str:
    try:
        with master_session_ctx() as s:
            u = s.query(User).filter_by(id=user["id"]).first()
            api_key = u.api_key if u else None

        key_display = f"""
        <div style="background:rgba(0,0,0,.3);border-radius:8px;
                    padding:1rem;font-family:monospace;word-break:break-all;
                    border:1px solid var(--border);margin-bottom:1rem">
          {api_key}
        </div>
        <button class="btn btn-danger btn-sm" onclick="revokeKey()">🗑 Revoke & Regenerate</button>
        """ if api_key else """
        <p style="opacity:.7;margin-bottom:1rem">No API key generated yet.</p>
        <button class="btn btn-primary" onclick="generateKey()">🔑 Generate API Key</button>"""

        return f"""
        <h1 class="page-title">🔑 API Keys</h1>
        <div class="grid-2">
          <div class="card">
            <h3 style="margin-bottom:1rem">Your API Key</h3>
            {key_display}
            <hr style="border-color:var(--border);margin:1.25rem 0">
            <h4 style="margin-bottom:.75rem">Usage Examples</h4>
            <pre>
# Header (recommended)
curl -H "X-API-Key: YOUR_KEY" \\
  https://yourapp.com/api/data/query

# Query parameter
curl "https://yourapp.com/api/data/query?api_key=YOUR_KEY"

# Read record
curl -H "X-API-Key: YOUR_KEY" \\
  https://yourapp.com/api/data/record/RECORD_ID</pre>
          </div>
          <div class="card">
            <h3 style="margin-bottom:1rem">📚 API Reference</h3>
            <div style="display:flex;flex-direction:column;gap:.75rem;font-size:.875rem">
              <div style="border-bottom:1px solid var(--border);padding-bottom:.75rem">
                <b>POST /api/data/write</b><br>
                <span style="opacity:.7">Write a single record to a shard</span>
              </div>
              <div style="border-bottom:1px solid var(--border);padding-bottom:.75rem">
                <b>POST /api/data/bulk-write</b><br>
                <span style="opacity:.7">Write multiple records at once</span>
              </div>
              <div style="border-bottom:1px solid var(--border);padding-bottom:.75rem">
                <b>GET /api/data/query</b><br>
                <span style="opacity:.7">Query records (collection, limit params)</span>
              </div>
              <div style="border-bottom:1px solid var(--border);padding-bottom:.75rem">
                <b>GET /api/data/record/&#123;id&#125;</b><br>
                <span style="opacity:.7">Get a single record by ID</span>
              </div>
              <div style="border-bottom:1px solid var(--border);padding-bottom:.75rem">
                <b>DELETE /api/data/record/&#123;id&#125;</b><br>
                <span style="opacity:.7">Delete a record</span>
              </div>
              <div style="border-bottom:1px solid var(--border);padding-bottom:.75rem">
                <b>POST /api/search</b><br>
                <span style="opacity:.7">Full-text search across all shards</span>
              </div>
              <div>
                <b>GET /api/health</b><br>
                <span style="opacity:.7">System health check (public)</span>
              </div>
            </div>
            <div style="margin-top:1rem">
              <a href="/api/docs" target="_blank" class="btn btn-outline btn-sm">
                📖 Full API Docs (Swagger)</a>
            </div>
          </div>
        </div>"""
    except Exception as exc:
        return f'<div class="alert alert-danger">API Keys error: {exc}</div>'

def render_notifications_page(user: dict) -> str:
    try:
        with master_session_ctx() as s:
            notifs = (s.query(Notification)
                      .filter(or_(
                          Notification.user_id == user["id"],
                          Notification.user_id.is_(None)
                      ))
                      .order_by(Notification.created_at.desc())
                      .limit(50).all())

        rows = ""
        for n in notifs:
            lvl_cls = {"info":"badge-info","warning":"badge-warning",
                       "danger":"badge-danger"}.get(n.level,"badge-info")
            read_style = "" if n.is_read else "font-weight:700;"
            ts = n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else ""
            rows += f"""
            <tr style="{read_style}">
              <td><span class="badge {lvl_cls}">{n.level}</span></td>
              <td>{n.title}</td>
              <td style="font-size:.85rem">{n.message}</td>
              <td style="font-size:.78rem">{ts}</td>
              <td>
                {'<span style="opacity:.4">Read</span>' if n.is_read else
                 f'<button class="btn btn-sm btn-outline" onclick="markRead(\'{n.id}\')">✓ Mark Read</button>'}
              </td>
            </tr>"""

        return f"""
        <h1 class="page-title">🔔 Notifications</h1>
        <div class="card">
          <div style="display:flex;justify-content:space-between;margin-bottom:1rem">
            <h3>Your Notifications</h3>
            <button class="btn btn-outline btn-sm" onclick="markAllRead()">✓ Mark All Read</button>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Level</th><th>Title</th><th>Message</th>
                  <th>Date</th><th>Action</th></tr>
              </thead>
              <tbody>
                {rows or '<tr><td colspan="5" style="text-align:center;opacity:.5;padding:2rem">No notifications</td></tr>'}
              </tbody>
            </table>
          </div>
        </div>"""
    except Exception as exc:
        return f'<div class="alert alert-danger">Notifications error: {exc}</div>'

def render_schemas_page() -> str:
    try:
        with master_session_ctx() as s:
            schemas = s.query(JsonSchema).order_by(JsonSchema.created_at.desc()).all()
        rows = ""
        for sc in schemas:
            ts = sc.created_at.strftime("%Y-%m-%d") if sc.created_at else ""
            rows += f"""
            <tr>
              <td><b>{sc.name}</b></td>
              <td>{sc.collection or 'any'}</td>
              <td><pre style="margin:0;font-size:.75rem;max-height:60px;overflow:auto">{json.dumps(sc.schema_def, indent=2)[:120]}…</pre></td>
              <td style="font-size:.78rem">{ts}</td>
              <td>
                <button class="btn btn-danger btn-sm"
                  onclick="deleteSchema('{sc.id}')">Delete</button>
              </td>
            </tr>"""

        example = json.dumps({
            "required": ["name", "email"],
            "properties": {
                "name"  : {"type": "string", "maxLength": 100},
                "email" : {"type": "string"},
                "age"   : {"type": "integer", "minimum": 0},
                "active": {"type": "boolean"}
            }
        }, indent=2)

        return f"""
        <h1 class="page-title">📐 JSON Schemas</h1>
        <div class="grid-2">
          <div class="card">
            <h3 style="margin-bottom:1rem">➕ Create Schema</h3>
            <div class="form-group">
              <label>Schema Name</label>
              <input type="text" id="schemaName" placeholder="user-schema">
            </div>
            <div class="form-group">
              <label>Collection (optional)</label>
              <input type="text" id="schemaCollection" placeholder="users">
            </div>
            <div class="form-group">
              <label>Schema Definition (JSON)</label>
              <textarea id="schemaDef" rows="12"
                style="font-family:monospace">{example}</textarea>
            </div>
            <button class="btn btn-primary" onclick="createSchema()">💾 Save Schema</button>
          </div>
          <div class="card">
            <h3 style="margin-bottom:1rem">📋 Active Schemas ({len(schemas)})</h3>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr><th>Name</th><th>Collection</th><th>Definition</th>
                    <th>Created</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  {rows or '<tr><td colspan="5" style="text-align:center;opacity:.5;padding:2rem">No schemas defined</td></tr>'}
                </tbody>
              </table>
            </div>
          </div>
        </div>"""
    except Exception as exc:
        return f'<div class="alert alert-danger">Schemas error: {exc}</div>'

def render_rebalance_page() -> str:
    try:
        with master_session_ctx() as s:
            workers = s.query(WorkerDB).filter_by(is_active=True).all()
        worker_opts = "".join(
            f'<option value="{w.id}">{w.name} ({w.record_count} records)</option>'
            for w in workers)
        return f"""
        <h1 class="page-title">⚖ Shard Rebalancing</h1>
        <div class="card" style="margin-bottom:1.5rem">
          <h3 style="margin-bottom:1rem">📦 Move Records Between Shards</h3>
          <p style="opacity:.7;font-size:.875rem;margin-bottom:1rem">
            Enter record IDs to move from their current shard to a target worker DB.
          </p>
          <div class="form-group">
            <label>Target Worker DB</label>
            <select id="targetWorker">{worker_opts}</select>
          </div>
          <div class="form-group">
            <label>Record IDs (one per line)</label>
            <textarea id="rebalanceIds" rows="6"
              placeholder="record-id-1&#10;record-id-2&#10;record-id-3"></textarea>
          </div>
          <button class="btn btn-primary" onclick="startRebalance()">
            ⚖ Move Records</button>
        </div>
        <div class="card">
          <h3 style="margin-bottom:1rem">📊 Shard Distribution</h3>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Worker</th><th>Records</th><th>Size</th>
                  <th>Usage</th><th>Status</th></tr>
              </thead>
              <tbody>
                {''.join(f"""<tr>
                  <td><b>{w.name}</b></td>
                  <td>{w.record_count:,}</td>
                  <td>{w.size_bytes//(1024*1024)} MB</td>
                  <td>
                    <div class="progress">
                      <div class="progress-bar" style="width:{min(100,int(w.size_bytes/SHARD_LIMIT_BYTES*100))}%"></div>
                    </div>
                  </td>
                  <td><span class="badge {'badge-success' if w.is_healthy else 'badge-danger'}">
                    {'Healthy' if w.is_healthy else 'Down'}</span></td>
                </tr>""" for w in workers) or '<tr><td colspan="5" style="text-align:center;opacity:.5">No workers</td></tr>'}
              </tbody>
            </table>
          </div>
        </div>"""
    except Exception as exc:
        return f'<div class="alert alert-danger">Rebalance error: {exc}</div>'

def render_transactions_page() -> str:
    try:
        with master_session_ctx() as s:
            txs = (s.query(Transaction)
                   .order_by(Transaction.created_at.desc())
                   .limit(100).all())
            users_map = {u.id: u.username
                         for u in s.query(User).all()}
        rows = ""
        for t in txs:
            uname = users_map.get(t.user_id, t.user_id[:8])
            color = "var(--accent)" if t.tx_type=="credit" else "var(--secondary)"
            sign  = "+" if t.tx_type=="credit" else "-"
            ts    = t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else ""
            rows += f"""
            <tr>
              <td>{ts}</td>
              <td>{uname}</td>
              <td><span class="badge {'badge-success' if t.tx_type=='credit' else 'badge-danger'}">
                {t.tx_type.upper()}</span></td>
              <td style="color:{color};font-weight:700">{sign}${abs(t.amount):.2f}</td>
              <td>${t.balance_after:.2f}</td>
              <td>{t.description or '—'}</td>
            </tr>"""
        return f"""
        <h1 class="page-title">💸 All Transactions</h1>
        <div class="card">
          <div style="display:flex;justify-content:space-between;margin-bottom:1rem">
            <h3>Last 100 Transactions</h3>
            <button class="btn btn-outline btn-sm" onclick="location.reload()">🔄 Refresh</button>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Date</th><th>User</th><th>Type</th>
                  <th>Amount</th><th>Balance After</th><th>Description</th></tr>
              </thead>
              <tbody>
                {rows or '<tr><td colspan="6" style="text-align:center;opacity:.5;padding:2rem">No transactions</td></tr>'}
              </tbody>
            </table>
          </div>
        </div>"""
    except Exception as exc:
        return f'<div class="alert alert-danger">Transactions error: {exc}</div>'

def render_profile_page(user: dict) -> str:
    try:
        with master_session_ctx() as s:
            u = s.query(User).filter_by(id=user["id"]).first()
        if not u:
            return '<div class="alert alert-danger">User not found</div>'

        return f"""
        <h1 class="page-title">👤 Profile</h1>
        <div class="grid-2">
          <div class="card">
            <h3 style="margin-bottom:1rem">Account Info</h3>
            <div style="display:flex;flex-direction:column;gap:.75rem;font-size:.9rem">
              <div><b>Username:</b> {u.username}</div>
              <div><b>Email:</b> {u.email or '—'}</div>
              <div><b>Role:</b> <span class="badge badge-info">{u.role.upper()}</span></div>
              <div><b>Balance:</b> <span style="color:var(--accent)">${u.balance:.2f}</span></div>
              <div><b>Theme:</b> {u.theme}</div>
              <div><b>Member since:</b>
                {u.created_at.strftime("%Y-%m-%d") if u.created_at else "—"}</div>
              <div><b>Last login:</b>
                {u.last_login.strftime("%Y-%m-%d %H:%M") if u.last_login else "—"}</div>
            </div>
          </div>
          <div class="card">
            <h3 style="margin-bottom:1rem">🔐 Change Password</h3>
            <div class="form-group">
              <label>Current Password</label>
              <input type="password" id="curPw" placeholder="Current password">
            </div>
            <div class="form-group">
              <label>New Password</label>
              <input type="password" id="newPw" placeholder="New password">
            </div>
            <div class="form-group">
              <label>Confirm Password</label>
              <input type="password" id="confPw" placeholder="Confirm new password">
            </div>
            <button class="btn btn-primary" onclick="changePw()">🔐 Update Password</button>

            <hr style="border-color:var(--border);margin:1.5rem 0">
            <h3 style="margin-bottom:1rem">🎨 UI Theme</h3>
            <div style="display:flex;gap:.75rem">
              <button class="btn {'btn-primary' if u.theme=='dark' else 'btn-outline'}"
                onclick="setThemeAndSave('dark')">🌙 Dark</button>
              <button class="btn {'btn-primary' if u.theme=='light' else 'btn-outline'}"
                onclick="setThemeAndSave('light')">☀ Light</button>
            </div>
          </div>
        </div>"""
    except Exception as exc:
        return f'<div class="alert alert-danger">Profile error: {exc}</div>'

# ════════════════════════════════════════════════════════════
# PAGE JAVASCRIPT
# ════════════════════════════════════════════════════════════

DASHBOARD_JS = """
async function pingAll(){
  var r=await fetch('/api/admin/ping-workers',{method:'POST'});
  var d=await r.json();showToast(d.message||'Pinged','success');
  setTimeout(()=>location.reload(),1500);
}
async function pingWorkers(){return pingAll();}
"""

WORKERS_JS = """
async function addWorker(){
  var n=document.getElementById('wName').value.trim();
  var u=document.getElementById('wUrl').value.trim();
  if(!n||!u){showToast('Name and URL required','danger');return;}
  var r=await fetch('/api/admin/workers',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name:n,db_url:u})});
  var d=await r.json();
  if(r.ok){showToast('Worker added!','success');setTimeout(()=>location.reload(),1200);}
  else showToast(d.detail||'Error','danger');
}
async function toggleWorker(id,state){
  var r=await fetch('/api/admin/workers/'+id+'/toggle',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({is_active:state})});
  if(r.ok){showToast('Updated','success');location.reload();}
}
async function deleteWorker(id){
  if(!confirm('Remove this worker? Existing records will not be deleted.'))return;
  var r=await fetch('/api/admin/workers/'+id,{method:'DELETE'});
  if(r.ok){showToast('Removed','success');setTimeout(()=>location.reload(),1000);}
}
async function pingAll(){
  var r=await fetch('/api/admin/ping-workers',{method:'POST'});
  var d=await r.json();showToast(d.message,'success');
  setTimeout(()=>location.reload(),2000);
}
"""

DATA_JS = """
async function writeRecord(){
  var col=document.getElementById('collection').value.trim()||'default';
  var raw=document.getElementById('jsonData').value.trim();
  var schema=document.getElementById('schemaName').value;
  var tagsRaw=document.getElementById('tags').value;
  var tags=tagsRaw?tagsRaw.split(',').map(t=>t.trim()).filter(Boolean):[];
  var data;
  try{data=JSON.parse(raw);}catch(e){showToast('Invalid JSON','danger');return;}
  var r=await fetch('/api/data/write',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({collection:col,data:data,schema_name:schema||null,tags:tags})});
  var d=await r.json();
  if(r.ok)showToast('Record saved → '+d.worker,'success');
  else showToast(d.detail||'Error','danger');
}
async function bulkWrite(){
  var col=document.getElementById('bulkCollection').value.trim()||'default';
  var raw=document.getElementById('bulkData').value.trim();
  var records;
  try{records=JSON.parse(raw);}catch(e){showToast('Invalid JSON array','danger');return;}
  if(!Array.isArray(records)){showToast('Must be a JSON array','danger');return;}
  var r=await fetch('/api/data/bulk-write',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({collection:col,records:records})});
  var d=await r.json();
  if(r.ok)showToast('Wrote '+d.written+' records','success');
  else showToast(d.detail||'Error','danger');
}
async function queryRecords(){
  var worker=document.getElementById('queryWorker').value;
  var col=document.getElementById('queryCollection').value.trim();
  var limit=document.getElementById('queryLimit').value||20;
  var url='/api/data/query?limit='+limit;
  if(worker)url+='&worker_id='+worker;
  if(col)url+='&collection='+encodeURIComponent(col);
  var r=await fetch(url);
  var d=await r.json();
  var box=document.getElementById('queryResults');
  if(!r.ok){box.innerHTML='<div class="alert alert-danger">'+( d.detail||'Error')+'</div>';return;}
  var records=d.records||[];
  if(!records.length){box.innerHTML='<p style="opacity:.6;font-size:.85rem">No records found</p>';return;}
  var html='<table style="width:100%;font-size:.8rem"><thead><tr><th>ID</th><th>Collection</th><th>Data</th><th>Action</th></tr></thead><tbody>';
  records.forEach(rec=>{
    html+='<tr><td style="opacity:.6">'+rec.id.substr(0,8)+'…</td><td>'+rec.collection+'</td><td><pre style="margin:0;max-height:60px;overflow:auto;font-size:.75rem">'+JSON.stringify(rec.data,null,1).substr(0,120)+'</pre></td>';
    html+='<td><button class="btn btn-sm btn-danger" onclick="deleteRecord(\''+rec.id+'\')">Del</button></td></tr>';
  });
  html+='</tbody></table>';
  box.innerHTML=html;
}
async function deleteRecord(id){
  if(!confirm('Delete record '+id+'?'))return;
  var r=await fetch('/api/data/record/'+id,{method:'DELETE'});
  if(r.ok){showToast('Deleted','success');queryRecords();}
  else showToast('Error deleting','danger');
}
async function bulkDelete(){
  var raw=document.getElementById('deleteIds').value;
  var ids=raw.split(',').map(s=>s.trim()).filter(Boolean);
  if(!ids.length){showToast('No IDs provided','danger');return;}
  var r=await fetch('/api/data/bulk-delete',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({record_ids:ids})});
  var d=await r.json();
  if(r.ok)showToast('Deleted '+d.deleted+' records','success');
  else showToast(d.detail||'Error','danger');
}
function clearResults(){document.getElementById('queryResults').innerHTML='';}
"""

SEARCH_JS = """
async function doSearch(){
  var q=document.getElementById('searchQuery').value.trim();
  var col=document.getElementById('searchCollection').value.trim();
  var limit=document.getElementById('searchLimit').value||50;
  if(!q){showToast('Enter a search query','warning');return;}
  document.getElementById('searchInfo').textContent='Searching…';
  document.getElementById('searchResults').innerHTML=
    '<tr><td colspan="6" style="text-align:center;opacity:.6">Searching all shards…</td></tr>';
  var r=await fetch('/api/search',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({query:q,collection:col||null,limit:parseInt(limit)})});
  var d=await r.json();
  if(!r.ok){
    document.getElementById('searchInfo').textContent='Error: '+(d.detail||'Unknown');
    return;
  }
  var results=d.results||[];
  document.getElementById('searchInfo').textContent=
    'Found '+results.length+' result(s) across '+d.shards_searched+' shard(s) in '+d.time_ms+'ms';
  var html='';
  if(!results.length){
    html='<tr><td colspan="6" style="text-align:center;opacity:.5;padding:1.5rem">No results found</td></tr>';
  }else{
    results.forEach(rec=>{
      var preview=JSON.stringify(rec.data||{}).substr(0,80);
      html+='<tr>';
      html+='<td style="font-size:.75rem;font-family:monospace">'+rec.id.substr(0,12)+'…</td>';
      html+='<td>'+rec.collection+'</td>';
      html+='<td style="font-size:.78rem;opacity:.7">'+rec.worker_name+'</td>';
      html+='<td style="font-size:.78rem"><code>'+preview+'</code></td>';
      html+='<td style="font-size:.75rem">'+rec.created_at+'</td>';
      html+='<td><button class="btn btn-sm btn-danger" onclick="deleteRecord(\''+rec.id+'\')">Del</button></td>';
      html+='</tr>';
    });
  }
  document.getElementById('searchResults').innerHTML=html;
}
async function deleteRecord(id){
  if(!confirm('Delete record '+id+'?'))return;
  var r=await fetch('/api/data/record/'+id,{method:'DELETE'});
  var d=await r.json();
  if(r.ok){showToast('Deleted','success');doSearch();}
  else showToast(d.detail||'Error deleting','danger');
}
"""

FILES_JS = """
async function uploadFile(){
  var inp=document.getElementById('fileInput');
  var col=document.getElementById('fileCollection').value||'files';
  var prog=document.getElementById('uploadProgress');
  if(!inp.files.length){showToast('Select a file first','warning');return;}
  var file=inp.files[0];
  prog.innerHTML='<p style="opacity:.7">Reading file…</p>';
  var reader=new FileReader();
  reader.onload=async function(e){
    var b64=e.target.result.split(',')[1];
    prog.innerHTML='<p style="opacity:.7">Uploading…</p>';
    var r=await fetch('/api/files/upload',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        filename:file.name,mime_type:file.type,
        data_b64:b64,collection:col
      })});
    var d=await r.json();
    if(r.ok){
      prog.innerHTML='<div class="alert alert-success">✓ Uploaded: '+d.id+'</div>';
      loadFiles();
    }else{
      prog.innerHTML='<div class="alert alert-danger">Error: '+(d.detail||'Upload failed')+'</div>';
    }
  };
  reader.readAsDataURL(file);
}
async function loadFiles(){
  var r=await fetch('/api/files/list');
  var d=await r.json();
  var files=d.files||[];
  var html='';
  if(!files.length){
    html='<tr><td colspan="5" style="text-align:center;opacity:.5;padding:1.5rem">No files stored</td></tr>';
  }else{
    files.forEach(f=>{
      var size=(f.size_bytes/1024).toFixed(1)+'KB';
      html+='<tr>';
      html+='<td>'+f.filename+'</td>';
      html+='<td><span class="badge badge-info">'+f.mime_type+'</span></td>';
      html+='<td>'+size+'</td>';
      html+='<td style="font-size:.78rem">'+f.created_at+'</td>';
      html+='<td>';
      html+='<a href="/api/files/download/'+f.id+'" class="btn btn-sm btn-outline" target="_blank">⬇</a> ';
      html+='<button class="btn btn-sm btn-danger" onclick="deleteFile(\''+f.id+'\')">Del</button>';
      html+='</td></tr>';
    });
  }
  document.getElementById('filesList').innerHTML=html;
}
async function deleteFile(id){
  if(!confirm('Delete this file?'))return;
  var r=await fetch('/api/files/'+id,{method:'DELETE'});
  if(r.ok){showToast('Deleted','success');loadFiles();}
  else showToast('Error','danger');
}
"""

WALLET_JS = """
async function sendTx(){
  var userId=document.getElementById('txUser').value;
  var amount=parseFloat(document.getElementById('txAmount').value);
  var txType=document.getElementById('txType').value;
  var desc=document.getElementById('txDesc').value;
  if(!userId||!amount||amount<=0){showToast('Fill all fields','warning');return;}
  var r=await fetch('/api/admin/transactions',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({user_id:userId,amount:amount,tx_type:txType,description:desc})});
  var d=await r.json();
  if(r.ok){showToast('Transaction completed. New balance: $'+d.balance_after,'success');
    setTimeout(()=>location.reload(),1500);}
  else showToast(d.detail||'Error','danger');
}
"""

CONFIG_JS = """
// Sync color pickers with hex inputs
['primary','secondary','accent','bg','card','text'].forEach(name=>{
  var picker=document.getElementById(name+'_color');
  var hex=document.getElementById(name+'_color_hex');
  if(!picker||!hex)return;
  picker.addEventListener('input',()=>{hex.value=picker.value;});
  hex.addEventListener('input',()=>{
    if(/^#[0-9A-Fa-f]{6}$/.test(hex.value))picker.value=hex.value;
  });
});
function livePreview(){
  var root=document.documentElement;
  root.style.setProperty('--primary',document.getElementById('primary_color').value);
  root.style.setProperty('--secondary',document.getElementById('secondary_color').value);
  root.style.setProperty('--accent',document.getElementById('accent_color').value);
  root.style.setProperty('--bg',document.getElementById('bg_color').value);
  root.style.setProperty('--card',document.getElementById('card_color').value);
  root.style.setProperty('--text',document.getElementById('text_color').value);
  showToast('Preview applied (not saved)','info');
}
async function saveColors(){
  var configs={};
  ['primary_color','secondary_color','accent_color','bg_color','card_color','text_color'].forEach(k=>{
    configs[k]=document.getElementById(k).value;
  });
  var r=await fetch('/api/admin/config',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({configs:configs})});
  if(r.ok){showToast('Colors saved!','success');}
  else showToast('Error saving','danger');
}
async function saveSiteInfo(){
  var configs={
    site_title:document.getElementById('site_title').value,
    site_subtitle:document.getElementById('site_subtitle').value,
    shard_limit_mb:document.getElementById('shard_limit_mb').value,
    max_file_size_mb:document.getElementById('max_file_size_mb').value,
  };
  var r=await fetch('/api/admin/config',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({configs:configs})});
  if(r.ok)showToast('Site info saved!','success');
  else showToast('Error','danger');
}
async function toggleCfg(key,val){
  var configs={};configs[key]=val?'true':'false';
  var r=await fetch('/api/admin/config',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({configs:configs})});
  if(r.ok)showToast((val?'Enabled':'Disabled')+': '+key,'success');
  else showToast('Error','danger');
}
async function saveAntiSleep(){
  var configs={anti_sleep_urls:document.getElementById('anti_sleep_urls').value};
  var r=await fetch('/api/admin/config',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({configs:configs})});
  if(r.ok)showToast('Saved!','success');
  else showToast('Error','danger');
}
async function saveCustomCode(){
  var configs={
    custom_css:document.getElementById('custom_css').value,
    custom_html_header:document.getElementById('custom_html_header').value,
    custom_html_footer:document.getElementById('custom_html_footer').value,
  };
  var r=await fetch('/api/admin/config',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({configs:configs})});
  if(r.ok)showToast('Custom code saved!','success');
  else showToast('Error','danger');
}
"""

MEDIA_JS = """
async function saveMedia(type){
  var configs={};
  if(type==='video'){
    configs.bg_video_url=document.getElementById('bg_video_url').value;
  }else{
    configs.bg_music_url=document.getElementById('bg_music_url').value;
  }
  var r=await fetch('/api/admin/config',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({configs:configs})});
  if(r.ok){showToast('Saved!','success');setTimeout(()=>location.reload(),1000);}
  else showToast('Error','danger');
}
async function clearMedia(type){
  var configs={};
  if(type==='video')configs.bg_video_url='';
  else configs.bg_music_url='';
  var r=await fetch('/api/admin/config',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({configs:configs})});
  if(r.ok){showToast('Cleared!','success');setTimeout(()=>location.reload(),1000);}
}
async function toggleCfg(key,val){
  var configs={};configs[key]=val?'true':'false';
  await fetch('/api/admin/config',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({configs:configs})});
}
"""

APIKEYS_JS = """
async function generateKey(){
  var r=await fetch('/api/user/generate-api-key',{method:'POST'});
  var d=await r.json();
  if(r.ok){showToast('API key generated!','success');setTimeout(()=>location.reload(),1200);}
  else showToast(d.detail||'Error','danger');
}
async function revokeKey(){
  if(!confirm('Revoke and regenerate your API key?'))return;
  var r=await fetch('/api/user/generate-api-key',{method:'POST'});
  if(r.ok){showToast('New key generated','success');setTimeout(()=>location.reload(),1200);}
}
"""

NOTIFICATIONS_JS = """
async function markRead(id){
  var r=await fetch('/api/notifications/read',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({notification_ids:[id]})});
  if(r.ok)location.reload();
}
async function markAllRead(){
  var r=await fetch('/api/notifications/read-all',{method:'POST'});
  if(r.ok)location.reload();
}
"""

SCHEMAS_JS = """
async function createSchema(){
  var name=document.getElementById('schemaName').value.trim();
  var col=document.getElementById('schemaCollection').value.trim();
  var raw=document.getElementById('schemaDef').value.trim();
  if(!name){showToast('Schema name required','warning');return;}
  var schema;
  try{schema=JSON.parse(raw);}catch(e){showToast('Invalid JSON schema','danger');return;}
  var r=await fetch('/api/schemas',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name:name,schema_def:schema,collection:col||null})});
  var d=await r.json();
  if(r.ok){showToast('Schema created!','success');setTimeout(()=>location.reload(),1200);}
  else showToast(d.detail||'Error','danger');
}
async function deleteSchema(id){
  if(!confirm('Delete this schema?'))return;
  var r=await fetch('/api/schemas/'+id,{method:'DELETE'});
  if(r.ok){showToast('Deleted','success');location.reload();}
}
"""

REBALANCE_JS = """
async function startRebalance(){
  var targetId=document.getElementById('targetWorker').value;
  var raw=document.getElementById('rebalanceIds').value;
  var ids=raw.split('\\n').map(s=>s.trim()).filter(Boolean);
  if(!targetId||!ids.length){showToast('Select target and enter IDs','warning');return;}
  if(!confirm('Move '+ids.length+' record(s) to selected worker?'))return;
  var r=await fetch('/api/admin/rebalance',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({record_ids:ids,target_worker_id:targetId})});
  var d=await r.json();
  if(r.ok){showToast('Moved '+d.moved+' record(s)','success');}
  else showToast(d.detail||'Error','danger');
}
"""

USERS_JS = """
async function changeRole(id,cur){
  var roles=['user','admin'];
  if(cur==='owner')return showToast('Cannot change owner role','warning');
  var next=cur==='user'?'admin':'user';
  if(!confirm('Change role to '+next+'?'))return;
  var r=await fetch('/api/admin/users/'+id+'/role',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({role:next})});
  if(r.ok){showToast('Role updated','success');location.reload();}
  else showToast('Error','danger');
}
async function toggleUser(id,state){
  var r=await fetch('/api/admin/users/'+id+'/toggle',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({is_active:state})});
  if(r.ok){showToast('User updated','success');location.reload();}
}
async function deleteUser(id){
  if(!confirm('Permanently delete this user?'))return;
  var r=await fetch('/api/admin/users/'+id,{method:'DELETE'});
  if(r.ok){showToast('Deleted','success');location.reload();}
  else showToast('Error','danger');
}
"""

LOGS_JS = """
async function clearLogs(){
  if(!confirm('Clear ALL activity logs?'))return;
  var r=await fetch('/api/admin/logs/clear',{method:'DELETE'});
  if(r.ok){showToast('Logs cleared','success');location.reload();}
}
"""

PROFILE_JS = """
async function changePw(){
  var cur=document.getElementById('curPw').value;
  var nw=document.getElementById('newPw').value;
  var cf=document.getElementById('confPw').value;
  if(!cur||!nw||!cf){showToast('Fill all fields','warning');return;}
  if(nw!==cf){showToast('Passwords do not match','danger');return;}
  if(nw.length<6){showToast('Password must be 6+ characters','warning');return;}
  var r=await fetch('/api/user/change-password',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({current_password:cur,new_password:nw})});
  var d=await r.json();
  if(r.ok)showToast('Password changed!','success');
  else showToast(d.detail||'Error','danger');
}
function setThemeAndSave(t){
  setTheme(t);
  showToast('Theme set to '+t,'success');
  setTimeout(()=>location.reload(),1000);
}
"""

HEALTH_JS = """
async function pingWorkers(){
  var r=await fetch('/api/admin/ping-workers',{method:'POST'});
  var d=await r.json();showToast(d.message,'success');
  setTimeout(()=>location.reload(),2000);
}
"""

# ════════════════════════════════════════════════════════════
# ROUTE HELPERS
# ════════════════════════════════════════════════════════════

def unread_count(user_id: str) -> int:
    try:
        with master_session_ctx() as s:
            return (s.query(Notification)
                    .filter(
                        or_(Notification.user_id==user_id,
                            Notification.user_id.is_(None)),
                        Notification.is_read==False
                    ).count())
    except Exception:
        return 0

def get_user_theme(user: dict) -> str:
    try:
        with master_session_ctx() as s:
            u = s.query(User).filter_by(id=user["id"]).first()
            return u.theme if u else "dark"
    except Exception:
        return "dark"

# ════════════════════════════════════════════════════════════
# ████████████████  PAGE ROUTES  ████████████████████████████
# ════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse("/dashboard")
    return RedirectResponse("/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return HTMLResponse(LOGIN_PAGE)

@app.get("/signup", response_class=HTMLResponse)
async def signup_page():
    if get_config("allow_registration","true") != "true":
        return HTMLResponse("""
        <html><body style="background:#0d0d1a;color:#e0e0ff;
          font-family:sans-serif;display:flex;align-items:center;
          justify-content:center;height:100vh;text-align:center">
          <div><h2>Registration Disabled</h2>
          <p style="opacity:.7">Public registration is currently disabled.</p>
          <a href="/login" style="color:#6c63ff">← Back to Login</a></div>
        </body></html>""")
    return HTMLResponse(SIGNUP_PAGE)

@app.get("/logout")
async def logout():
    resp = RedirectResponse("/login")
    resp.delete_cookie("access_token")
    return resp

# ── Dashboard Routes ─────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request,
                    _: None = Depends(maintenance_check)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    cfg   = get_all_config()
    cfg["theme"] = get_user_theme(user)
    unread = unread_count(user["id"])
    content = render_dashboard(user, cfg)
    return HTMLResponse(page_shell("Dashboard", content, "dashboard",
                                   user["role"], cfg, unread, DASHBOARD_JS))

@app.get("/dashboard/workers", response_class=HTMLResponse)
async def workers_page(request: Request,
                       user: dict = Depends(require_admin)):
    cfg    = get_all_config()
    cfg["theme"] = get_user_theme(user)
    content = render_workers_page(cfg)
    return HTMLResponse(page_shell("Worker DBs", content, "workers",
                                   user["role"], cfg,
                                   unread_count(user["id"]), WORKERS_JS))

@app.get("/dashboard/data", response_class=HTMLResponse)
async def data_page(request: Request,
                    user: dict = Depends(require_auth)):
    cfg  = get_all_config()
    cfg["theme"] = get_user_theme(user)
    content = render_data_page(user, cfg)
    return HTMLResponse(page_shell("Data Explorer", content, "data",
                                   user["role"], cfg,
                                   unread_count(user["id"]), DATA_JS))

@app.get("/dashboard/search", response_class=HTMLResponse)
async def search_page(request: Request,
                      user: dict = Depends(require_auth)):
    cfg = get_all_config()
    cfg["theme"] = get_user_theme(user)
    return HTMLResponse(page_shell("Smart Search", render_search_page(),
                                   "search", user["role"], cfg,
                                   unread_count(user["id"]), SEARCH_JS))

@app.get("/dashboard/files", response_class=HTMLResponse)
async def files_page(request: Request,
                     user: dict = Depends(require_auth)):
    cfg = get_all_config()
    cfg["theme"] = get_user_theme(user)
    return HTMLResponse(page_shell("File Storage", render_files_page(),
                                   "files", user["role"], cfg,
                                   unread_count(user["id"]), FILES_JS))

@app.get("/dashboard/wallet", response_class=HTMLResponse)
async def wallet_page(request: Request,
                      user: dict = Depends(require_auth)):
    cfg = get_all_config()
    cfg["theme"] = get_user_theme(user)
    return HTMLResponse(page_shell("Wallet", render_wallet_page(user),
                                   "wallet", user["role"], cfg,
                                   unread_count(user["id"]), WALLET_JS))

@app.get("/dashboard/health", response_class=HTMLResponse)
async def health_page(request: Request,
                      user: dict = Depends(require_admin)):
    cfg = get_all_config()
    cfg["theme"] = get_user_theme(user)
    return HTMLResponse(page_shell("Health Monitor", render_health_page(cfg),
                                   "health", user["role"], cfg,
                                   unread_count(user["id"]), HEALTH_JS))

@app.get("/dashboard/logs", response_class=HTMLResponse)
async def logs_page(request: Request,
                    user: dict = Depends(require_admin)):
    cfg = get_all_config()
    cfg["theme"] = get_user_theme(user)
    return HTMLResponse(page_shell("Activity Logs", render_logs_page(),
                                   "logs", user["role"], cfg,
                                   unread_count(user["id"]), LOGS_JS))

@app.get("/dashboard/users", response_class=HTMLResponse)
async def users_page(request: Request,
                     user: dict = Depends(require_admin)):
    cfg = get_all_config()
    cfg["theme"] = get_user_theme(user)
    return HTMLResponse(page_shell("Users", render_users_page(),
                                   "users", user["role"], cfg,
                                   unread_count(user["id"]), USERS_JS))

@app.get("/dashboard/config", response_class=HTMLResponse)
async def config_page(request: Request,
                      user: dict = Depends(require_owner)):
    cfg = get_all_config()
    cfg["theme"] = get_user_theme(user)
    return HTMLResponse(page_shell("Config & Branding", render_config_page(cfg),
                                   "config", user["role"], cfg,
                                   unread_count(user["id"]), CONFIG_JS))

@app.get("/dashboard/media", response_class=HTMLResponse)
async def media_page(request: Request,
                     user: dict = Depends(require_owner)):
    cfg = get_all_config()
    cfg["theme"] = get_user_theme(user)
    return HTMLResponse(page_shell("Media Suite", render_media_page(cfg),
                                   "media", user["role"], cfg,
                                   unread_count(user["id"]), MEDIA_JS))

@app.get("/dashboard/apikeys", response_class=HTMLResponse)
async def apikeys_page(request: Request,
                       user: dict = Depends(require_auth)):
    cfg = get_all_config()
    cfg["theme"] = get_user_theme(user)
    return HTMLResponse(page_shell("API Keys", render_apikeys_page(user),
                                   "apikeys", user["role"], cfg,
                                   unread_count(user["id"]), APIKEYS_JS))

@app.get("/dashboard/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request,
                              user: dict = Depends(require_auth)):
    cfg = get_all_config()
    cfg["theme"] = get_user_theme(user)
    return HTMLResponse(page_shell("Notifications",
                                   render_notifications_page(user),
                                   "notifications", user["role"], cfg,
                                   unread_count(user["id"]), NOTIFICATIONS_JS))

@app.get("/dashboard/schemas", response_class=HTMLResponse)
async def schemas_page(request: Request,
                       user: dict = Depends(require_owner)):
    cfg = get_all_config()
    cfg["theme"] = get_user_theme(user)
    return HTMLResponse(page_shell("JSON Schemas", render_schemas_page(),
                                   "schemas", user["role"], cfg,
                                   unread_count(user["id"]), SCHEMAS_JS))

@app.get("/dashboard/rebalance", response_class=HTMLResponse)
async def rebalance_page(request: Request,
                         user: dict = Depends(require_admin)):
    cfg = get_all_config()
    cfg["theme"] = get_user_theme(user)
    return HTMLResponse(page_shell("Rebalancing", render_rebalance_page(),
                                   "rebalance", user["role"], cfg,
                                   unread_count(user["id"]), REBALANCE_JS))

@app.get("/dashboard/transactions", response_class=HTMLResponse)
async def transactions_page(request: Request,
                             user: dict = Depends(require_admin)):
    cfg = get_all_config()
    cfg["theme"] = get_user_theme(user)
    return HTMLResponse(page_shell("Transactions",
                                   render_transactions_page(),
                                   "transactions", user["role"], cfg,
                                   unread_count(user["id"]), ""))

@app.get("/dashboard/profile", response_class=HTMLResponse)
async def profile_page(request: Request,
                       user: dict = Depends(require_auth)):
    cfg = get_all_config()
    cfg["theme"] = get_user_theme(user)
    return HTMLResponse(page_shell("Profile", render_profile_page(user),
                                   "profile", user["role"], cfg,
                                   unread_count(user["id"]), PROFILE_JS))

# ════════════════════════════════════════════════════════════
# ████████████████  API ROUTES  █████████████████████████████
# ════════════════════════════════════════════════════════════

# ── Health ───────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    try:
        with master_session_ctx() as s:
            s.execute(text("SELECT 1"))
        return {
            "status" : "ok",
            "app"    : APP_NAME,
            "version": VERSION,
            "time"   : datetime.datetime.utcnow().isoformat(),
        }
    except Exception as exc:
        return JSONResponse({"status":"error","detail":str(exc)},
                            status_code=503)

# ── Auth ─────────────────────────────────────────────────────

@app.post("/api/auth/login")
async def api_login(body: LoginRequest, request: Request):
    try:
        with master_session_ctx() as s:
            user = s.query(User).filter_by(username=body.username).first()
            if not user or not verify_password(body.password, user.password_hash):
                raise HTTPException(status_code=401, detail="Invalid credentials")
            if not user.is_active:
                raise HTTPException(status_code=403, detail="Account disabled")

            if get_config("maintenance_mode","false") == "true" \
               and user.role not in ("owner","admin"):
                raise HTTPException(status_code=503, detail="System under maintenance")

            token = create_token(user.id, user.username, user.role)
            user.last_login = datetime.datetime.utcnow()
            ip = request.client.host if request.client else "unknown"
            log_activity("LOGIN", f"User {user.username} logged in",
                         user_id=user.id, username=user.username, ip=ip)
            return {"token": token, "role": user.role,
                    "username": user.username}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/auth/signup")
async def api_signup(body: SignupRequest, request: Request):
    if get_config("allow_registration","true") != "true":
        raise HTTPException(status_code=403, detail="Registration is disabled")
    if len(body.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be 3+ characters")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be 6+ characters")
    try:
        with master_session_ctx() as s:
            if s.query(User).filter_by(username=body.username).first():
                raise HTTPException(status_code=409, detail="Username already taken")
            if body.email and s.query(User).filter_by(email=body.email).first():
                raise HTTPException(status_code=409, detail="Email already registered")
            pw_hash = hash_password(body.password)
            u = User(
                username      = body.username,
                email         = body.email,
                password_hash = pw_hash,
                role          = "user",
                is_active     = True,
                balance       = 0.0,
            )
            s.add(u)
        ip = request.client.host if request.client else "unknown"
        log_activity("SIGNUP", f"New user: {body.username}",
                     username=body.username, ip=ip)
        return {"message": "Account created successfully"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ── Data Write / Query ────────────────────────────────────────

@app.post("/api/data/write")
async def write_record(body: DataWriteRequest,
                       user: dict = Depends(require_auth)):
    # Schema validation
    if body.schema_name:
        try:
            with master_session_ctx() as s:
                sc = s.query(JsonSchema).filter_by(name=body.schema_name).first()
            if sc:
                ok, err = validate_against_schema(body.data, sc.schema_def)
                if not ok:
                    raise HTTPException(status_code=422,
                                        detail=f"Schema validation failed: {err}")
        except HTTPException:
            raise
        except Exception:
            pass

    worker = get_available_worker()
    if not worker:
        raise HTTPException(status_code=503,
                            detail="No available worker DB. Add a worker or increase limits.")
    try:
        rec_id    = str(uuid.uuid4())
        data_str  = json.dumps(body.data)
        size_b    = len(data_str.encode("utf-8"))

        with worker_session_ctx(worker.db_url, worker.id) as ws:
            rec = DataRecord(
                id          = rec_id,
                collection  = body.collection,
                data        = body.data,
                owner_id    = user["id"],
                schema_name = body.schema_name,
                size_bytes  = size_b,
                tags        = body.tags,
            )
            ws.add(rec)

        with master_session_ctx() as ms:
            ms.add(DataMapping(
                record_id  = rec_id,
                worker_id  = worker.id,
                collection = body.collection,
                user_id    = user["id"],
            ))

        update_worker_stats(worker.id, delta_bytes=size_b, delta_records=1)
        log_activity("DATA_WRITE", f"Record {rec_id} → {worker.name}",
                     user_id=user["id"], username=user["username"])
        return {
            "id"        : rec_id,
            "worker"    : worker.name,
            "collection": body.collection,
            "size_bytes": size_b,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/data/bulk-write")
async def bulk_write(body: BulkWriteRequest,
                     user: dict = Depends(require_auth)):
    if not body.records:
        raise HTTPException(status_code=400, detail="No records provided")
    if len(body.records) > 1000:
        raise HTTPException(status_code=400, detail="Max 1000 records per bulk write")

    worker = get_available_worker()
    if not worker:
        raise HTTPException(status_code=503, detail="No available worker DB")

    written = 0
    total_bytes = 0
    mappings = []
    records_to_insert = []

    for item in body.records:
        rec_id   = str(uuid.uuid4())
        data_str = json.dumps(item)
        size_b   = len(data_str.encode("utf-8"))
        records_to_insert.append(DataRecord(
            id         = rec_id,
            collection = body.collection,
            data       = item,
            owner_id   = user["id"],
            size_bytes = size_b,
        ))
        mappings.append(DataMapping(
            record_id  = rec_id,
            worker_id  = worker.id,
            collection = body.collection,
            user_id    = user["id"],
        ))
        total_bytes += size_b
        written += 1

    try:
        with worker_session_ctx(worker.db_url, worker.id) as ws:
            ws.bulk_save_objects(records_to_insert)

        with master_session_ctx() as ms:
            ms.bulk_save_objects(mappings)

        update_worker_stats(worker.id, delta_bytes=total_bytes,
                            delta_records=written)
        log_activity("BULK_WRITE",
                     f"{written} records → {worker.name}",
                     user_id=user["id"], username=user["username"])
        return {"written": written, "worker": worker.name,
                "total_bytes": total_bytes}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/data/query")
async def query_records(
    worker_id : Optional[str] = None,
    collection: Optional[str] = None,
    limit     : int = 20,
    offset    : int = 0,
    user      : dict = Depends(require_auth)
):
    limit = min(limit, 500)
    records_out = []

    try:
        with master_session_ctx() as s:
            if worker_id:
                workers = s.query(WorkerDB).filter_by(id=worker_id,
                                                       is_active=True).all()
            else:
                workers = s.query(WorkerDB).filter_by(is_active=True).all()

        for w in workers:
            try:
                with worker_session_ctx(w.db_url, w.id) as ws:
                    q = ws.query(DataRecord)
                    if collection:
                        q = q.filter_by(collection=collection)
                    recs = q.order_by(DataRecord.created_at.desc()) \
                             .offset(offset).limit(limit).all()
                    for r in recs:
                        records_out.append({
                            "id"         : r.id,
                            "collection" : r.collection,
                            "data"       : r.data,
                            "owner_id"   : r.owner_id,
                            "tags"       : r.tags,
                            "size_bytes" : r.size_bytes,
                            "created_at" : str(r.created_at),
                            "worker_id"  : w.id,
                            "worker_name": w.name,
                        })
            except Exception:
                continue

        return {"records": records_out[:limit], "count": len(records_out)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/data/record/{record_id}")
async def get_record(record_id: str,
                     user: dict = Depends(require_auth)):
    try:
        with master_session_ctx() as s:
            mapping = s.query(DataMapping).filter_by(record_id=record_id).first()
        if not mapping:
            raise HTTPException(status_code=404, detail="Record not found")

        worker = get_worker_by_id(mapping.worker_id)
        if not worker:
            raise HTTPException(status_code=404, detail="Worker not found")

        with worker_session_ctx(worker.db_url, worker.id) as ws:
            rec = ws.query(DataRecord).filter_by(id=record_id).first()
        if not rec:
            raise HTTPException(status_code=404, detail="Record not found in shard")

        return {
            "id"         : rec.id,
            "collection" : rec.collection,
            "data"       : rec.data,
            "tags"       : rec.tags,
            "size_bytes" : rec.size_bytes,
            "created_at" : str(rec.created_at),
            "worker"     : worker.name,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.delete("/api/data/record/{record_id}")
async def delete_record(record_id: str,
                        user: dict = Depends(require_auth)):
    try:
        with master_session_ctx() as s:
            mapping = s.query(DataMapping).filter_by(record_id=record_id).first()
        if not mapping:
            raise HTTPException(status_code=404, detail="Record not found")

        worker = get_worker_by_id(mapping.worker_id)
        if worker:
            try:
                with worker_session_ctx(worker.db_url, worker.id) as ws:
                    rec = ws.query(DataRecord).filter_by(id=record_id).first()
                    if rec:
                        size_b = rec.size_bytes or 0
                        ws.delete(rec)
                update_worker_stats(worker.id,
                                    delta_bytes=-size_b, delta_records=-1)
            except Exception:
                pass

        with master_session_ctx() as ms:
            mp = ms.query(DataMapping).filter_by(record_id=record_id).first()
            if mp:
                ms.delete(mp)

        log_activity("DATA_DELETE", f"Record {record_id}",
                     user_id=user["id"], username=user["username"])
        return {"message": "Deleted", "id": record_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/data/bulk-delete")
async def bulk_delete(body: BulkDeleteRequest,
                      user: dict = Depends(require_auth)):
    deleted = 0
    for record_id in body.record_ids:
        try:
            with master_session_ctx() as s:
                mapping = s.query(DataMapping).filter_by(record_id=record_id).first()
            if not mapping:
                continue
            worker = get_worker_by_id(mapping.worker_id)
            size_b = 0
            if worker:
                try:
                    with worker_session_ctx(worker.db_url, worker.id) as ws:
                        rec = ws.query(DataRecord).filter_by(id=record_id).first()
                        if rec:
                            size_b = rec.size_bytes or 0
                            ws.delete(rec)
                    update_worker_stats(worker.id,
                                        delta_bytes=-size_b, delta_records=-1)
                except Exception:
                    pass
            with master_session_ctx() as ms:
                mp = ms.query(DataMapping).filter_by(record_id=record_id).first()
                if mp:
                    ms.delete(mp)
            deleted += 1
        except Exception:
            continue

    log_activity("BULK_DELETE", f"{deleted} records deleted",
                 user_id=user["id"], username=user["username"])
    return {"deleted": deleted}

# ── Search ────────────────────────────────────────────────────

@app.post("/api/search")
async def smart_search(body: SearchRequest,
                       user: dict = Depends(require_auth)):
    start_t = time.time()
    results = []
    shards_searched = 0

    try:
        with master_session_ctx() as s:
            workers = s.query(WorkerDB).filter_by(is_active=True).all()

        for w in workers:
            try:
                with worker_session_ctx(w.db_url, w.id) as ws:
                    q = ws.query(DataRecord)
                    if body.collection:
                        q = q.filter_by(collection=body.collection)
                    # cast JSON to text for ILIKE search (PostgreSQL)
                    q = q.filter(
                        func.cast(DataRecord.data, Text).ilike(
                            f"%{body.query}%")
                    )
                    recs = q.limit(body.limit).all()
                    for r in recs:
                        results.append({
                            "id"         : r.id,
                            "collection" : r.collection,
                            "data"       : r.data,
                            "tags"       : r.tags or [],
                            "created_at" : str(r.created_at),
                            "worker_id"  : w.id,
                            "worker_name": w.name,
                        })
                    shards_searched += 1
            except Exception:
                continue

        elapsed = round((time.time() - start_t) * 1000, 2)
        return {
            "results"        : results[:body.limit],
            "total"          : len(results),
            "shards_searched": shards_searched,
            "time_ms"        : elapsed,
            "query"          : body.query,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ── File Storage ──────────────────────────────────────────────

class FileUploadRequest(BaseModel):
    filename  : str
    mime_type : Optional[str] = "application/octet-stream"
    data_b64  : str
    collection: str = "files"

@app.post("/api/files/upload")
async def upload_file(body: FileUploadRequest,
                      user: dict = Depends(require_auth)):
    max_mb = int(get_config("max_file_size_mb","5"))
    raw    = base64.b64decode(body.data_b64)
    size_b = len(raw)
    if size_b > max_mb * 1024 * 1024:
        raise HTTPException(status_code=413,
                            detail=f"File exceeds {max_mb} MB limit")

    worker = get_available_worker()
    if not worker:
        raise HTTPException(status_code=503, detail="No available worker DB")

    try:
        file_id = str(uuid.uuid4())
        with worker_session_ctx(worker.db_url, worker.id) as ws:
            ws.add(FileRecord(
                id         = file_id,
                filename   = body.filename,
                mime_type  = body.mime_type,
                data_b64   = body.data_b64,
                owner_id   = user["id"],
                size_bytes = size_b,
                collection = body.collection,
            ))
        update_worker_stats(worker.id, delta_bytes=size_b)
        log_activity("FILE_UPLOAD",
                     f"{body.filename} ({size_b//1024} KB) → {worker.name}",
                     user_id=user["id"], username=user["username"])
        return {"id": file_id, "worker": worker.name,
                "size_bytes": size_b}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/files/list")
async def list_files(user: dict = Depends(require_auth)):
    files_out = []
    try:
        with master_session_ctx() as s:
            workers = s.query(WorkerDB).filter_by(is_active=True).all()

        for w in workers:
            try:
                with worker_session_ctx(w.db_url, w.id) as ws:
                    files = (ws.query(FileRecord)
                               .filter_by(owner_id=user["id"])
                               .order_by(FileRecord.created_at.desc())
                               .all())
                    for f in files:
                        files_out.append({
                            "id"         : f.id,
                            "filename"   : f.filename,
                            "mime_type"  : f.mime_type,
                            "size_bytes" : f.size_bytes,
                            "collection" : f.collection,
                            "created_at" : str(f.created_at),
                            "worker_id"  : w.id,
                        })
            except Exception:
                continue

        return {"files": files_out}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/files/download/{file_id}")
async def download_file(file_id: str,
                        user: dict = Depends(require_auth)):
    try:
        with master_session_ctx() as s:
            workers = s.query(WorkerDB).filter_by(is_active=True).all()

        for w in workers:
            try:
                with worker_session_ctx(w.db_url, w.id) as ws:
                    f = ws.query(FileRecord).filter_by(id=file_id).first()
                    if f:
                        data = base64.b64decode(f.data_b64)
                        return Response(
                            content=data,
                            media_type=f.mime_type or "application/octet-stream",
                            headers={
                                "Content-Disposition":
                                    f'attachment; filename="{f.filename}"'
                            }
                        )
            except Exception:
                continue
        raise HTTPException(status_code=404, detail="File not found")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str,
                      user: dict = Depends(require_auth)):
    try:
        with master_session_ctx() as s:
            workers = s.query(WorkerDB).filter_by(is_active=True).all()
        for w in workers:
            try:
                with worker_session_ctx(w.db_url, w.id) as ws:
                    f = ws.query(FileRecord).filter_by(id=file_id).first()
                    if f:
                        size_b = f.size_bytes or 0
                        ws.delete(f)
                        update_worker_stats(w.id, delta_bytes=-size_b)
                        return {"message":"Deleted","id":file_id}
            except Exception:
                continue
        raise HTTPException(status_code=404, detail="File not found")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ── User Self-Service ─────────────────────────────────────────

@app.post("/api/user/generate-api-key")
async def generate_api_key(user: dict = Depends(require_auth)):
    try:
        new_key = secrets.token_hex(32)
        with master_session_ctx() as s:
            u = s.query(User).filter_by(id=user["id"]).first()
            if u:
                u.api_key = new_key
        log_activity("API_KEY_GEN", "New API key generated",
                     user_id=user["id"], username=user["username"])
        return {"api_key": new_key}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

class PwChangeRequest(BaseModel):
    current_password: str
    new_password    : str

@app.post("/api/user/change-password")
async def change_password(body: PwChangeRequest,
                          user: dict = Depends(require_auth)):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400,
                            detail="Password must be 6+ characters")
    try:
        with master_session_ctx() as s:
            u = s.query(User).filter_by(id=user["id"]).first()
            if not u:
                raise HTTPException(status_code=404, detail="User not found")
            if not verify_password(body.current_password, u.password_hash):
                raise HTTPException(status_code=401,
                                    detail="Current password incorrect")
            u.password_hash = hash_password(body.new_password)
        log_activity("PW_CHANGE", "Password changed",
                     user_id=user["id"], username=user["username"])
        return {"message": "Password updated"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

class ThemeRequest(BaseModel):
    theme: str

@app.post("/api/user/theme")
async def set_theme(body: ThemeRequest,
                    user: dict = Depends(require_auth)):
    if body.theme not in ("dark","light"):
        raise HTTPException(status_code=400,
                            detail="Theme must be 'dark' or 'light'")
    try:
        with master_session_ctx() as s:
            u = s.query(User).filter_by(id=user["id"]).first()
            if u:
                u.theme = body.theme
        return {"theme": body.theme}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ── Admin: Workers ────────────────────────────────────────────

@app.post("/api/admin/workers")
async def add_worker(body: WorkerAddRequest,
                     user: dict = Depends(require_admin)):
    try:
        # test connection first
        test_eng = _make_engine(body.db_url, pool=False)
        with test_eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        test_eng.dispose()
    except Exception as exc:
        raise HTTPException(status_code=400,
                            detail=f"Cannot connect to DB: {exc}")
    try:
        with master_session_ctx() as s:
            if s.query(WorkerDB).filter_by(name=body.name).first():
                raise HTTPException(status_code=409,
                                    detail="Worker name already exists")
            w = WorkerDB(name=body.name, db_url=body.db_url)
            s.add(w)
        # initialise worker tables
        eng = _make_engine(body.db_url)
        WorkerBase.metadata.create_all(eng)
        log_activity("WORKER_ADD", f"Worker '{body.name}' added",
                     user_id=user["id"], username=user["username"])
        return {"message":"Worker added","name":body.name}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/admin/workers/{worker_id}/toggle")
async def toggle_worker(worker_id: str,
                        body: dict,
                        user: dict = Depends(require_admin)):
    try:
        with master_session_ctx() as s:
            w = s.query(WorkerDB).filter_by(id=worker_id).first()
            if not w:
                raise HTTPException(status_code=404, detail="Worker not found")
            w.is_active = body.get("is_active", not w.is_active)
        return {"message":"Updated"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.delete("/api/admin/workers/{worker_id}")
async def remove_worker(worker_id: str,
                        user: dict = Depends(require_admin)):
    try:
        with master_session_ctx() as s:
            w = s.query(WorkerDB).filter_by(id=worker_id).first()
            if not w:
                raise HTTPException(status_code=404, detail="Worker not found")
            s.delete(w)
        log_activity("WORKER_REMOVE", f"Worker {worker_id} removed",
                     user_id=user["id"], username=user["username"])
        return {"message":"Removed"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/admin/ping-workers")
async def ping_workers_api(user: dict = Depends(require_admin)):
    thread = threading.Thread(target=anti_sleep_ping, daemon=True)
    thread.start()
    return {"message":"Ping initiated for all workers"}

# ── Admin: Users ──────────────────────────────────────────────

@app.post("/api/admin/users/{user_id}/role")
async def change_user_role(user_id: str, body: dict,
                           user: dict = Depends(require_admin)):
    role = body.get("role","user")
    if role not in ("user","admin"):
        raise HTTPException(status_code=400, detail="Invalid role")
    try:
        with master_session_ctx() as s:
            u = s.query(User).filter_by(id=user_id).first()
            if not u:
                raise HTTPException(status_code=404, detail="User not found")
            if u.role == "owner":
                raise HTTPException(status_code=403,
                                    detail="Cannot change owner role")
            u.role = role
        log_activity("ROLE_CHANGE", f"User {user_id} → {role}",
                     user_id=user["id"], username=user["username"])
        return {"message":"Role updated"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/admin/users/{user_id}/toggle")
async def toggle_user(user_id: str, body: dict,
                      user: dict = Depends(require_admin)):
    try:
        with master_session_ctx() as s:
            u = s.query(User).filter_by(id=user_id).first()
            if not u:
                raise HTTPException(status_code=404, detail="User not found")
            if u.role == "owner":
                raise HTTPException(status_code=403,
                                    detail="Cannot disable owner")
            u.is_active = body.get("is_active", not u.is_active)
        return {"message":"User updated"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: str,
                      user: dict = Depends(require_admin)):
    try:
        with master_session_ctx() as s:
            u = s.query(User).filter_by(id=user_id).first()
            if not u:
                raise HTTPException(status_code=404, detail="User not found")
            if u.role == "owner":
                raise HTTPException(status_code=403,
                                    detail="Cannot delete owner")
            s.delete(u)
        log_activity("USER_DELETE", f"User {user_id} deleted",
                     user_id=user["id"], username=user["username"])
        return {"message":"Deleted"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ── Admin: Config ─────────────────────────────────────────────

@app.post("/api/admin/config")
async def update_config(body: ConfigUpdateRequest,
                        user: dict = Depends(require_owner)):
    try:
        with master_session_ctx() as s:
            for k, v in body.configs.items():
                row = s.query(SystemConfig).filter_by(key=k).first()
                if row:
                    row.value = v
                else:
                    s.add(SystemConfig(key=k, value=v))
        log_activity("CONFIG_UPDATE",
                     f"Keys: {list(body.configs.keys())}",
                     user_id=user["id"], username=user["username"])
        return {"message":"Config updated","keys":list(body.configs.keys())}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ── Admin: Transactions ───────────────────────────────────────

@app.post("/api/admin/transactions")
async def create_transaction(body: TransactionRequest,
                             user: dict = Depends(require_admin)):
    if body.tx_type not in ("credit","debit"):
        raise HTTPException(status_code=400, detail="tx_type must be credit or debit")
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    try:
        with master_session_ctx() as s:
            u = s.query(User).filter_by(id=body.user_id).first()
            if not u:
                raise HTTPException(status_code=404, detail="User not found")
            if body.tx_type == "debit" and u.balance < body.amount:
                raise HTTPException(status_code=400,
                                    detail="Insufficient balance")
            if body.tx_type == "credit":
                u.balance += body.amount
            else:
                u.balance -= body.amount
            bal = round(u.balance, 2)
            s.add(Transaction(
                user_id      = body.user_id,
                amount       = body.amount,
                tx_type      = body.tx_type,
                description  = body.description,
                balance_after= bal,
            ))
        log_activity("TRANSACTION",
                     f"{body.tx_type} ${body.amount} for {body.user_id}",
                     user_id=user["id"], username=user["username"])
        return {"message":"Transaction completed","balance_after":bal}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ── Admin: Logs ───────────────────────────────────────────────

@app.delete("/api/admin/logs/clear")
async def clear_logs(user: dict = Depends(require_admin)):
    try:
        with master_session_ctx() as s:
            s.query(ActivityLog).delete()
        return {"message":"Logs cleared"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ── Admin: Rebalance ──────────────────────────────────────────

@app.post("/api/admin/rebalance")
async def rebalance(body: RebalanceRequest,
                    user: dict = Depends(require_admin)):
    target_worker = get_worker_by_id(body.target_worker_id)
    if not target_worker or not target_worker.is_active:
        raise HTTPException(status_code=404,
                            detail="Target worker not found or inactive")
    moved = 0

    for record_id in body.record_ids:
        try:
            with master_session_ctx() as s:
                mapping = s.query(DataMapping).filter_by(record_id=record_id).first()
            if not mapping or mapping.worker_id == body.target_worker_id:
                continue

            src_worker = get_worker_by_id(mapping.worker_id)
            if not src_worker:
                continue

            # Fetch record from source
            rec_data = None
            size_b   = 0
            with worker_session_ctx(src_worker.db_url, src_worker.id) as ws:
                rec = ws.query(DataRecord).filter_by(id=record_id).first()
                if rec:
                    rec_data   = rec.data
                    size_b     = rec.size_bytes or 0
                    collection = rec.collection
                    owner_id   = rec.owner_id
                    tags       = rec.tags or []
                    ws.delete(rec)

            if rec_data is None:
                continue

            # Write to target
            with worker_session_ctx(target_worker.db_url,
                                    target_worker.id) as ws:
                ws.add(DataRecord(
                    id         = record_id,
                    collection = collection,
                    data       = rec_data,
                    owner_id   = owner_id,
                    size_bytes = size_b,
                    tags       = tags,
                ))

            # Update mapping
            with master_session_ctx() as s:
                mp = s.query(DataMapping).filter_by(record_id=record_id).first()
                if mp:
                    mp.worker_id = body.target_worker_id

            update_worker_stats(src_worker.id,
                                delta_bytes=-size_b, delta_records=-1)
            update_worker_stats(target_worker.id,
                                delta_bytes=size_b,  delta_records=1)
            moved += 1
        except Exception:
            continue

    log_activity("REBALANCE",
                 f"Moved {moved} records → {target_worker.name}",
                 user_id=user["id"], username=user["username"])
    return {"moved": moved, "target": target_worker.name}

# ── Schemas ───────────────────────────────────────────────────

@app.post("/api/schemas")
async def create_schema(body: SchemaCreateRequest,
                        user: dict = Depends(require_owner)):
    try:
        with master_session_ctx() as s:
            if s.query(JsonSchema).filter_by(name=body.name).first():
                raise HTTPException(status_code=409,
                                    detail="Schema name already exists")
            s.add(JsonSchema(
                name       = body.name,
                schema_def = body.schema_def,
                collection = body.collection,
                created_by = user["id"],
            ))
        return {"message":"Schema created","name":body.name}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.delete("/api/schemas/{schema_id}")
async def delete_schema(schema_id: str,
                        user: dict = Depends(require_owner)):
    try:
        with master_session_ctx() as s:
            sc = s.query(JsonSchema).filter_by(id=schema_id).first()
            if not sc:
                raise HTTPException(status_code=404, detail="Schema not found")
            s.delete(sc)
        return {"message":"Schema deleted"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ── Notifications ─────────────────────────────────────────────

@app.post("/api/notifications/read")
async def mark_notifications_read(body: NotificationMarkRequest,
                                  user: dict = Depends(require_auth)):
    try:
        with master_session_ctx() as s:
            for nid in body.notification_ids:
                n = s.query(Notification).filter_by(id=nid).first()
                if n:
                    n.is_read = True
        return {"message":"Marked read"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/notifications/read-all")
async def mark_all_read(user: dict = Depends(require_auth)):
    try:
        with master_session_ctx() as s:
            (s.query(Notification)
             .filter(
                 or_(Notification.user_id==user["id"],
                     Notification.user_id.is_(None)),
                 Notification.is_read==False
             ).update({"is_read": True}))
        return {"message":"All marked read"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ── Export / Backup ───────────────────────────────────────────

@app.get("/api/export/all")
async def export_all(user: dict = Depends(require_admin)):
    """Export all data records from all active shards as JSON."""
    try:
        with master_session_ctx() as s:
            workers = s.query(WorkerDB).filter_by(is_active=True).all()

        export_data = {
            "export_time": datetime.datetime.utcnow().isoformat(),
            "version"    : VERSION,
            "shards"     : [],
        }

        for w in workers:
            shard_data: Dict[str, Any] = {
                "worker_id"  : w.id,
                "worker_name": w.name,
                "records"    : [],
                "files"      : [],
            }
            try:
                with worker_session_ctx(w.db_url, w.id) as ws:
                    recs = ws.query(DataRecord).all()
                    for r in recs:
                        shard_data["records"].append({
                            "id"        : r.id,
                            "collection": r.collection,
                            "data"      : r.data,
                            "tags"      : r.tags,
                            "created_at": str(r.created_at),
                        })
                    files = ws.query(FileRecord).all()
                    for f in files:
                        shard_data["files"].append({
                            "id"       : f.id,
                            "filename" : f.filename,
                            "mime_type": f.mime_type,
                            "size_bytes": f.size_bytes,
                        })
            except Exception:
                pass
            export_data["shards"].append(shard_data)

        content = json.dumps(export_data, indent=2, default=str)
        fname   = f"ruhi-vig-export-{datetime.date.today()}.json"
        log_activity("EXPORT", "Full data export",
                     user_id=user["id"], username=user["username"])
        return Response(
            content    = content,
            media_type = "application/json",
            headers    = {"Content-Disposition": f'attachment; filename="{fname}"'}
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/export/worker/{worker_id}")
async def export_worker(worker_id: str,
                        user: dict = Depends(require_admin)):
    worker = get_worker_by_id(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    try:
        with worker_session_ctx(worker.db_url, worker.id) as ws:
            recs  = ws.query(DataRecord).all()
            files = ws.query(FileRecord).all()

        data = {
            "worker"     : worker.name,
            "export_time": datetime.datetime.utcnow().isoformat(),
            "records"    : [{"id":r.id,"collection":r.collection,
                              "data":r.data,"created_at":str(r.created_at)}
                             for r in recs],
            "files"      : [{"id":f.id,"filename":f.filename,
                              "size_bytes":f.size_bytes}
                             for f in files],
        }
        fname = f"shard-{worker.name}-{datetime.date.today()}.json"
        return Response(
            content    = json.dumps(data, indent=2, default=str),
            media_type = "application/json",
            headers    = {"Content-Disposition": f'attachment; filename="{fname}"'}
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ════════════════════════════════════════════════════════════
# STARTUP / SHUTDOWN
# ════════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup():
    log.info(f"Starting {APP_NAME} v{VERSION}…")
    if not MASTER_DB_URL:
        log.warning("⚠  DATABASE_URL is not set! "
                    "Set it as an env variable.")
        return
    try:
        init_master_db()
        start_scheduler()
        log_activity("SYSTEM_START",
                     f"{APP_NAME} v{VERSION} started successfully",
                     username="system", level="info")
        log.info(f"✅ {APP_NAME} v{VERSION} is ready.")
    except Exception as exc:
        log.error(f"❌ Startup error: {exc}")


@app.on_event("shutdown")
async def shutdown():
    """Graceful shutdown: stop scheduler, dispose all DB engines."""
    log.info(f"Shutting down {APP_NAME} v{VERSION}…")
    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
            log.info("Scheduler stopped.")
    except Exception as exc:
        log.warning(f"Scheduler shutdown warning: {exc}")

    # Dispose master engine
    global _master_engine
    if _master_engine is not None:
        try:
            _master_engine.dispose()
            log.info("Master DB engine disposed.")
        except Exception as exc:
            log.warning(f"Master engine dispose warning: {exc}")

    # Dispose all worker engines
    for wid, eng in list(_worker_engines.items()):
        try:
            eng.dispose()
        except Exception:
            pass
    log.info("All worker engines disposed.")
    log.info(f"👋 {APP_NAME} v{VERSION} shutdown complete.")


# ════════════════════════════════════════════════════════════
# SECTION 10: ENTRY POINT
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    reload = os.getenv("RELOAD", "false").lower() == "true"

    log.info(f"Launching {APP_NAME} v{VERSION} on {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
        access_log=True,
    )
                     
