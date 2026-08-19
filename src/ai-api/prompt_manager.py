#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""提示词模板管理器

提供系统提示词模板的增删查改、切换与持久化能力。
供 ai_chat_with_api.py 中的 AIChatter 使用。
"""

import os
import json
import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class PromptTemplate:
    """单个提示词模板"""
    id: str
    name: str
    description: str
    system_prompt: str
    tags: List[str] = field(default_factory=list)
    usage_count: int = 0
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


class PromptManager:
    """提示词管理器，负责模板的存储、检索与切换"""

    def __init__(self, storage_file: Optional[str] = None):
        self.storage_file = storage_file or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "prompt_templates.json"
        )
        self.templates: List[PromptTemplate] = []
        self.current_template_id: Optional[str] = None

        self._load()

    # ---------- 内部持久化 ----------
    def _default_templates(self) -> List[PromptTemplate]:
        """内置默认模板"""
        return [
            PromptTemplate(
                id="general",
                name="通用助手",
                description="友善、有帮助的通用AI助手，适合日常对话",
                system_prompt="你是一个友善、有帮助的AI助手。请用中文回答问题，并尽量提供有用、准确的信息。",
                tags=["通用", "日常"],
            ),
            PromptTemplate(
                id="coder",
                name="代码专家",
                description="专注于编程、调试与代码解释的助手",
                system_prompt="你是一位资深软件工程师。请用中文回答问题，给出清晰、可运行的代码示例，并解释关键实现思路。",
                tags=["编程", "代码", "调试"],
            ),
            PromptTemplate(
                id="translator",
                name="翻译助手",
                description="中英互译，注重信达雅",
                system_prompt="你是一位专业翻译。请根据用户输入在中文与英文之间进行准确、自然的翻译，并保持原文语气。",
                tags=["翻译", "英语"],
            ),
            PromptTemplate(
                id="writer",
                name="写作助手",
                description="帮助撰写文章、润色文本",
                system_prompt="你是一位文字工作者，擅长写作与润色。请根据用户需求撰写或优化文本，语言流畅、结构清晰。",
                tags=["写作", "润色"],
            ),
        ]

    def _load(self):
        """从存储文件加载模板，若不存在则使用内置默认模板"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                templates = [PromptTemplate(**t) for t in data.get("templates", [])]
                if templates:
                    self.templates = templates
                    self.current_template_id = data.get("current_template_id")
                    return
            except Exception:
                # 存储文件损坏时回退到默认模板
                pass
        self.templates = self._default_templates()
        self.current_template_id = self.templates[0].id

    def _save(self):
        """保存模板到存储文件（失败不抛出，避免影响主流程）"""
        try:
            data = {
                "current_template_id": self.current_template_id,
                "templates": [asdict(t) for t in self.templates],
            }
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ---------- 查询 ----------
    def _find(self, template_id: str) -> Optional[PromptTemplate]:
        for t in self.templates:
            if t.id == template_id:
                return t
        return None

    def get_templates(self) -> List[PromptTemplate]:
        """返回全部模板"""
        return list(self.templates)

    def get_current_template(self) -> Optional[PromptTemplate]:
        """返回当前使用的模板，未设置时返回 None"""
        return self._find(self.current_template_id) if self.current_template_id else None

    def get_popular_templates(self, limit: int = 10) -> List[PromptTemplate]:
        """按使用次数降序返回热门模板"""
        return sorted(self.templates, key=lambda t: t.usage_count, reverse=True)[:limit]

    def search_templates(self, keyword: str) -> List[PromptTemplate]:
        """按关键词在名称、描述、标签中搜索"""
        keyword = keyword.lower()
        results = []
        for t in self.templates:
            haystack = " ".join([t.name, t.description, " ".join(t.tags)]).lower()
            if keyword in haystack:
                results.append(t)
        return results

    # ---------- 操作 ----------
    def set_current_template(self, template_id: str) -> bool:
        """切换到指定模板，成功返回 True"""
        template = self._find(template_id)
        if template is None:
            return False
        self.current_template_id = template_id
        template.usage_count += 1
        template.updated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save()
        return True

    def add_template(self, name: str, description: str, system_prompt: str, tags: Optional[List[str]] = None) -> str:
        """新增自定义模板，返回新模板 ID"""
        template_id = f"custom_{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        template = PromptTemplate(
            id=template_id,
            name=name,
            description=description,
            system_prompt=system_prompt,
            tags=tags or [],
        )
        self.templates.append(template)
        self._save()
        return template_id