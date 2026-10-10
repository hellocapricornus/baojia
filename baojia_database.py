"""baojia 报价机器人 - 数据库模块（SQLite）

包含 3 张表，表名与字段名全部使用 baojia 前缀：
- baojia_users         ：机器人用户（管理员 / 操作员）
- baojia_quotes        ：报价表（同群组+国家+料性+账户类别+结算方式+类型 唯一一条）
- baojia_quote_history ：报价变更历史（覆盖更新时旧值留档）
"""

import contextlib
import sqlite3
from pathlib import Path

import baojia_config

BAOJIA_DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS baojia_users (
        baojia_user_id    INTEGER PRIMARY KEY,
        baojia_full_name  TEXT NOT NULL DEFAULT '',
        baojia_role       TEXT NOT NULL DEFAULT 'operator',
        baojia_is_active  INTEGER NOT NULL DEFAULT 1,
        baojia_created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS baojia_quotes (
        baojia_quote_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        baojia_type          TEXT NOT NULL,
        baojia_country       TEXT NOT NULL,
        baojia_material      TEXT NOT NULL,
        baojia_account_type  TEXT NOT NULL,
        baojia_settle_method TEXT NOT NULL,
        baojia_fee_rate      REAL NOT NULL,
        baojia_rate          REAL NOT NULL,
        baojia_single_fee    REAL NOT NULL DEFAULT 0,
        baojia_group_id      INTEGER NOT NULL,
        baojia_group_name    TEXT NOT NULL DEFAULT '',
        baojia_parent_group  TEXT NOT NULL DEFAULT '',
        baojia_sales         TEXT NOT NULL DEFAULT '',
        baojia_remark        TEXT NOT NULL DEFAULT '',
        baojia_user_id       INTEGER NOT NULL,
        baojia_created_at    TEXT NOT NULL,
        baojia_updated_at    TEXT NOT NULL
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS baojia_idx_quote_unique
    ON baojia_quotes(
        baojia_group_id, baojia_country, baojia_material,
        baojia_account_type, baojia_settle_method, baojia_type
    )
    """,
    "CREATE INDEX IF NOT EXISTS baojia_idx_quote_country ON baojia_quotes(baojia_country)",
    "CREATE INDEX IF NOT EXISTS baojia_idx_quote_group ON baojia_quotes(baojia_group_id)",
    """
    CREATE TABLE IF NOT EXISTS baojia_quote_history (
        baojia_history_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        baojia_quote_id      INTEGER NOT NULL,
        baojia_action        TEXT NOT NULL,
        baojia_type          TEXT NOT NULL,
        baojia_country       TEXT NOT NULL,
        baojia_material      TEXT NOT NULL,
        baojia_account_type  TEXT NOT NULL,
        baojia_settle_method TEXT NOT NULL,
        baojia_fee_rate      REAL NOT NULL,
        baojia_rate          REAL NOT NULL,
        baojia_single_fee    REAL NOT NULL DEFAULT 0,
        baojia_group_id      INTEGER NOT NULL,
        baojia_group_name    TEXT NOT NULL DEFAULT '',
        baojia_parent_group  TEXT NOT NULL DEFAULT '',
        baojia_sales         TEXT NOT NULL DEFAULT '',
        baojia_remark        TEXT NOT NULL DEFAULT '',
        baojia_changed_by    INTEGER NOT NULL,
        baojia_changed_at    TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS baojia_idx_history_group ON baojia_quote_history(baojia_group_id, baojia_changed_at)",
    "CREATE INDEX IF NOT EXISTS baojia_idx_history_quote ON baojia_quote_history(baojia_quote_id, baojia_changed_at)",
]


def baojia_get_connection():
    """创建一个 SQLite 连接。"""
    baojia_db_path = Path(baojia_config.baojia_DB_PATH)
    baojia_db_path.parent.mkdir(parents=True, exist_ok=True)
    baojia_conn = sqlite3.connect(str(baojia_db_path))
    baojia_conn.row_factory = sqlite3.Row
    baojia_conn.execute("PRAGMA foreign_keys = ON")
    return baojia_conn


def baojia_init_db():
    """建表并执行增量迁移，幂等可重复执行。

    CREATE TABLE IF NOT EXISTS 不会给已存在的旧表补列，
    因此新增字段时必须在此用 PRAGMA + ALTER TABLE ADD COLUMN 做增量升级，
    保证旧数据库文件无需删除即可平滑升级。
    """
    with contextlib.closing(baojia_get_connection()) as baojia_conn:
        with baojia_conn:
            for baojia_sql in BAOJIA_DDL_STATEMENTS:
                baojia_conn.execute(baojia_sql)
            baojia_run_migrations(baojia_conn)


# 增量迁移清单：(表名, 列名, 列定义)
# 新增字段时在此追加一行即可，旧库启动时自动补列，已存在则跳过。
BAOJIA_MIGRATION_COLUMNS = [
    ("baojia_quotes", "baojia_parent_group", "TEXT NOT NULL DEFAULT ''"),
    ("baojia_quote_history", "baojia_parent_group", "TEXT NOT NULL DEFAULT ''"),
    ("baojia_quotes", "baojia_remark", "TEXT NOT NULL DEFAULT ''"),
    ("baojia_quote_history", "baojia_remark", "TEXT NOT NULL DEFAULT ''"),
]


def baojia_run_migrations(baojia_conn):
    """检查每张表的列，缺少则 ALTER TABLE ADD COLUMN 补上。"""
    for baojia_table, baojia_column, baojia_column_def in BAOJIA_MIGRATION_COLUMNS:
        baojia_existing = {
            baojia_row[1]
            for baojia_row in baojia_conn.execute(f"PRAGMA table_info({baojia_table})")
        }
        if baojia_column not in baojia_existing:
            baojia_conn.execute(
                f"ALTER TABLE {baojia_table} ADD COLUMN {baojia_column} {baojia_column_def}"
            )


def baojia_execute(baojia_sql, baojia_params=()):
    """执行单条写操作，返回 lastrowid。"""
    with contextlib.closing(baojia_get_connection()) as baojia_conn:
        with baojia_conn:
            baojia_cur = baojia_conn.execute(baojia_sql, baojia_params)
            return baojia_cur.lastrowid


def baojia_query(baojia_sql, baojia_params=()):
    """查询多行，返回 dict 列表。"""
    with contextlib.closing(baojia_get_connection()) as baojia_conn:
        baojia_rows = baojia_conn.execute(baojia_sql, baojia_params).fetchall()
        return [dict(baojia_row) for baojia_row in baojia_rows]


def baojia_query_one(baojia_sql, baojia_params=()):
    """查询单行，返回 dict 或 None。"""
    with contextlib.closing(baojia_get_connection()) as baojia_conn:
        baojia_row = baojia_conn.execute(baojia_sql, baojia_params).fetchone()
        return dict(baojia_row) if baojia_row else None
