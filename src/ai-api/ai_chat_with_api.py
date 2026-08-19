#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI对话程序 - 支持真实AI API
支持OpenAI、Claude、本地模型等多种AI服务
"""

import json
import os
import datetime
import requests
from typing import List, Dict, Optional
import argparse

# 导入RAG管理器
from rag_manager import RAGManager

"""客户端层（AIClient 及其子类）:
    负责与外部 AI API 通信。屏蔽了 OpenAI、Claude、Qwen 各自不同的接口差异，对外提供统一的 get_response（传统）和 get_streaming_response（流式）方法。
"""
class AIClient:
    """AI客户端基类"""
    
    def __init__(self, api_key: str, model: str = None, base_url: str = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
    
    def get_response(self, messages: List[Dict], **kwargs) -> str:
        """获取AI响应（传统模式）"""
        raise NotImplementedError
    
    def get_streaming_response(self, messages: List[Dict], **kwargs):
        """获取AI流式响应（流式模式，返回生成器）"""
        raise NotImplementedError


class OpenAIClient(AIClient):
    """OpenAI客户端"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo", base_url: str = None):
        super().__init__(api_key, model, base_url)
        self.base_url = base_url or "https://api.openai.com/v1"
    
    def get_response(self, messages: List[Dict], **kwargs) -> str:
        """获取OpenAI响应（传统模式）"""
        if "model" in kwargs:
            self.model = kwargs["model"]
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        
        except requests.exceptions.RequestException as e:
            return f"❌ OpenAI API请求失败: {e}"
        except KeyError as e:
            return f"❌ 解析OpenAI响应失败: {e}"
        except Exception as e:
            return f"❌ 未知错误: {e}"
    
    def get_streaming_response(self, messages: List[Dict], **kwargs):
        """获取OpenAI流式响应"""
        if "model" in kwargs:
            self.model = kwargs["model"]
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000,
            "stream": True  # 启用流式响应
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=60,
                stream=True
            )
            response.raise_for_status()
            
            full_response = ""
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_part = line[6:]  # 移除 'data: ' 前缀
                        if data_part.strip() == '[DONE]':
                            break
                        
                        try:
                            chunk = json.loads(data_part)
                            if 'choices' in chunk and len(chunk['choices']) > 0:
                                delta = chunk['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content = delta['content']
                                    full_response += content
                                    yield content
                        except json.JSONDecodeError:
                            continue
            
            return full_response
            
        except requests.exceptions.RequestException as e:
            yield f"❌ OpenAI API请求失败: {e}"
        except Exception as e:
            yield f"❌ 未知错误: {e}"


class ClaudeClient(AIClient):
    """Anthropic Claude客户端"""
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229", base_url: str = None):
        super().__init__(api_key, model, base_url)
        self.base_url = base_url or "https://api.anthropic.com/v1"
    
    def get_response(self, messages: List[Dict], **kwargs) -> str:
        """获取Claude响应（传统模式）"""
        if "model" in kwargs:
            self.model = kwargs["model"]
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        # 转换消息格式
        system_message = ""
        filtered_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                filtered_messages.append(msg)
        
        data = {
            "model": self.model,
            "max_tokens": 1000,
            "messages": filtered_messages
        }
        
        if system_message:
            data["system"] = system_message
        
        try:
            response = requests.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            return result["content"][0]["text"].strip()
        
        except requests.exceptions.RequestException as e:
            return f"❌ Claude API请求失败: {e}"
        except KeyError as e:
            return f"❌ 解析Claude响应失败: {e}"
        except Exception as e:
            return f"❌ 未知错误: {e}"
    
    def get_streaming_response(self, messages: List[Dict], **kwargs):
        """获取Claude流式响应"""
        if "model" in kwargs:
            self.model = kwargs["model"]
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        # 转换消息格式
        system_message = ""
        filtered_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                filtered_messages.append(msg)
        
        data = {
            "model": self.model,
            "max_tokens": 1000,
            "messages": filtered_messages,
            "stream": True
        }
        
        if system_message:
            data["system"] = system_message
        
        try:
            response = requests.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=data,
                timeout=60,
                stream=True
            )
            response.raise_for_status()
            
            full_response = ""
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_part = line[6:]  # 移除 'data: ' 前缀
                        if data_part.strip() == '[DONE]':
                            break
                        
                        try:
                            chunk = json.loads(data_part)
                            if 'content' in chunk and len(chunk['content']) > 0:
                                delta = chunk['content'][0].get('text', '')
                                full_response += delta
                                yield delta
                        except json.JSONDecodeError:
                            continue
            
            return full_response
            
        except requests.exceptions.RequestException as e:
            yield f"❌ Claude API请求失败: {e}"
        except Exception as e:
            yield f"❌ 未知错误: {e}"


class QwenClient(AIClient):
    """阿里云Qwen客户端"""
    
    def __init__(self, api_key: str, model: str = "qwen-turbo", base_url: str = None):
        super().__init__(api_key, model, base_url)
        self.base_url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.client = None
    
    def _get_client(self):
        """获取OpenAI兼容客户端"""
        if self.client is None:
            import openai
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        return self.client
    
    def get_response(self, messages: List[Dict], **kwargs) -> str:
        """获取Qwen响应（传统模式）"""
        if "model" in kwargs:
            self.model = kwargs["model"]
        
        try:
            # 转换消息格式为OpenAI兼容格式
            openai_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    # Qwen支持system消息
                    openai_messages.append({
                        "role": "system",
                        "content": msg["content"]
                    })
                else:
                    openai_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=0.7,
                max_tokens=2048
            )
            return response.choices[0].message.content
        
        except ImportError:
            return "❌ 请安装openai库: pip install openai"
        except Exception as e:
            return f"❌ Qwen API请求失败: {e}"
    
    def get_streaming_response(self, messages: List[Dict], **kwargs):
        """获取Qwen流式响应"""
        if "model" in kwargs:
            self.model = kwargs["model"]
        
        try:
            # 转换消息格式为OpenAI兼容格式
            openai_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    openai_messages.append({
                        "role": "system",
                        "content": msg["content"]
                    })
                else:
                    openai_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            client = self._get_client()
            
            # 使用流式响应
            stream = client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=0.7,
                max_tokens=2048,
                stream=True
            )
            
            full_response = ""
            for chunk in stream:
                # 跳过空 choices 的 chunk（如末尾携带 usage 统计的 chunk），
                # 否则 chunk.choices[0] 会抛 IndexError: list index out of range
                if not chunk.choices:
                    continue
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
            
            return full_response
            
        except ImportError:
            yield "❌ 请安装openai库: pip install openai"
        except Exception as e:
            yield f"❌ Qwen API请求失败: {e}"

"""业务逻辑层（AIChatter）:
    核心控制器。负责管理对话历史、加载配置、协调 RAG（检索增强生成）和提示词模板，并决定何时调用客户端。
"""
class AIChatter:
    """AI对话器"""
    
    def __init__(self, config_file: str = "config.json", preset_service: str = None, streaming: bool = True):
        """初始化"""
        self.user_name = "用户"
        self.ai_name = "AI助手"
        self.config_file = config_file                  # 保存配置文件路径
        self.preset_service = preset_service            # 保存预设服务 (qwen)
        self.streaming = streaming                      # 是否使用流式响应

        self.ai_client: Optional[AIClient] = None       # AI客户端（当前为None，等待初始化）
        self.conversation_history: List[Dict] = []      # 存放多轮对话历史
        self.prompt_manager = None                      # 提示词管理器（当前为None，等待初始化）
        self.rag_manager: Optional[RAGManager] = None   # RAG管理器（当前为None，等待初始化）
        self.rag_enabled = False                        # 默认禁用RAG功能
        
        # 加载配置
        self.load_config()
        
        # 初始化提示词管理器
        self.setup_prompt_manager()
        
        # 初始化RAG管理器
        self.setup_rag_manager()
        
        # 如果预设了服务，直接设置AI客户端
        if preset_service:
            try:
                self.config["ai_service"] = preset_service
                self.ai_client = self.create_client(preset_service)
                print(f"✅ 已预设AI服务: {preset_service}")
            except Exception as e:
                print(f"⚠️ 预设AI服务初始化失败: {e}")
                # 如果预设失败，尝试加载默认服务
                self.setup_ai_client()
        
        # 显示响应模式信息
        response_mode = "流式响应" if self.streaming else "传统响应"
        print(f"🎯 当前响应模式: {response_mode}")
        print(f"🔍 RAG功能: {'已启用' if self.rag_enabled else '已禁用'}")
    
    def setup_rag_manager(self):
        """初始化RAG管理器"""
        try:
            # 从配置中加载RAG设置
            rag_config = self.config.get("rag", {})
            self.rag_enabled = rag_config.get("enabled", False)
            
            # 初始化RAG管理器
            self.rag_manager = RAGManager(rag_config)
            
            # 如果配置中指定了索引文件，尝试加载
            index_path = rag_config.get("index_path")
            if index_path and os.path.exists(index_path):
                try:
                    self.rag_manager.load_rag_index(index_path)
                    print(f"✅ 已加载RAG索引: {index_path}")
                except Exception as e:
                    print(f"⚠️ 加载RAG索引失败: {e}")
                    
        except Exception as e:
            print(f"⚠️ RAG管理器初始化失败: {e}")
            self.rag_manager = None
            self.rag_enabled = False
    
    def setup_prompt_manager(self):
        """初始化提示词管理器"""
        try:
            # 创建提示词管理器
            from prompt_manager import PromptManager
            self.prompt_manager = PromptManager()
            print("✅ 提示词管理器初始化成功")
            return True
        except ImportError:
            # 如果提示词管理器模块不存在，创建简化版本
            print("⚠️ 提示词管理器模块不存在，AI将继续使用配置中的系统提示词")
            self.prompt_manager = None
            return False
        except Exception as e:
            print(f"❌ 提示词管理器初始化失败: {e}")
            self.prompt_manager = None
            return False
    
    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.config = config
            else:
                self.config = self._create_default_config()
                self.save_config()
        except Exception as e:
            print(f"❌ 加载配置失败: {e}")
            self.config = self._create_default_config()
    
    def _create_default_config(self) -> dict:
        """创建默认配置"""
        return {
            "ai_service": "openai",
            "openai": {
                "api_key": "",
                "model": "gpt-3.5-turbo"
            },
            "claude": {
                "api_key": "",
                "model": "claude-3-sonnet-20240229"
            },
            "local": {
                "base_url": "http://localhost:11434",
                "model": "llama2"
            }
        }
    
    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
    
    def setup_ai_client(self) -> bool:
        """设置AI客户端"""
        try:
            service = self.config.get("ai_service", "openai")
            self.ai_client = self.create_client(service)
            return True
        except Exception as e:
            print(f"❌ AI客户端初始化失败: {e}")
            return False
    
    def create_client(self, service_name):
        """创建AI客户端"""
        if service_name == "openai":
            config = self.config.get("openai", {})
            return OpenAIClient(
                api_key=config.get("api_key", ""),
                model=config.get("model", "gpt-3.5-turbo"),
                base_url=config.get("base_url")
            )
        elif service_name == "claude":
            config = self.config.get("claude", {})
            return ClaudeClient(
                api_key=config.get("api_key", ""),
                model=config.get("model", "claude-3-sonnet-20240229"),
                base_url=config.get("base_url")
            )
        elif service_name == "qwen":
            config = self.config.get("qwen", {})
            return QwenClient(
                api_key=config.get("api_key", ""),
                model=config.get("model", "qwen-turbo"),
                base_url=config.get("base_url")
            )
        elif service_name == "local":
            config = self.config.get("local", {})
            return OpenAIClient(
                api_key="dummy",
                model=config.get("model", "llama2"),
                base_url=config.get("base_url", "http://localhost:11434")
            )
        else:
            raise ValueError(f"不支持的AI服务: {service_name}")
    
    def get_conversation_messages(self) -> List[Dict]:
        """获取对话消息格式"""
        messages = []
        
        # 添加系统消息（优先使用提示词模板）
        if hasattr(self, 'prompt_manager') and self.prompt_manager:
            current_template = self.prompt_manager.get_current_template()
            if current_template:
                system_prompt = current_template.system_prompt
            else:
                system_prompt = self.config.get("system_prompt", "你是一个友善的AI助手。")
        else:
            system_prompt = self.config.get("system_prompt", "你是一个友善的AI助手。")
        
        messages.append({"role": "system", "content": system_prompt})
        
        # 添加对话历史（限制最近20轮对话以控制token长度）
        recent_history = self.conversation_history[-40:]  # 最近40条消息
        messages.extend(recent_history)
        
        return messages
    
    def get_ai_response(self, user_input: str) -> str:
        """获取AI响应，支持流式和传统两种模式"""
        try:
            if not self.ai_client:
                return "❌ AI客户端未初始化"
            
            # 如果RAG功能启用，生成增强提示词
            enhanced_user_input = user_input
            if self.rag_enabled and self.rag_manager:
                try:
                    enhanced_user_input = self.rag_manager.generate_enhanced_prompt(user_input)
                except Exception as e:
                    print(f"⚠️ RAG增强提示词生成失败: {e}")
                    # 失败时使用原始输入
            
            # 构建消息历史
            messages = self.get_conversation_messages()
            user_message = {"role": "user", "content": enhanced_user_input}
            messages.append(user_message)
            
            # 根据设置选择响应模式
            if hasattr(self, 'streaming') and self.streaming:
                return self._get_streaming_response(messages)
            else:
                return self._get_traditional_response(messages)
                
        except Exception as e:
            error_msg = f"❌ 获取AI响应失败: {e}"
            return error_msg
    
    def _get_traditional_response(self, messages: List[Dict]) -> str:
        """获取传统一次性响应"""
        try:
            response = self.ai_client.get_response(messages)
            return response
        except Exception as e:
            return f"❌ 传统响应获取失败: {e}"
    
    def _get_streaming_response(self, messages: List[Dict]) -> str:
        """获取流式响应"""
        try:
            print(f"🤖 {self.ai_client.__class__.__name__}: ", end="", flush=True)
            
            # 检查客户端是否支持流式响应
            if not hasattr(self.ai_client, 'get_streaming_response'):
                return self._get_traditional_response(messages)
            
            full_response = ""
            for content_chunk in self.ai_client.get_streaming_response(messages):
                print(content_chunk, end="", flush=True)
                full_response += content_chunk
            
            print()  # 换行
            
            return full_response
            
        except Exception as e:
            return f"❌ 流式响应获取失败: {e}"
    
    def add_message(self, role: str, content: str):
        """添加消息到对话历史"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.conversation_history.append(message)
        return message
    
    def save_conversation(self, filename: str = None):
        """保存对话历史"""
        if filename is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"conversation_{timestamp}.json"
        
        conversation_data = {
            "title": f"AI对话记录 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "user_name": self.user_name,
            "ai_name": self.ai_name,
            "ai_service": self.config.get("ai_service", "openai"),
            "messages": self.conversation_history
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, ensure_ascii=False, indent=2)
            print(f"✅ 对话记录已保存到: {filename}")
            return filename
        except Exception as e:
            print(f"❌ 保存对话记录失败: {e}")
            return None
    
    def show_config(self):
        """显示当前配置"""
        print("\n" + "=" * 50)
        print("🔧 当前配置")
        print("=" * 50)
        print(f"AI服务: {self.config.get('ai_service', 'openai')}")
        
        service = self.config.get("ai_service", "openai")
        if service == "openai":
            api_key = self.config["openai"]["api_key"]
            model = self.config["openai"]["model"]
            print(f"OpenAI模型: {model}")
            print(f"API密钥状态: {'已设置' if api_key and api_key != 'sk-your-openai-api-key-here' else '未设置'}")
        elif service == "claude":
            api_key = self.config["claude"]["api_key"]
            model = self.config["claude"]["model"]
            print(f"Claude模型: {model}")
            print(f"API密钥状态: {'已设置' if api_key and api_key != 'sk-ant-your-claude-api-key-here' else '未设置'}")
        
        print("=" * 50)
    
    def show_prompt_templates(self):
        """显示可用的提示词模板"""
        if not self.prompt_manager:
            print("❌ 提示词管理器未初始化")
            return
        
        templates = self.prompt_manager.get_templates()
        current_id = self.prompt_manager.current_template_id
        
        print("\n" + "=" * 60)
        print("📋 可用的提示词模板")
        print("=" * 60)
        
        for i, template in enumerate(templates, 1):
            marker = "✅" if template.id == current_id else "  "
            print(f"{marker} {i}. {template.name}")
            print(f"    📝 {template.description}")
            print(f"    🏷️  标签: {', '.join(template.tags) if template.tags else '无'}")
            print(f"    📊 使用次数: {template.usage_count}")
            print()
        
        print(f"当前使用: {current_id}")
        print("=" * 60)
    
    def switch_prompt_template(self, template_id: str = None):
        """切换提示词模板"""
        if not self.prompt_manager:
            print("❌ 提示词管理器未初始化")
            return False
        
        if template_id is None:
            # 交互式选择
            templates = self.prompt_manager.get_templates()
            current_id = self.prompt_manager.current_template_id
            
            print("\n" + "=" * 50)
            print("🔄 切换提示词模板")
            print("=" * 50)
            
            for i, template in enumerate(templates, 1):
                marker = "👈 当前" if template.id == current_id else ""
                print(f"{i}. {template.name} {marker}")
                print(f"   {template.description}")
                print()
            
            try:
                choice = input("请选择模板编号 (按回车保持当前): ").strip()
                if not choice:
                    return False
                
                index = int(choice) - 1
                if 0 <= index < len(templates):
                    template_id = templates[index].id
                else:
                    print("❌ 无效的选择")
                    return False
            except ValueError:
                print("❌ 请输入有效的数字")
                return False
            except KeyboardInterrupt:
                print("\n已取消")
                return False
        
        # 切换模板
        if self.prompt_manager.set_current_template(template_id):
            current_template = self.prompt_manager.get_current_template()
            print(f"✅ 已切换到: {current_template.name}")
            print(f"📝 描述: {current_template.description}")
            return True
        else:
            print("❌ 切换失败，模板不存在")
            return False
    
    def add_custom_prompt(self):
        """添加自定义提示词模板"""
        if not self.prompt_manager:
            print("❌ 提示词管理器未初始化")
            return False
        
        try:
            print("\n" + "=" * 50)
            print("➕ 添加自定义提示词模板")
            print("=" * 50)
            
            name = input("模板名称: ").strip()
            if not name:
                print("❌ 模板名称不能为空")
                return False
            
            description = input("模板描述: ").strip()
            if not description:
                print("❌ 模板描述不能为空")
                return False
            
            print("\n请输入系统提示词（输入 'END' 结束）:")
            system_prompt_lines = []
            while True:
                line = input("> ")
                if line.strip() == 'END':
                    break
                system_prompt_lines.append(line)
            
            system_prompt = '\n'.join(system_prompt_lines)
            if not system_prompt:
                print("❌ 系统提示词不能为空")
                return False
            
            tags_input = input("标签 (用逗号分隔，可选): ").strip()
            tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()] if tags_input else []
            
            template_id = self.prompt_manager.add_template(
                name=name,
                description=description,
                system_prompt=system_prompt,
                tags=tags
            )
            
            print(f"✅ 成功添加模板: {name} (ID: {template_id})")
            
            # 询问是否立即切换到此模板
            switch = input("是否立即切换到此模板? (y/n): ").strip().lower()
            if switch == 'y':
                self.prompt_manager.set_current_template(template_id)
                print(f"✅ 已切换到: {name}")
            
            return True
            
        except KeyboardInterrupt:
            print("\n❌ 已取消添加")
            return False
        except Exception as e:
            print(f"❌ 添加失败: {e}")
            return False
    
    def search_prompts(self):
        """搜索提示词模板"""
        if not self.prompt_manager:
            print("❌ 提示词管理器未初始化")
            return
        
        try:
            keyword = input("\n🔍 搜索关键词: ").strip()
            if not keyword:
                return
            
            results = self.prompt_manager.search_templates(keyword)
            
            print(f"\n🔍 搜索结果 (关键词: '{keyword}'):")
            print("=" * 60)
            
            if not results:
                print("❌ 没有找到匹配的模板")
            else:
                for template in results:
                    print(f"📄 {template.name}")
                    print(f"   📝 {template.description}")
                    print(f"   🏷️  标签: {', '.join(template.tags) if template.tags else '无'}")
                    print(f"   📊 使用次数: {template.usage_count}")
                    print()
            
        except KeyboardInterrupt:
            print("\n已取消搜索")
        except Exception as e:
            print(f"❌ 搜索失败: {e}")
    
    def show_prompt_usage_stats(self):
        """显示提示词使用统计"""
        if not self.prompt_manager:
            print("❌ 提示词管理器未初始化")
            return
        
        print("\n" + "=" * 60)
        print("📊 提示词使用统计")
        print("=" * 60)
        
        # 按使用次数排序
        templates = self.prompt_manager.get_popular_templates(10)  # 显示前10个
        
        if not templates:
            print("❌ 暂无使用统计")
            return
        
        for i, template in enumerate(templates, 1):
            print(f"{i}. {template.name}")
            print(f"   使用次数: {template.usage_count}")
            print(f"   创建时间: {template.created_at[:10]}")
            print(f"   最后更新: {template.updated_at[:10]}")
            print()
        
        print("=" * 60)
        print("  save/保存    - 保存当前对话到文件")
        print("  config/配置  - 显示当前配置")
        print("  quit/退出    - 退出程序")
        print("  rag/rag      - RAG功能管理")
        print("\n功能说明:")
        print("  • 支持OpenAI GPT、Claude和Qwen模型")
        print("  • 自动保存对话历史")
        print("  • 支持多种AI服务切换")
        print("  • 时间戳记录每条消息")
        print("  • 支持RAG(检索增强生成)功能")
        print("=" * 40)
    
    def _show_history(self):
        """显示对话历史"""
        if not self.conversation_history:
            print("\n暂无对话记录")
            return
        
        print("\n" + "=" * 50)
        print("📋 对话历史")
        print("=" * 50)
        
        for i, message in enumerate(self.conversation_history[-10:], 1):
            timestamp = datetime.datetime.fromisoformat(message["timestamp"])
            time_str = timestamp.strftime("%H:%M:%S")
            
            if message["role"] == "user":
                print(f"{i:2d}. [{time_str}] {self.user_name}: {message['content'][:100]}{'...' if len(message['content']) > 100 else ''}")
            else:
                print(f"{i:2d}. [{time_str}] {self.ai_name}: {message['content'][:100]}{'...' if len(message['content']) > 100 else ''}")
        
        print(f"\n共 {len(self.conversation_history)} 条消息")
        print("=" * 50)
    
    def chat(self):
        """开始对话"""
        print("=" * 50)
        print("🤖 欢迎使用AI对话程序！")
        print("=" * 50)
        
        # 设置AI客户端
        if not self.setup_ai_client():
            print("❌ AI客户端初始化失败，请检查配置")
            return
        
        print(f"✅ AI客户端初始化成功，使用服务: {self.config.get('ai_service', 'openai')}")
        print("输入 'help' 查看帮助信息")
        print("输入 'quit' 退出程序")
        print("=" * 50)
        
        while True:
            try:
                # 获取用户输入
                user_input = input(f"\n{self.user_name}: ").strip()
                
                # 处理特殊命令
                if user_input.lower() in ['quit', 'exit', '退出']:
                    print(f"\n{self.ai_name}: 好的，再见！👋")
                    self.add_message("user", user_input)
                    self.add_message("assistant", "好的，再见！")
                    break
                
                elif user_input.lower() in ['help', '帮助']:
                    self._show_help()
                    self.add_message("user", user_input)
                    self.add_message("assistant", "已显示帮助信息")
                    continue
                
                elif user_input.lower() in ['save', '保存']:
                    self.save_conversation()
                    self.add_message("user", user_input)
                    self.add_message("assistant", "已保存对话记录")
                    continue
                
                elif user_input.lower() in ['config', '配置']:
                    self.show_config()
                    self.add_message("user", user_input)
                    self.add_message("assistant", "已显示配置信息")
                    continue
                
                elif user_input.lower() in ['history', '历史']:
                    self._show_history()
                    self.add_message("user", user_input)
                    self.add_message("assistant", "已显示对话历史")
                    continue
                
                elif user_input.lower() == 'switch':
                    print("\n🔄 切换AI服务")
                    print("="*30)
                    print("可用服务:")
                    print("1. openai  - OpenAI GPT")
                    print("2. claude  - Anthropic Claude")  
                    print("3. qwen    - 阿里云Qwen")
                    print("4. local   - 本地模型")
                    print("="*30)
                    
                    choice = input("请选择服务 (1-4): ").strip()
                    
                    service_map = {
                        "1": "openai",
                        "2": "claude", 
                        "3": "qwen",
                        "4": "local"
                    }
                    
                    if choice in service_map:
                        try:
                            old_service = self.config.get("ai_service", "openai")
                            self.config["ai_service"] = service_map[choice]
                            self.ai_client = self.create_client(service_map[choice])
                            print(f"✅ 已切换到 {service_map[choice]} 服务")
                            self.add_message("user", user_input)
                            self.add_message("assistant", f"已从 {old_service} 切换到 {service_map[choice]} 服务")
                        except Exception as e:
                            print(f"❌ 切换服务失败: {e}")
                            self.add_message("user", user_input)
                            self.add_message("assistant", f"切换服务失败: {e}")
                    else:
                        print("❌ 无效选择")
                        self.add_message("user", user_input)
                        self.add_message("assistant", "无效选择，切换失败")
                    continue
                
                # RAG相关命令
                elif user_input.lower() == 'rag':
                    print("\n🔍 RAG功能管理")
                    print("="*30)
                    print("RAG功能状态: {}".format("✅ 已启用" if self.rag_enabled else "❌ 已禁用"))
                    print("可用操作:")
                    print("1. enable/开启  - 启用RAG功能")
                    print("2. disable/关闭 - 禁用RAG功能")
                    print("3. add/添加     - 添加文档到RAG")
                    print("4. status/状态  - 查看RAG状态")
                    print("5. save/保存    - 保存RAG索引")
                    print("6. load/加载    - 加载RAG索引")
                    print("="*30)
                    
                    action = input("请输入操作: ").strip().lower()
                    
                    if action in ['enable', '开启', '1']:
                        self.rag_enabled = True
                        self.config.setdefault("rag", {})["enabled"] = True
                        self.save_config()
                        print("✅ RAG功能已启用")
                        self.add_message("user", user_input)
                        self.add_message("assistant", "RAG功能已启用")
                    
                    elif action in ['disable', '关闭', '2']:
                        self.rag_enabled = False
                        self.config.setdefault("rag", {})["enabled"] = False
                        self.save_config()
                        print("✅ RAG功能已禁用")
                        self.add_message("user", user_input)
                        self.add_message("assistant", "RAG功能已禁用")
                    
                    elif action in ['add', '添加', '3']:
                        if not self.rag_manager:
                            print("❌ RAG管理器未初始化")
                            continue
                        
                        file_path = input("请输入文档路径: ").strip()
                        file_path = file_path.replace('"', '').replace("'", "")  # 移除引号
                        
                        if os.path.exists(file_path):
                            result = self.rag_manager.add_document(file_path)
                            if result["status"] == "success":
                                print(f"✅ 文档添加成功: {result['message']}")
                            else:
                                print(f"❌ 文档添加失败: {result['message']}")
                        else:
                            print(f"❌ 文件不存在: {file_path}")
                            
                        self.add_message("user", user_input)
                        self.add_message("assistant", "RAG文档添加操作完成")
                    
                    elif action in ['status', '状态', '4']:
                        if not self.rag_manager:
                            print("❌ RAG管理器未初始化")
                        else:
                            status = self.rag_manager.get_status()
                            print(f"RAG状态: {'已初始化' if status['initialized'] else '未初始化'}")
                            print(f"向量存储: {'已创建' if status['has_vector_store'] else '未创建'}")
                        
                        self.add_message("user", user_input)
                        self.add_message("assistant", "已显示RAG状态")
                    
                    elif action in ['save', '保存', '5']:
                        if not self.rag_manager:
                            print("❌ RAG管理器未初始化")
                        elif not self.rag_manager.is_initialized:
                            print("❌ RAG系统未初始化，无法保存")
                        else:
                            index_path = input("请输入索引保存路径: ").strip()
                            if not index_path:
                                index_path = "rag_index"
                            
                            try:
                                self.rag_manager.save_rag_index(index_path)
                                self.config.setdefault("rag", {})["index_path"] = index_path
                                self.save_config()
                                print(f"✅ RAG索引已保存到: {index_path}")
                            except Exception as e:
                                print(f"❌ 保存RAG索引失败: {e}")
                        
                        self.add_message("user", user_input)
                        self.add_message("assistant", "RAG索引保存操作完成")
                    
                    elif action in ['load', '加载', '6']:
                        if not self.rag_manager:
                            print("❌ RAG管理器未初始化")
                        else:
                            index_path = input("请输入索引加载路径: ").strip()
                            if not index_path:
                                index_path = self.config.get("rag", {}).get("index_path", "rag_index")
                            
                            try:
                                self.rag_manager.load_rag_index(index_path)
                                self.config.setdefault("rag", {})["index_path"] = index_path
                                self.save_config()
                                print(f"✅ RAG索引已加载: {index_path}")
                            except Exception as e:
                                print(f"❌ 加载RAG索引失败: {e}")
                        
                        self.add_message("user", user_input)
                        self.add_message("assistant", "RAG索引加载操作完成")
                    
                    else:
                        print("❌ 无效操作")
                    
                    continue
                
                elif user_input == "":
                    print(f"{self.ai_name}: 请输入一些内容与我对话！")
                    continue
                
                # 获取AI响应（内部根据历史构建 prompt，流式模式会实时打印内容）
                print(f"\n{self.ai_name}: 正在思考...", end="", flush=True)
                ai_response = self.get_ai_response(user_input)
                if not self.streaming:
                    # 传统模式：一次性显示完整回复
                    print(f"\r{self.ai_name}: {ai_response}")

                # 添加本轮用户消息与AI响应到历史
                self.add_message("user", user_input)
                self.add_message("assistant", ai_response)
                
            except KeyboardInterrupt:
                print(f"\n\n{self.ai_name}: 程序被中断，再见！")
                break
            except Exception as e:
                print(f"\n❌ 发生错误: {e}")
                continue


def main():
    """主函数"""
    # 命令行参数解析器，使用 Python 内置的 argparse 库 
    parser = argparse.ArgumentParser(description='AI对话程序')
    parser.add_argument('--config', default='config.json', help='配置文件路径')
    parser.add_argument('--service', choices=['openai', 'claude', 'qwen', 'local'], help='启动时预设的AI服务')

    # 严格处理字符串（兼容你当前的传参方式）
    parser.add_argument('--streaming',  type=lambda x: x.lower() == 'true', default=True, help='是否使用流式响应 (默认: True)')
    args = parser.parse_args()
    
    print("🚀 启动AI对话程序...")
    
    # 显示启动信息
    if args.service:
        print(f"🎯 将使用AI服务: {args.service}")
    else:
        print("📋 将使用配置文件中的AI服务")
    
    # 显示响应模式
    response_mode = "流式响应" if args.streaming else "传统响应"
    print(f"🎭 响应模式: {response_mode}")
    
    # 创建AI对话实例
    chatter = AIChatter(config_file=args.config, preset_service=args.service, streaming=args.streaming)
    
    # 开始对话
    chatter.chat()


if __name__ == "__main__":
    main()