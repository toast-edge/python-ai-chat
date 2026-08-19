# 错误笔记：流式响应 list index out of range

> 记录时间：2026-08-05
> 触发场景：`python .\run_ai_chat.py` 选 qwen + 流式，AI 已完整回复后末尾报错

---

## 一、原始报错

```
AI助手: 正在思考...🤖 QwenClient: 你好！我是一个人工智能助手。...请问今天有什么我可以帮你的吗？❌ Qwen API请求失败: list index out of range
```

特征：**回复内容已完整输出**，错误紧跟在内容之后出现。

## 二、根本原因

[ai_chat_with_api.py](file:///f:/work-space/AI_GROUP/python-ai-chat/src/ai-api/ai_chat_with_api.py) `QwenClient.get_streaming_response` 的流式循环：

```python
for chunk in stream:
    if chunk.choices[0].delta.content is not None:   # ← 这里崩
        content = chunk.choices[0].delta.content
        full_response += content
        yield content
```

OpenAI 兼容的流式协议中，**某些 chunk 的 `choices` 是空列表 `[]`**——典型是流末尾携带 usage 统计的 chunk。当遍历到这种 chunk 时，`chunk.choices[0]` 直接 `IndexError: list index out of range`。

由于内容在前面的 chunk 里已经全部 yield 完了，只有最后这个空 choices chunk 触发异常，被 `except Exception` 捕获后 `yield` 出错误信息——所以表现为「完整回复 + 末尾报错」。

## 三、实测确认

写了流式测试脚本逐 chunk 打印，结果：

```
我是通义千问，由阿里巴巴通义实验室自主研发的超大规模语言模型……
[info] 跳过空 choices chunk（确认存在此类 chunk）

遇到的空 choices chunk 数: 1
```

证实：阿里云兼容模式在流末尾确实发了 1 个 `choices: []` 的 chunk。

## 四、修复

在循环开头跳过空 choices 的 chunk：

```python
for chunk in stream:
    # 跳过空 choices 的 chunk（如末尾携带 usage 统计的 chunk），
    # 否则 chunk.choices[0] 会抛 IndexError: list index out of range
    if not chunk.choices:
        continue
    if chunk.choices[0].delta.content is not None:
        content = chunk.choices[0].delta.content
        full_response += content
        yield content
```

修复后流式测试全程无异常，内容完整。

## 五、经验总结 / 避坑要点

1. **「内容已返回 + 末尾报错」是流式空 choices 的典型信号**：如果回复本身完整，错误只在末尾冒出来，优先怀疑流末尾的 usage/结束 chunk 被当成正常 chunk 处理了。
2. **访问 `chunk.choices[0]` 前必须判空**：OpenAI 流式协议允许 `choices: []`（尤其开启 `stream_options.include_usage` 或某些服务端实现总会附带 usage chunk）。标准写法是 `if not chunk.choices: continue`。
3. **异常被 yield 会混进正常输出**：本例 `except` 里 `yield` 错误字符串，导致错误信息和正常回复黏在一起，不易定位。生产代码里更好做法是用一个标志位区分正常内容与错误，或把错误通过独立通道抛出。
4. **写最小复现脚本是诊断利器**：脱离交互式主程序，直接用 OpenAI SDK 逐 chunk 打印，立刻看出哪个 chunk 结构异常。

## 六、相关文件

- [ai_chat_with_api.py](file:///f:/work-space/AI_GROUP/python-ai-chat/src/ai-api/ai_chat_with_api.py)（`QwenClient.get_streaming_response`，第 311-354 行；修复在第 343-348 行）
