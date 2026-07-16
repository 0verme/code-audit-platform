# P0-S2D 元数据快照日期与新鲜度设计

## 1. 设计原则

1. 审计平台不强依赖资产门户是否部署；资产门户可作为展示或跳转入口，但不应成为审计任务运行的前置条件。
2. 审计平台依赖本地元数据快照。本地快照是 `audit_metadata_service.py` 和 `re_service.py` 中增强检查、血缘补充、来源系统标注等能力的输入。
3. 元数据快照必须展示 `data_date` 和 `synced_at`，分别说明快照对应的业务日期和本地同步完成时间。
4. 定时任务失败时，审计报告必须能看出当前实际使用的是哪天的数据，避免旧快照被静默当作最新数据使用。
5. 元数据过期不应静默通过。即使第一阶段不中止扫描，也必须在报告和页面中显式提示。
6. 关键元数据缺失时，报告应给出 `error` 或强 `warning`，并标明受影响的检查项或增强能力。
7. 第一阶段只做设计，不修改同步脚本、数据库结构、业务代码、配置文件，也不执行数据库迁移。

## 2. 元数据范围

本设计覆盖当前审计平台已依赖的本地元数据能力，第一阶段先盘点并定义统一快照标识，不调整现有查询逻辑。

| 依赖能力 | 所在模块 | 当前用途 | snapshot_name |
| --- | --- | --- | --- |
| `list_term_roots` | `audit_metadata_service.py` | 词根或统一资产表命名相关检查，用于判断 SQL 中识别到的表是否命中已有词根。 | `term_roots` |
| `list_upstream_system_ids` | `audit_metadata_service.py` | 有效上游系统 ID，供调度接入计划判断使用。 | `upstream_system_ids` |
| `list_job_outfiles` | `audit_metadata_service.py` | 作业到下游 outfile 的映射，供宽表链路和结果表输出补充使用。 | `job_outfiles` |
| `list_result_table_sys_names` | `audit_metadata_service.py` | 结果表到来源系统名称的映射，用于报告中标注结果表来源系统。 | `result_table_sys_names` |
| `build_wide_table_lineage_summary` | `re_service.py` | 聚合结果表、作业、recv plan、来源系统、outfile、统计信息和 warnings，形成宽表血缘摘要。 | `wide_table_lineage` |

补充说明：

- `build_wide_table_lineage_summary` 本身是聚合能力，依赖 `job_outfiles` 和 `result_table_sys_names` 等底层元数据。报告展示时可以保留 `wide_table_lineage` 作为聚合快照项，同时在 `items` 中列出其底层依赖项状态。

## 3. 字段定义

统一快照状态记录建议使用以下字段。第一阶段仅定义语义，后续 P0-S2H 再决定落表结构、索引和写入方式。

| 字段 | 类型建议 | 含义 |
| --- | --- | --- |
| `snapshot_name` | string | 快照类型标识，例如 `term_roots`、`job_outfiles`、`wide_table_lineage`。同一批同步中每类元数据一条状态记录。 |
| `data_date` | date/string | 元数据对应的业务日期。示例：同步 2026-07-04 的生产元数据快照，则 `data_date` 为 `2026-07-04`。这是判断审计报告使用哪天数据的核心字段。 |
| `synced_at` | datetime/string | 本地定时任务同步完成时间。示例：`2026-07-05 02:15:31`。用于判断同步是否按时完成，不等同于业务日期。 |
| `status` | enum/string | 同步或快照状态，取值建议为 `success`、`stale`、`missing`、`failed`、`unknown`。 |
| `row_count` | integer | 本地快照行数。用于发现空快照、异常少量数据、同步截断等问题。 |
| `source_max_update_time` | datetime/string | 源端数据最大更新时间。用于判断生产端元数据本身是否更新，以及区分源端未更新和本地同步失败。 |
| `snapshot_batch_id` | string | 同步批次号。建议包含快照业务日期和同步时间，例如 `metadata_20260704_021531`，用于串联同一轮多类元数据快照。 |
| `error_message` | string | 同步失败或状态异常的脱敏错误摘要。不得包含完整账号、密码、token、连接串、内网 IP 等敏感内容。 |
| `created_at` | datetime/string | 快照状态记录创建时间。 |
| `updated_at` | datetime/string | 快照状态记录最后更新时间。同步重试或状态修正时更新。 |

重点区分：

- `data_date` 表示这份元数据反映的业务日期，是报告判断“用的是哪天元数据”的依据。
- `synced_at` 表示本地同步任务完成时间，是判断定时任务是否按时跑完的依据。
- `source_max_update_time` 表示源端数据最大更新时间，可辅助判断源端是否已经产生新数据。
- `snapshot_batch_id` 表示同步批次，便于把各类快照状态、日志和报告追踪到同一次同步。

## 4. 状态定义

### 4.1 快照状态 `status`

| status | 含义 |
| --- | --- |
| `success` | 快照同步成功，存在可用状态记录，且数据行数和基础校验通过。 |
| `stale` | 存在快照记录，但 `data_date` 落后于预期日期，或超过配置的新鲜度阈值。 |
| `missing` | 查不到对应 `snapshot_name` 的快照状态记录，或关键快照表为空且无法确认同步成功。 |
| `failed` | 同步任务明确失败，存在失败状态或脱敏错误摘要。 |
| `unknown` | 无法判断状态，例如历史数据未接入控制表、字段缺失、状态枚举无法识别。 |

### 4.2 报告新鲜度 `freshness_status`

报告层建议收敛为四类状态，便于前端和用户理解。

| freshness_status | 判断规则 | 报告影响 |
| --- | --- | --- |
| `ok` | 所有核心快照 `status=success`，且 `data_date` 等于预期日期。 | 正常扫描，报告展示快照日期和同步时间。 |
| `stale` | 至少一个核心快照 `data_date` 落后预期日期 1 天以上，或状态为 `stale`。 | 继续扫描，但报告强提示“元数据已过期”。 |
| `missing` | 任一关键元数据查不到快照记录，或状态为 `missing`。 | 继续扫描或跳过相关增强检查，报告给出 `error`。 |
| `failed` | 任一核心元数据同步任务明确失败，或状态为 `failed`。 | 第一阶段继续扫描，但报告给出 `error`；是否中止由后续配置决定。 |

建议判断优先级：`failed` > `missing` > `stale` > `ok`。如果存在 `unknown`，第一阶段建议按强 `warning` 处理；若该元数据属于核心能力且影响关键检查，可提升为 `missing`。

预期日期建议由审计任务运行日期和业务调度规则计算。常见模式是审计任务在 2026-07-05 运行时，预期元数据业务日期为 2026-07-04。

## 5. 报告结构建议

审计报告顶层新增 `metadataSnapshot` 字段，用于记录本次扫描实际使用的元数据快照状态。

```json
{
  "metadataSnapshot": {
    "data_date": "2026-07-04",
    "synced_at": "2026-07-05 02:15:31",
    "snapshot_batch_id": "metadata_20260704_021531",
    "freshness_status": "ok",
    "items": []
  }
}
```

`items` 建议包含各类 `snapshot_name` 的状态，示例：

```json
{
  "metadataSnapshot": {
    "data_date": "2026-07-04",
    "synced_at": "2026-07-05 02:15:31",
    "snapshot_batch_id": "metadata_20260704_021531",
    "freshness_status": "stale",
    "items": [
      {
        "snapshot_name": "term_roots",
        "data_date": "2026-07-04",
        "synced_at": "2026-07-05 02:15:31",
        "status": "success",
        "freshness_status": "ok",
        "row_count": 1280,
        "source_max_update_time": "2026-07-04 23:58:12",
        "snapshot_batch_id": "metadata_20260704_021531",
        "message": ""
      },
      {
        "snapshot_name": "job_outfiles",
        "data_date": "2026-07-03",
        "synced_at": "2026-07-04 02:15:08",
        "status": "stale",
        "freshness_status": "stale",
        "row_count": 8492,
        "source_max_update_time": "2026-07-03 23:57:40",
        "snapshot_batch_id": "metadata_20260703_021508",
        "message": "元数据快照落后预期日期 1 天，outfile 和宽表血缘结果可能不完整。"
      }
    ]
  }
}
```

字段约束：

- 顶层 `metadataSnapshot.data_date` 可取核心快照中的最小 `data_date`，用于保守展示“本报告最旧依赖数据日期”。
- 顶层 `metadataSnapshot.synced_at` 可取对应最小 `data_date` 项的 `synced_at`，或展示最新批次同步时间；具体规则需在 P0-S2F 实现前固定。
- `error_message` 不建议直接进入报告；报告可使用脱敏后的 `message`，避免暴露连接信息或内部环境细节。

## 6. 页面展示建议

审计结果页应在报告摘要区展示元数据快照状态，避免用户只看到审计通过或告警数量，却不知道元数据是否过期。

正常状态：

```text
元数据快照：2026-07-04
同步时间：2026-07-05 02:15
状态：正常
```

过期状态：

```text
元数据快照：2026-07-03
同步时间：2026-07-04 02:15
状态：已过期 1 天
```

缺失状态：

```text
元数据快照：未知
状态：缺失，相关检查结果可能不可信
```

展示建议：

- `ok` 使用普通信息提示，不抢占主要问题列表。
- `stale` 使用强 warning 样式，并展示落后天数。
- `missing` 和 `failed` 使用 error 样式，并提示受影响的能力，例如词根检查、outfile 补充、宽表血缘。
- `items` 可折叠展示，默认展示总体状态和最旧 `data_date`，展开后查看每类 `snapshot_name` 明细。

## 7. 扫描行为建议

| freshness_status | 第一阶段扫描行为 | 报告要求 |
| --- | --- | --- |
| `ok` | 正常扫描。 | 展示快照日期、同步时间和批次号。 |
| `stale` | 继续扫描。 | 强提示元数据过期，标明落后天数和受影响快照项。 |
| `missing` | 继续扫描，或跳过依赖该快照的增强检查。 | 报告 `error`，说明相关检查结果可能不可信或不完整。 |
| `failed` | 核心元数据失败时第一阶段仍继续扫描。 | 报告 `error`，说明同步失败；是否中止扫描留给后续配置决定。 |

第一阶段建议不直接中止扫描，原因是当前服务已有空列表降级和 warning 降级行为，贸然中止会改变现有任务可用性。但必须把风险写入报告，尤其是以下场景：

- 词根快照缺失时，词根缺失类检查结果可能大量误报或漏报。
- `job_outfiles` 缺失或过期时，下游 outfile 和宽表血缘补充可能不完整。
- `upstream_system_ids` 缺失或过期时，上游系统计划相关判断可能不可信。
- `result_table_sys_names` 缺失或过期时，结果表来源系统标注可能不完整。
- `wide_table_lineage` 聚合依赖项异常时，血缘摘要应保留基础扫描结果，但必须附带强 warning 或 error。

## 8. 后续实施路线

| 阶段 | 目标 | 交付物 |
| --- | --- | --- |
| P0-S2D | 完成元数据快照日期与新鲜度设计。 | 本设计文档。 |
| P0-S2E | 新增读取元数据快照状态的 service。 | 只读服务，返回统一字段和 `freshness_status`。 |
| P0-S2F | 审计报告追加 `metadataSnapshot`。 | 报告 JSON 包含总体状态和 `items` 明细。 |
| P0-S2G | 结果页展示元数据快照状态。 | 页面摘要区展示正常、过期、缺失、失败状态。 |
| P0-S2H | 同步脚本写入快照控制表。 | 同步批次、行数、业务日期、同步时间、错误摘要入库。 |
| P1 | 支持过期阈值配置和强制中止策略。 | 可配置 freshness 阈值、核心元数据失败时是否中止扫描。 |

实施顺序建议：

1. 先做只读状态服务，避免同步脚本和报告结构同时变化。
2. 再把状态附加到审计报告，保证离线报告也能自描述使用了哪天元数据。
3. 最后改页面展示和同步脚本写入，减少一次性变更范围。

## 9. 安全要求

1. 不打印完整账号、密码、token、连接串、内网 IP。
2. 如果发现疑似敏感内容，只写“发现疑似敏感配置/连接信息”，不要展开。
3. 不修改业务代码。
4. 不修改配置。
5. 不执行数据库迁移。
6. 不安装依赖。
7. 不启动服务。
8. 不格式化无关文件。
9. 如果开始实施前已有脏文件，停止并汇报。

本轮 P0-S2D 仅新增设计文档，不涉及业务代码、同步脚本、配置文件、数据库结构或运行时行为变更。
