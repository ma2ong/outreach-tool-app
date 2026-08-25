# 46 — Historical Reply Integrity / 历史自动回复误判修复

## 背景

PR #13 已经阻止新的邮件自动回复被当成真人回复，但旧数据库仍可能保留历史误判。
真实生产核验里，EIDIM 已经有一条新的 `kind='auto'` 记录，同时旧版留下的同一封
`hello+noreply@eidim.com` 邮件仍是 `kind='reply'`；这让 `outreach.status='replied'`、
reply task 和 reply-sourced noreply contact 继续存在。

## 原则

1. **默认只预览。** 维护脚本不接入 Worker、startup 或任何自动周期；只有显式
   `--apply` 才写库。
2. **只修强证据。** 可自动修复的历史 reply 必须满足当前 autoresponder 规则，且至少
   有一个强证据：发件地址本身是 noreply/send-only，或数据库里已经存在同一封邮件的
   `kind='auto'` 版本。仅靠正文措辞命中的记录只报告，不自动改。
3. **真人回复优先。** 如果同一 lead/channel 还存在其他 `reply` 或 `unsubscribe`，只修
   这封机器邮件本身，不回退该客户的 replied 状态，也不重开序列。
4. **保留审计。** 对应 reply activity 改为 `cancelled` 而不是删除，并附上修复原因。
   若已有重复 auto inbox row，则合并成一条后再把旧 reply row 转为 auto，避免唯一索引冲突。
5. **联系人只删机器地址。** 只删除 `source='reply'`、非 primary、邮箱与误判发件人完全一致、
   且邮箱明确是 noreply/send-only 的联系人。manual/legacy/primary 联系人绝不自动删。
6. **Outreach 回退必须可证明。** 只有不存在其他真人邮件、当前 email outreach 确实是
   `replied`、`reply_received=0` 且存在强证据时，才回到 `messaged`；touch_count 和最后发送
   日期保持不变。
7. **序列恢复留缓冲。** 仅在上述 outreach 安全回退成立时，将同 channel、状态为
   `replied` 的 enrollment 恢复为 active；如果 next_due_date 已过，至少推到明天，避免维护
   命令执行后立刻触发一封邮件。
8. **Stage 不自动回退。** `leads.stage='replied'` 可能由人工设置，缺少可证明来源，因此维护
   工具只报告并保留 stage，不猜。

## CLI

```text
python -m app.fix_historical_auto_replies
python -m app.fix_historical_auto_replies --apply
```

数据库路径遵循 `OUTREACH_DB` / `app.main_deps.DB_PATH`。

## 验证

- EIDIM 形状：旧 reply + 新 auto duplicate + noreply contact + reply task + stopped sequence。
- preview 不写任何数据。
- apply 后只保留 auto inbox、reply task cancelled、机器联系人移除、outreach 回到 messaged、
  sequence 安全恢复，stage 保留。
- 如果还有另一封真人 reply，则绝不回退 outreach/sequence。
- 文本措辞命中但没有 noreply/duplicate-auto 强证据的候选只报告，不自动修。
