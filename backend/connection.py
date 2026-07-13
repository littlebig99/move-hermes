"""Move Hermes — 数据库连接管理（线程安全）"""
import sqlite3
import threading
from pathlib import Path
from contextlib import contextmanager
from typing import Optional


_db_path_lock = threading.Lock()
_DB_PATH: Optional[str] = None


def get_db_path() -> str:
    """获取当前数据库路径（线程安全）"""
    global _DB_PATH
    with _db_path_lock:
        return _DB_PATH or ""


def set_db_path(path: str):
    """设置数据库路径（线程安全）"""
    global _DB_PATH
    with _db_path_lock:
        _DB_PATH = path


def _resolve_db_path(db_path: Optional[str] = None) -> str:
    """解析数据库路径"""
    global _DB_PATH
    with _db_path_lock:
        if db_path is not None:
            _DB_PATH = db_path
        elif _DB_PATH is None:
            script_dir = Path(__file__).parent.parent.parent
            data_dir = script_dir / "data"
            data_dir.mkdir(exist_ok=True)
            _DB_PATH = str(data_dir / "move_hermes.db")
        return _DB_PATH


@contextmanager
def get_connection(db_path: Optional[str] = None):
    """获取数据库连接的上下文管理器"""
    path = _resolve_db_path(db_path)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
