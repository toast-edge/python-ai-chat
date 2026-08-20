"""SQL 安全校验：只读、表白名单、LIMIT 限制。

注意：这里是「第二道防线」。第一道、也是最可靠的防线，是使用只有
SELECT 权限的数据库账号连接 PostgreSQL（config.json -> postgres.user）。
"""

import re
from typing import Any, List, Optional, Set, Tuple

# 整词匹配的禁止关键字（出现即拒绝），防止写操作/危险操作
_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|"
    r"COPY|CALL|DO|VACUUM|ANALYZE|MERGE|EXECUTE|SET|BEGIN|COMMIT|ROLLBACK|"
    r"REINDEX|CLUSTER|RESET|LOCK|REFRESH|DISCARD|LISTEN|NOTIFY|UNLISTEN|"
    r"DECLARE|PREPARE|DEALLOCATE|TRANSACTION|SAVEPOINT|RELEASE)\b",
    re.IGNORECASE,
)

_HAS_LIMIT = re.compile(r"\bLIMIT\b", re.IGNORECASE)


def _strip_comments(sql: str) -> str:
    """去掉 SQL 注释，避免注释里夹带内容绕过校验。"""
    sql = re.sub(r"--[^\n]*", "", sql)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.S)
    return sql


def _clean_identifier(name: str) -> str:
    """去掉引号与 schema 前缀，只保留表名本体。"""
    name = name.strip().replace('"', "").replace("`", "")
    if "." in name:
        name = name.split(".")[-1]
    return name


def extract_tables(sql: str) -> Set[str]:
    """从 SQL 中粗略提取 FROM/JOIN 引用的表名（用于白名单校验）。"""
    tables: Set[str] = set()
    sql = _strip_comments(sql)

    # FROM 之后的表列表，直到遇到子句关键字 / JOIN / 分号 / 右括号
    from_m = re.search(
        r"\bFROM\s+(?P<seg>.+?)(?=\b(?:WHERE|GROUP|ORDER|HAVING|LIMIT|OFFSET|UNION|JOIN)\b|[;)]|$)",
        sql,
        re.IGNORECASE,
    )
    if from_m:
        _collect_segment(from_m.group("seg"), tables)

    # 各种 JOIN 后的表
    for m in re.finditer(
        r"\b(?:INNER\s+|LEFT\s+(?:OUTER\s+)?|RIGHT\s+(?:OUTER\s+)?|"
        r"FULL\s+(?:OUTER\s+)?|CROSS\s+)?JOIN\s+([^\s,;()]+)",
        sql,
        re.IGNORECASE,
    ):
        tables.add(_clean_identifier(m.group(1)))

    return {t for t in tables if t}


def _collect_segment(segment: str, tables: Set[str]) -> None:
    """解析 FROM 段：按逗号拆分，取每一项的第一个标识符作为表名。"""
    for part in segment.split(","):
        m = re.search(r'([A-Za-z_][\w.]*|"[^"]+"|`[^`]+`)', part)
        if m:
            tables.add(_clean_identifier(m.group(1)))


def validate(
    sql: str,
    allowed_tables: Optional[List[str]] = None,
    max_rows: int = 100,
) -> Tuple[bool, Any]:
    """校验 SQL 是否只读且在允许的表范围内。

    返回 (是否合法, 处理后的 SQL 或错误信息字符串)。
    """
    sql = (_strip_comments(sql) or "").strip()
    if not sql:
        return False, "SQL 为空"

    clean = sql.rstrip().rstrip(";").rstrip()
    if ";" in clean:
        return False, "不允许执行多条语句"

    m = re.match(r"\s*([A-Za-z]+)", clean)
    first_word = m.group(1).upper() if m else ""
    if first_word != "SELECT":
        return False, "仅允许 SELECT 只读查询"

    if _FORBIDDEN_KEYWORDS.search(clean):
        return False, "检测到非只读或危险关键字"

    if allowed_tables:
        used = extract_tables(clean)
        unknown = used - set(allowed_tables)
        if unknown:
            return False, f"访问了未授权表: {', '.join(sorted(unknown))}"

    if not _HAS_LIMIT.search(clean):
        clean += f" LIMIT {int(max_rows)}"

    return True, clean