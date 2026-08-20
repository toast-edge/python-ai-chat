"""用 Qwen（OpenAI 兼容接口）生成 SQL 与自然语言总结。"""

import re
from typing import Any, Dict, List

from openai import OpenAI


class TextToSQL:
    """调用大模型完成「自然语言 -> SQL」以及「查询结果 -> 总结」。"""

    def __init__(self, ai_config: Dict[str, Any]):
        kwargs = {"api_key": ai_config.get("api_key")}
        base_url = ai_config.get("base_url")
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)
        self.model = ai_config.get("model", "qwen-max")

    def _chat(self, system: str, user: str, temperature: float = 0.0) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""

    def generate_sql(self, question: str, schema_desc: str) -> str:
        """根据表结构和问题生成一条 SELECT 语句。"""
        system = (
            "你是 PostgreSQL 专家。根据给定的表结构和用户问题，生成一条正确的 SELECT 查询。\n"
            "要求：\n"
            "1. 只输出 SQL 语句本身，不要任何解释，不要 markdown 代码块。\n"
            "2. 只使用 SELECT，禁止任何写操作。\n"
            "3. 只使用表结构中出现的表名与字段名，不要臆造。\n"
            "4. 查询要简洁、正确；统计类问题优先使用 GROUP BY 与聚合函数。"
        )
        user = f"表结构：\n{schema_desc}\n\n用户问题：\n{question}\n\n请输出 SQL："
        sql = self._chat(system, user)
        return self._clean_sql(sql)

    def summarize(
        self,
        question: str,
        sql: str,
        columns: List[str],
        rows: List[List[Any]],
    ) -> str:
        """把查询结果总结成自然语言统计结论。"""
        system = "你是数据分析助手，用中文简洁、准确地总结查询结果。"
        preview = self._format_rows(columns, rows)
        user = (
            f"用户问题：{question}\n"
            f"执行的 SQL：{sql}\n"
            f"结果字段：{columns}\n"
            f"查询结果（最多显示前 50 行）：\n{preview}\n\n"
            "请给出统计结论或数据解读。"
        )
        return self._chat(system, user, temperature=0.2)

    @staticmethod
    def _format_rows(columns: List[str], rows: List[List[Any]], limit: int = 50) -> str:
        rows = rows[:limit]
        if not rows:
            return "(无数据)"
        header = "\t".join(columns)
        lines = [header]
        for r in rows:
            lines.append("\t".join("" if v is None else str(v) for v in r))
        return "\n".join(lines)

    @staticmethod
    def _clean_sql(text: str) -> str:
        """去掉模型输出里的 markdown 代码块等杂质。"""
        text = (text or "").strip()
        text = re.sub(r"^```(?:sql)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        return text.strip().rstrip(";").rstrip()