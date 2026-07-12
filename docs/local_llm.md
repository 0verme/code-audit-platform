# 本地大模型审计（雏形）

平台在任务页面启用“接入本地 AI 大模型”后，会在既有规则检查完成后，对最多 10 个候选 Python 或 SQL 文件追加语义审计。AI 结果只作为报告中的补充发现；当前版本不会改变规则引擎计算出的 `pass`、`warn` 或 `fail` 状态。

## 配置

在启动后端的环境中设置以下变量：

```powershell
$env:LOCAL_LLM_BASE_URL = "http://10.0.0.8:8000/v1"
$env:LOCAL_LLM_MODEL = "your-internal-model"
$env:LOCAL_LLM_API_KEY = ""                  # 内网网关不需要鉴权时可省略
$env:LOCAL_LLM_TIMEOUT_SECONDS = "30"        # 可省略，默认 30 秒
```

`LOCAL_LLM_BASE_URL` 应包含 `/v1`，服务需要提供与 OpenAI Chat Completions 兼容的 `POST /v1/chat/completions` 接口。

如果地址、模型、文件读取、网络请求或模型 JSON 输出任一环节不可用，AI 阶段会降级为空结果，主审计不会失败。

## Prompt 与输出约束

固定 Prompt 位于 `backend/audit/prompts/`：

- `python_review.txt`：Python 数据加工脚本；
- `sql_review.txt`：SQL/HQL 脚本；
- `generic_review.txt`：其他候选文件。

模型必须返回 JSON：`summary` 和 `findings`。每个 finding 使用 `severity`（`info`、`warn`、`err`）、`title`、`line_start`、`evidence`、`suggestion`、`confidence` 字段。源码会被限制为前 12,000 个字符，且 Prompt 明确要求把源码内容作为不可信数据处理。
