from __future__ import annotations

import re

from db import exec_one, fetch_one, tx


def _col_exists(conn, table: str, col: str) -> bool:
    row = fetch_one(conn, f"SHOW COLUMNS FROM `{table}` LIKE %(col)s", {"col": col})
    return bool(row)

def _safe_add_column(conn, table: str, col: str, ddl: str) -> bool:
    """
    ddl example: "ADD COLUMN area VARCHAR(32) NULL"
    """
    if _col_exists(conn, table, col):
        return False
    exec_one(conn, f"ALTER TABLE `{table}` {ddl}")
    return True


def ensure_schema() -> dict[str, int]:
    """
    轻量级“自愈迁移”：当用户用旧 SQL 初始化过库时，自动补齐必要字段，避免运行时报 1054。
    只做 ADD COLUMN（不删不改），风险低，适合比赛本地交付。
    """
    changes = 0
    with tx() as conn:
        # company_basic: 兼容“用户曾经用不同脚本建表”的情况
        # 不使用 AFTER（避免依赖列不存在导致迁移整体失败）
        for col, ddl in [
            ("symbol", "ADD COLUMN symbol VARCHAR(16) NULL"),
            ("name", "ADD COLUMN name VARCHAR(64) NULL"),
            ("area", "ADD COLUMN area VARCHAR(32) NULL"),
            ("industry", "ADD COLUMN industry VARCHAR(64) NULL"),
            ("fullname", "ADD COLUMN fullname VARCHAR(128) NULL"),
            ("enname", "ADD COLUMN enname VARCHAR(128) NULL"),
            ("cnspell", "ADD COLUMN cnspell VARCHAR(64) NULL"),
            ("market", "ADD COLUMN market VARCHAR(32) NULL"),
            ("exchange", "ADD COLUMN exchange VARCHAR(16) NULL"),
            ("list_status", "ADD COLUMN list_status VARCHAR(8) NULL"),
            ("list_date", "ADD COLUMN list_date VARCHAR(16) NULL"),
            ("delist_date", "ADD COLUMN delist_date VARCHAR(16) NULL"),
            ("is_hs", "ADD COLUMN is_hs VARCHAR(8) NULL"),
            ("updated_at", "ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ]:
            if _safe_add_column(conn, "company_basic", col, ddl):
                changes += 1

    return {"changes": changes}

