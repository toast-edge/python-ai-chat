# AI对话程序 - 支持真实AI API

这是一个名为 python-ai-code 的AI对话系统项目，支持多种AI服务（如OpenAI、Claude、Qwen等），具有RAG（检索增强生成）功能、流式响应等功能。项目采用模块化设计，提供了丰富的交互功能和配置选项。

## 🚀 功能特性

- ✅ **真实AI集成**: 支持OpenAI GPT和Claude模型
- 💬 **连续对话**: 支持多轮对话和上下文记忆
- 📝 **对话记录**: 自动保存对话历史到JSON文件
- ⏰ **时间戳**: 每条消息都包含准确时间信息
- 🔧 **灵活配置**: 支持切换AI服务和模型
- 🎯 **智能错误处理**: 完善的异常处理和用户提示

## 📋 使用前准备
### 0. 项目结构
```
python-ai-code/
├── src/
│   └── ai-api/
│       ├── ai_chat_with_api.py         # 主程序文件，AI对话核心逻辑
│       ├── rag_manager.py              # RAG（检索增强生成）功能模块
│       ├── run_ai_chat.py              # 启动脚本
│       ├── config.json                 # 配置文件
│       ├── test_rag_functionality.py   # RAG功能测试脚本
│       └── test_rag_document.txt       # RAG测试文档
├── README.md                          # 项目说明文档
├── requirements.txt                   # Python依赖包列表
└── pyproject.toml                     # 项目配置文件（空）
```

### 1. 配置API密钥

编辑 `config.json` 文件，填入你的AI服务API密钥：

```json
{
  "ai_service": "openai",  // 或 "claude"
  "openai": {
    "api_key": "sk-your-actual-api-key-here",
    "model": "gpt-3.5-turbo"
  },
  "claude": {
    "api_key": "sk-ant-your-actual-claude-api-key",
    "model": "claude-3-sonnet-20240229"
  }
}
```

### 2. 安装依赖

```bash
pip install requests
```

## 🎮 使用方法

### 运行程序

```bash
# 方法1: 直接运行主程序
python ai_chat_with_api.py

# 方法2: 使用启动器
python run_ai_chat.py
```

### 交互命令

| 命令 | 说明 |
|------|------|
| `help` | 显示帮助信息 |
| `save` | 保存当前对话到文件 |
| `config` | 显示当前配置状态 |
| `history` | 查看最近的对话历史 |
| `quit` | 退出程序 |

### 基本对话

直接输入你想说的话即可开始对话：
