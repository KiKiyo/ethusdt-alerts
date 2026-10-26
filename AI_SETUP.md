# OpenAI候选复核配置（未启用）

用户授权：配置OpenAI，但不开启付费调用。当前两条工作流都硬编码AI_ENABLED=false、AI_PAID_APPROVED=false；仅添加密钥不会开启调用。没有创建API密钥、购买额度或发出真实OpenAI API请求。现有免费规则提醒继续工作。

## 已配置的模型与接口

- 模型：gpt-5.4-mini-2026-03-17，固定快照，禁止通过环境变量任意换为更贵模型。
- API：https://api.openai.com/v1/responses；只连接OpenAI官方域名，不跟随重定向。
- 输入：OKX ETH-USDT-SWAP、候选多空方向、收盘时间、5m/15m EMA9/21、RSI14、ATR14、收盘价和量比。只允许指定数字字段，不发送Telegram密钥、聊天ID、个人持仓或GitHub令牌。
- 输出：严格JSON，accept/reject、normal/elevated/high风险和简短中文说明；模型不能改变候选方向。没有联网搜索、工具调用或下单功能，store=false。
- 仅去重/冷却/日提醒上限筛选通过的新候选才可能调用。dry-run、单元测试和普通观察周期不调用模型。
- 在持久化调用次数后才请求API；最多每UTC日3次、该状态生命周期累计9次，单次最多1200输出token（含推理）；不自动重试，超时25秒。失败尝试也消耗次数。
- 高风险、reject、拒答、截断、错误或达到调用限额均暂扣提醒，不降级为声称AI已认可的信号。候选和冷却已预留，可能错过后续同方向候选；不保证每个规则候选都送达。

## 密钥安全配置（可暂不执行）

若已有OpenAI API密钥，可直接在 https://github.com/KiKiyo/ethusdt-alerts/settings/secrets/actions → New repository secret 保存：名称 OPENAI_API_KEY，值为自己的密钥。不要发到聊天、Issue、代码、截图或cron-job.org。只需告知“Secret已保存”，不要提供密钥内容。

没有密钥时，可在 https://platform.openai.com/api-keys 创建独立项目密钥；无需现在充值或开启自动充值。若页面要求购买额度，暂停，所有付费步骤需另行明确批准。当前无需创建密钥即可完成离线配置。

## 后续付费启用边界

启用前需向用户说明模型、单价、调用次数上限、试用日期及发送给OpenAI的数据，并单独取得明确付费授权。之后才能修改两条工作流的AI_ENABLED与AI_PAID_APPROVED；单独添加GitHub Variable不会绕过代码中的关闭状态。启用后才做一次真实API验收（计入持久化次数），现阶段尚未验证账户访问、额度和真实模型响应。

不要清空.state/state.json或重置ai_total_calls来绕过累计限额。此限额仅约束本程序，不能约束其他程序对同一API密钥的消费，也不是账户账单硬封顶。试用到期TRIAL_UNTIL仍会先停止分析和调用。

## 费用参考与验证

2026-10-25核对官方文档，标准文本输入每百万token $0.75，输出每百万token $4.50（美元）。例如一次1000输入、1200输出约$0.00615；实际取决于用量、服务定价及税费，不是获准消费的预算。

本地25项测试通过，使用模拟API响应，覆盖付费开关、调用前持久化、失败不重试、日/累计限额、字段白名单、拒答/截断/错误输出、AI拒绝/高风险暂扣及dry-run零付费调用。真实API未调用，模型的信号改善效果未经回测。

- https://developers.openai.com/api/docs/models/gpt-5.4-mini
- https://developers.openai.com/api/docs/guides/structured-outputs
