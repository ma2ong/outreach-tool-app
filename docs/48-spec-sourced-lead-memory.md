# 48 — Sourced Lead Memory / 可追溯客户记忆

## 目标

旧的 `lead_memory.summary` 是一段最多约 200 字符的散文，每次客户回复后整段重写。这个结构会静默遗忘旧事实，也无法回答“这条记忆来自哪封邮件”。

本规范把客户记忆改成一组独立、可追溯、可退休的事实条目，同时保留 `summary` 作为向后兼容的渲染视图。

## 规则

### R1 — 记忆是一组条目，不是一次次重写的散文

`lead_memory_items` 每条包含：

- `kind`: `profile`（长期）或 `log`（阶段性）；
- `content`: 单条事实，最多 500 字符；
- `origin`: `explicit`（销售人员明确写入）或 `synthesized`（Agent 从往来合成）；
- `evidence`: `inbox:<id>` / `note:<id>` 来源；
- `superseded_at`: 被新证据推翻或人工退休时填写，不物理删除。

模型只返回 `create / update / remove` 的增量变化。未被提到的旧条目必须保持不变。

### R2 — Agent 合成的事实必须有真实出处

每个 synthesized create/update/remove 都必须引用真实存在的 `inbox_messages` 或 `notes` ID。不存在、格式错误或空 evidence 的变更整条拒绝，不能把无来源猜测混入客户事实。

### R3 — 人工明确记忆拥有更高权限

`origin='explicit'` 的条目可以被 Agent 读取和用于上下文，但 Agent 不得 update/remove。只有人工 API/UI 可以退休这类条目。

### R4 — 不推断客户没说过的事实

不得把沉默解释为没兴趣，不推断动机或敏感属性。带日期的计划过期后可以表述为“曾计划”，但不能推断计划已发生。

### R5 — 保留历史，不做硬删除

remove/人工“删除”都只写 `superseded_at`。当前 summary 只由未退休条目渲染，因此历史可审计但不会继续影响下一封消息。

### R6 — 有界增长

单次合成最多 12 个变更；单个客户最多 40 个有效条目。超过上限时只自动退休最旧的 synthesized `log`，长期 profile 和人工 explicit 不因容量自动消失。

### R7 — 向后兼容

`proposals.get_memory(...)["summary"]` 继续存在，`draft.py` 不需要知道底层存储已经从散文变成条目。若一次合成全部被拒绝，不能用空 summary 覆盖已有旧记忆。

### R8 — 客户抽屉可见、可写、可退休

客户抽屉显示当前记忆，并区分：

- “我记的” — explicit；
- “Agent 从往来里总结” — synthesized。

人工可新增长期/阶段性记忆并退休任何当前条目。Agent 合成的自动更新仍只发生在真实客户互动的现有 memory update 路径中。

## API

- `GET /api/agent/memory/{lead_no}` — summary + 当前 items；
- `POST /api/agent/memory/{lead_no}` — 新增 explicit item；
- `DELETE /api/agent/memory/{lead_no}/{item_id}` — 退休 item，不物理删除。

## 安全边界

- 本功能不新增客户发送路径；
- 不修改 CRM stage、报价、付款、交期或订单；
- LLM 不可修改人工 explicit 记忆；
- 无有效 evidence 的 synthesized 事实不得落库；
- 模型不可用时，记忆更新失败不能阻塞客户回复流程。

## 验证

测试至少覆盖：

1. 未被模型提到的条目不会消失；
2. 不存在的 evidence 被拒绝；
3. note/inbox evidence 均可验证；
4. explicit 条目拒绝 Agent update/remove；
5. superseded 条目仍保留历史但不进入 summary；
6. 变更数/条目数有上限；
7. LLM 不可用时保留已有记忆；
8. API 可新增/读取/退休人工记忆；
9. frontend production build 与完整后端测试通过。
