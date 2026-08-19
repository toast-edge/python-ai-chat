# 错误笔记：Qwen API 401 - Incorrect API key provided

> 记录时间：2026-08-05
> 触发场景：`python .\run_ai_chat.py` 选 qwen + 流式，输入"你是谁？"后报 401

---

## 一、原始报错

```
❌ Qwen API请求失败: Error code: 401 - {'error': {'message': 'Incorrect API key provided.
For details, see: https://help.aliyun.com/zh/model-studio/error-code#apikey-error',
'type': 'invalid_request_error', 'code': 'invalid_api_key'},
'request_id': '2e27db93-6cc1-99a3-8251-e0fcfbc017c2'}
```

## 二、根本原因

**API key 与请求端点不匹配**——key 是「阿里云百炼专属模型服务（MaaS 实例）」的凭证，但代码默认请求的是「通用 DashScope 端点」。

### 关键区分：两种阿里云服务

| 项 | 通用 DashScope | 百炼专属模型服务（本例） |
|---|---|---|
| 端点 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `https://<workspaceId>.cn-beijing.maas.aliyuncs.com/compatible-mode/v1` |
| key 前缀 | `sk-` + 一串 | `sk-ws-` + 签名 token（ws = workspace） |
| 模型名 | `qwen-max` / `qwen-plus` / `qwen-turbo` 等 | 该实例部署的模型 ID（如 `qwen3.7-max-2026-05-20`） |

### 出问题的地方

- [ai_chat_with_api.py:263](file:///f:/work-space/AI_GROUP/python-ai-chat/src/ai-api/ai_chat_with_api.py#L263)：`QwenClient` 默认 base_url 是通用端点 `https://dashscope.aliyuncs.com/compatible-mode/v1`
- [config.json](file:///f:/work-space/AI_GROUP/python-ai-chat/src/ai-api/config.json) 的 `qwen` 节点**只填了 api_key 和 model，没填 base_url**
- 于是拿着专属服务的 `sk-ws-...` key 去敲通用端点的门 → 服务端不认 → `401 invalid_api_key`

> 注：从 `sk-ws-` 前缀 + `MEUCIQC...` 签名段就能判断这是 workspace 专属凭证，不是通用 key。模型名 `qwen3.7-max-2026-05-20` 带版本日期，也是专属服务的命名风格，不在通用模型列表里。

## 三、修复

在 `config.json` 的 `qwen` 节点加上专属服务的 `base_url`（代码本身已支持从 config 读取，见 [ai_chat_with_api.py:511](file:///f:/work-space/AI_GROUP/python-ai-chat/src/ai-api/ai_chat_with_api.py#L511) `base_url=config.get("base_url")`）：

```json
"qwen": {
  "api_key": "sk-ws-...",
  "model": "qwen3.7-max-2026-05-20",
  "base_url": "https://llm-y67yca7aadrfdfrg.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
}
```

> 百炼专属服务会提供两个端点，OpenAI 兼容格式用 `compatible-mode/v1`：
> - openAiCompatible: `https://<workspaceId>.cn-beijing.maas.aliyuncs.com/compatible-mode/v1` ← 用这个（代码走 OpenAI SDK）
> - dashScope: `https://<workspaceId>.cn-beijing.maas.aliyuncs.com/api/v1`

## 四、验证

用 OpenAI SDK 发最小请求，返回正常：

```
base_url: https://llm-y67yca7aadrfdfrg.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
model   : qwen3.7-max-2026-05-20
OK! Qwen 回复: 您好，连接正常，随时为您服务。
```

修复后 `python .\run_ai_chat.py` 即可正常对话。

## 五、经验总结 / 避坑要点

1. **key 和端点必须配套**：阿里云有「通用 DashScope」和「百炼专属模型服务」两套，各自的 key、端点、模型名互不通用。看到 `sk-ws-` 前缀或带 `workspaceId` 的专属域名，一定要在 config 里配对应 base_url。
2. **看 key 前缀辨服务**：`sk-` 普通串多为通用 DashScope；`sk-ws-` + 签名 token 是 workspace 专属凭证。
3. **401 优先查端点**：拿到 401 invalid_api_key，先别急着换 key，先确认请求的 base_url 和 key 是否属于同一套服务。本例 key 一直有效，只是端点错了。
4. **config 字段要补全**：代码已支持 `base_url` 可配置，但 config 没填就会走默认值。新建配置时务必根据服务类型填全 `api_key` / `model` / `base_url` 三项。
5. **沙箱与外网**：测试请求需要访问阿里云外网端点，在 Trae 沙箱内会挂起/无输出，需禁用沙箱才能完成真实连通性测试。

## 六、相关文件

- [config.json](file:///f:/work-space/AI_GROUP/python-ai-chat/src/ai-api/config.json)（新增 qwen.base_url）
- [ai_chat_with_api.py](file:///f:/work-space/AI_GROUP/python-ai-chat/src/ai-api/ai_chat_with_api.py)（QwenClient，第 258-354 行）
