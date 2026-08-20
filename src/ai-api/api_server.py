"""自然语言查库服务（FastAPI）。

用法：
    cd src/ai-api
    uvicorn api_server:app --host 0.0.0.0 --port 8000

然后访问：
    - API 文档：http://127.0.0.1:8000/docs
    - 健康检查：GET /health
    - 表结构：  GET /schema
    - 自然语言查询：POST /query  {"question": "..."}
"""

import json
import os
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from database.pg_connector import PgConnector
from database.sql_guard import validate
from text_to_sql import TextToSQL

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")


def load_config() -> Dict[str, Any]:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


config = load_config()
dql_config = config.get("database_query", {})
allowed_tables = [t.strip() for t in dql_config.get("tables", []) if t and t.strip()]
max_rows = int(dql_config.get("max_rows", 100))
timeout = int(dql_config.get("query_timeout_seconds", 30))

pg = PgConnector(config.get("postgres", {}))
sql_engine = TextToSQL(config.get("qwen", {})) if dql_config.get("enabled", True) else None

app = FastAPI(
    title="自然语言查库服务",
    description="通过自然语言查询 PostgreSQL 数据（只读）",
    version="1.0.0",
)


class QueryRequest(BaseModel):
    question: str


@app.get("/")
def index():
    return {
        "name": "自然语言查库服务",
        "docs": "/docs",
        "endpoints": ["/health", "/schema", "/query"],
    }


@app.get("/health")
def health():
    db_ok, db_msg = pg.test_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database_ok": db_ok,
        "database_message": db_msg,
        "ai_enabled": sql_engine is not None,
        "allowed_tables": allowed_tables,
    }


@app.get("/schema")
def schema():
    if not allowed_tables:
        return {
            "tables": {},
            "description": "未配置表清单，请在 config.json -> database_query.tables 中填写",
        }
    schema_dict = pg.get_tables_schema(allowed_tables)
    return {
        "tables": schema_dict,
        "description": pg.build_schema_description(schema_dict),
    }


@app.post("/query")
def query(req: QueryRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question 不能为空")
    if sql_engine is None:
        raise HTTPException(status_code=503, detail="AI 服务未启用")
    if not allowed_tables:
        raise HTTPException(status_code=400, detail="未配置允许查询的表清单 database_query.tables")

    # 1. 读取表结构
    try:
        schema_dict = pg.get_tables_schema(allowed_tables)
        schema_desc = pg.build_schema_description(schema_dict)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取表结构失败: {e}")

    # 2. AI 生成 SQL
    try:
        raw_sql = sql_engine.generate_sql(question, schema_desc)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"生成 SQL 失败: {e}")

    # 3. 安全校验
    ok, result = validate(raw_sql, allowed_tables, max_rows)
    if not ok:
        return {"question": question, "sql": raw_sql, "error": result}

    # 4. 执行查询
    try:
        columns, rows, truncated = pg.execute_read_query(result, timeout, max_rows)
    except Exception as e:  # noqa: BLE001
        return {"question": question, "sql": result, "error": f"执行查询失败: {e}"}

    # 5. AI 总结（失败不影响返回数据）
    summary = None
    try:
        summary = sql_engine.summarize(question, result, columns, rows)
    except Exception:  # noqa: BLE001
        summary = None

    return {
        "question": question,
        "sql": result,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "truncated": truncated,
        "summary": summary,
    }