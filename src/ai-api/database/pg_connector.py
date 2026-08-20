"""PostgreSQL 连接与只读查询封装。"""

from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

import psycopg2


class PgConnector:
    """负责连接 PostgreSQL、读取表结构、执行只读查询。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @contextmanager
    def _connection(self, read_only: bool = True):
        """每个请求使用独立连接；默认开启只读事务，用后回滚并关闭。"""
        conn = psycopg2.connect(
            host=self.config.get("host", "localhost"),
            port=self.config.get("port", 5432),
            database=self.config.get("database"),
            user=self.config.get("user"),
            password=self.config.get("password"),
            connect_timeout=self.config.get("connect_timeout", 10),
        )
        try:
            conn.autocommit = False
            if read_only:
                cur = conn.cursor()
                cur.execute("SET TRANSACTION READ ONLY")
                cur.close()
            yield conn
            conn.rollback()
        finally:
            conn.close()

    def test_connection(self) -> Tuple[bool, str]:
        """探测数据库连通性。"""
        try:
            with self._connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT current_database(), version()")
                row = cur.fetchone()
            return True, f"{row[0]} / {row[1][:60]}"
        except Exception as e:  # noqa: BLE001
            return False, str(e)

    def get_columns(self, table: str, schema: str = "public") -> List[Dict[str, str]]:
        """读取单张表的字段信息。"""
        sql = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (schema, table))
            cols = [
                {
                    "column": r[0],
                    "type": r[1],
                    "nullable": r[2],
                    "default": r[3],
                }
                for r in cur.fetchall()
            ]
        return cols

    def get_tables_schema(self, tables: List[str]) -> Dict[str, List[Dict[str, str]]]:
        """读取多张表的字段结构。"""
        result: Dict[str, List[Dict[str, str]]] = {}
        for table in tables:
            result[table] = self.get_columns(table)
        return result

    @staticmethod
    def build_schema_description(schema_dict: Dict[str, List[Dict[str, str]]]) -> str:
        """把表结构转成给 AI 看的文本描述。"""
        lines: List[str] = []
        for table, cols in schema_dict.items():
            lines.append(f"表 {table}:")
            if not cols:
                lines.append("  (无字段，或表不存在)")
                continue
            for c in cols:
                nullable = "可空" if c["nullable"] == "YES" else "非空"
                default = f", 默认 {c['default']}" if c.get("default") else ""
                lines.append(f"  - {c['column']} ({c['type']}, {nullable}{default})")
        return "\n".join(lines)

    def execute_read_query(
        self,
        sql: str,
        timeout: int = 30,
        max_rows: int = 100,
    ) -> Tuple[List[str], List[List[Any]], bool]:
        """执行只读 SQL，返回 (字段名, 数据行, 是否被截断)。"""
        with self._connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(f"SET statement_timeout = {int(timeout) * 1000}")
            except Exception:  # noqa: BLE001
                pass
            cur.execute(sql)
            columns = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchmany(max_rows + 1)
            truncated = len(rows) > max_rows
            rows = rows[:max_rows]
        return columns, rows, truncated