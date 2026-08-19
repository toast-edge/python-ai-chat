# 错误笔记：ModuleNotFoundError: No module named 'langchain_text_splitters'

> 记录时间：2026-08-05
> 触发场景：运行 `python .\run_ai_chat.py`，选择 qwen + 流式响应后崩溃

---

## 一、原始报错

```
Traceback (most recent call last):
  File "...\src\ai-api\ai_chat_with_api.py", line 16, in <module>
    from rag_manager import RAGManager
  File "...\src\ai-api\rag_manager.py", line 11, in <module>
    from langchain_text_splitters import RecursiveCharacterTextSplitter
ModuleNotFoundError: No module named 'langchain_text_splitters'
```

## 二、根本原因

1. `rag_manager.py` 顶层（第 11 行）写了：
   ```python
   from langchain_text_splitters import RecursiveCharacterTextSplitter
   ```
   这是 **模块级 import**，只要 `ai_chat_with_api.py` 第 16 行 `from rag_manager import RAGManager` 被执行，就会立刻触发这一行 import。

2. 当前 Python 环境（`D:\environment\python.exe`，Python 3.12.4）**没有安装** `langchain-text-splitters` 这个包。

3. 根因其实是：项目根目录的 `requirements.txt` **根本没有列出任何 langchain 系列 RAG 依赖**，只有 openai、anthropic、pydantic、requests 等基础包。所以新环境 `pip install -r requirements.txt` 之后，RAG 相关代码必然 import 失败。

4. `rag_manager.py` 不仅缺 `langchain-text-splitters`，还同时引用了：
   - `langchain_community.document_loaders`（TextLoader / PyPDFLoader / Docx2txtLoader / UnstructuredMarkdownLoader）
   - `langchain_community.embeddings.HuggingFaceEmbeddings`
   - `langchain_community.vectorstores.FAISS`
   - `langchain_core.documents.Document`

   这些都需要对应包安装后才能运行 RAG 功能。

## 三、修复步骤

### 1. 安装核心 import 依赖（解决当前报错，让程序能启动）

```powershell
python -m pip install langchain-text-splitters langchain-community langchain-core faiss-cpu pypdf docx2txt
```

装完后版本（参考）：
- langchain-text-splitters==1.1.2
- langchain-community==0.4.2
- langchain-core==1.5.3
- faiss-cpu==1.15.0
- pypdf==6.14.2
- docx2txt==0.9

### 2. 安装 RAG 真正检索时需要的依赖（实例化 RAGManager 后会用到）

```powershell
python -m pip install sentence-transformers
```

> 用途：`VectorStoreManager.__init__` 里 `HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")`
> 需要它来加载 embedding 模型。这个包会带上 torch，体积较大，安装较慢。

### 3.（可选）支持 `.md` 的 UnstructuredMarkdownLoader

```powershell
python -m pip install unstructured
```

> 如果不加载 markdown 文档，可以不装。

### 4. 更新 `requirements.txt`

把上述依赖补进项目根目录的 `requirements.txt`，避免下次重建环境时再次踩坑。

## 四、验证

```powershell
cd f:\work-space\AI_GROUP\python-ai-chat\src\ai-api
python -c "from rag_manager import RAGManager; print('OK')"
```

能打印 `OK` 即说明 import 链已修复，`python .\run_ai_chat.py` 即可正常进入服务选择菜单。

## 五、经验总结 / 避坑要点

1. **模块级 import 是硬依赖**：哪怕功能（如 RAG）暂时不用，只要 import 触发就会要求包存在。如果想让某功能真正“可选”，应改成**函数内延迟导入（lazy import）**，把 import 挪到使用它的方法体内部。
2. **requirements.txt 要与代码同步**：新增任何第三方 import 后，必须同步更新 `requirements.txt`，否则换环境必崩。
3. **看报错先看链路**：`ai_chat_with_api.py → rag_manager.py → langchain_text_splitters`，顺着 import 栈一层层往下看，最后那个 `ModuleNotFoundError` 就是真正缺失的包。
4. **区分“能启动”和“能用”**：装核心 langchain 包让程序能启动；但要真正使用 RAG 检索，还需要 `sentence-transformers`（embedding）和 `faiss-cpu`（向量库）等。
5. **PowerShell 下的 pip 输出**：pip 把进度写到 stderr，PowerShell 会把它当成 `NativeCommandError`，但只要最后出现 `Successfully installed ...` 就说明安装成功，可忽略该红色提示。

## 六、相关文件

- [rag_manager.py](file:///f:/work-space/AI_GROUP/python-ai-chat/src/ai-api/rag_manager.py)（第 11 行报错点）
- [ai_chat_with_api.py](file:///f:/work-space/AI_GROUP/python-ai-chat/src/ai-api/ai_chat_with_api.py)（第 16 行触发 import）
- [requirements.txt](file:///f:/work-space/AI_GROUP/python-ai-chat/requirements.txt)（缺失依赖应补在此处）
