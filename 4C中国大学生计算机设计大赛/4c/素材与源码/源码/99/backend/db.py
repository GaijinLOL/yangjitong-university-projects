from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Any, Iterable

import pymysql

from config import Config


@dataclass(frozen=True)
class MySQLDsn:
    host: str
    port: int
    user: str
    password: str
    database: str


DSN = MySQLDsn(
    host=Config.MYSQL_HOST,
    port=Config.MYSQL_PORT,
    user=Config.MYSQL_USER,
    password=Config.MYSQL_PASSWORD,
    database=Config.MYSQL_DATABASE,
)


def get_conn():
    return pymysql.connect(
        host=DSN.host,
        port=DSN.port,
        user=DSN.user,
        password=DSN.password,
        database=DSN.database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


@contextlib.contextmanager
def tx():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def exec_many(conn, sql: str, rows: Iterable[dict[str, Any]]):
    with conn.cursor() as cur:
        cur.executemany(sql, list(rows))


def exec_one(conn, sql: str, params: dict[str, Any] | None = None) -> int:
    with conn.cursor() as cur:
        return cur.execute(sql, params or {})


def fetch_all(conn, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(sql, params or {})
        return list(cur.fetchall())


def fetch_one(conn, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(sql, params or {})
        return cur.fetchone()

