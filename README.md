# ETHUSDT 永续五分钟提醒 · 免费测试版

状态：代码可本地测试；部署后须配置 Secrets/Variables 并手动验收。默认关闭通知和 AI。没有交易接口、Binance 账户密钥或自动下单功能。

## 数据与规则

只使用 `https://fapi.binance.com/fapi/v1/time` 和 `/fapi/v1/klines`，ETHUSDT USDⓈ-M 永续，5m/15m 各200根。以 Binance 服务器时间减2秒筛选已收盘K线；拒绝无效价格、非有限数、重复、断档、少于100根和过期数据。15m独立取最近已收盘数据。

EMA9/21以SMA初始化；RSI14和ATR14使用Wilder平滑；量比为当前成交量/之前20根均量。两个周期EMA同向，RSI符合区间（偏多5m 50–70/15m 50–75；偏空5m 30–50/15m 25–50），且5m量比≥1.2、ATR/收盘介于0.1%–3%时产生候选。其余为观察。仅方向改变时推送，30分钟冷却，每UTC日最多24条；并非每5分钟发送一条。规则未回测，不代表获利能力。

候选会调用离线 `review_candidate()` 占位接口，明确标注“AI复核未启用”。本版本无任何外部AI请求；设置AI_ENABLED=true直接失败。TradingCursor没有接入，也未假设它可在Actions调用。真实AI需要另行确认供应商、可调用接口、价格及独立批准后实施。

## 本地验收（Python 3.10+，无第三方依赖）

```sh
python3 -m unittest discover -s tests -v
python3 monitor.py --demo
python3 monitor.py --dry-run
```

`--dry-run` 请求真实公开行情但不读写状态、不发送Telegram。`--demo` 仅演示文字，非实时。

## Telegram：用户本人安全操作

1. 在官方Telegram客户端或 https://web.telegram.org/ 登录，寻找已验证的 @BotFather，发送 `/newbot`，按提示完成名字和username。
2. BotFather返回token。不要发到聊天、README、Issues、代码或截图；若泄露，在BotFather撤销并重新生成。
3. 打开自己的Bot，发送 `/start`。
4. 本机执行 `python3 telegram_setup.py`，在隐藏输入提示输入token，工具只列出私聊chat ID，不打印token。请在私人终端操作；不使用第三方查ID机器人。此脚本只读取getUpdates，不发送消息。
5. 仓库 Settings → Secrets and variables → Actions → Secrets，新建 `TELEGRAM_BOT_TOKEN` 与 `TELEGRAM_CHAT_ID`。两者都存为Secret。无须Binance API key或个人GitHub token。

## Actions启动步骤

独立**公开仓库**，默认分支main。复制全部项目文件（含隐藏的 `.github` 与 `.gitignore`）到根目录。

1. 确认仓库只授予可信写入者。工作流只支持schedule/manual，避免PR访问Secrets。
2. Settings → Actions → General，如权限策略阻止写入，允许该工作流使用Contents写权限（用于小型去重状态）。无需PAT。
3. Settings → Secrets and variables → Actions → Variables，配置：
   - `TRIAL_UNTIL`：UTC ISO时间，必须在未来7天以内，如 `2026-10-24T16:00:00Z`（例子可能过期，按实际启动日填写）。
   - `BOOTSTRAP_STATE`：设 `false`（仓库已初始化 `.state/state.json`）。状态丢失将失败关闭；仅全新部署且没有状态文件时临时设true，成功后恢复false。
   - `MONITOR_ENABLED`：最后设 `true`。暂停时设 `false`，或在Actions禁用工作流。
4. Actions → ETHUSDT free trial → Run workflow。确认测试通过、行情成功、`.state/state.json`出现；若无信号，日志显示No new eligible signal属正常，并不会发送测试交易信号。
5. 首条符合条件提醒到达后核对Bot/私聊/收盘时间；在此之前不能声称端到端验收成功。可在私人Telegram中通过BotFather管理Bot，但它不会替本项目测试通知。
6. 到期后脚本拒绝分析和发送；**仍需禁用workflow或将MONITOR_ENABLED=false停止启动runner**。延长试验需要用户主动修改日期，每次最多向后7天。

## 去重与故障语义

使用GitHub Contents API在默认分支写 `.state/state.json`，利用SHA条件更新阻止并发覆盖；工作流concurrency串行，不使用易失cache。状态只有时间、方向、计数和投递状态，无聊天ID/token。代码、日志和信号时间在公开仓库可见。

发送前必须成功持久化reservation。Telegram请求仅一次且显式关闭付费广播；成功后标记confirmed。网络超时或发送后写回失败，状态保留reserved：**可能漏发，不自动重试，避免重复**。这不是exactly-once保证。reserved需要人工核实；删除状态或开启bootstrap可能重发。程序不回补错过的历史信号。GitHub故障或写权限失败时不发送；Binance不可达、429/451时失败，不绕过区域限制，也不改用现货。

HTTP错误隐藏URL和响应体，避免Telegram URL泄露token；不在终端打开调试追踪。通过GitHub Actions失败通知关注故障；本项目无额外Telegram故障轰炸。

## 免费与限额

只在公开仓库的标准 `ubuntu-latest` runner运行；私有仓库在job层直接跳过。无大型runner、缓存、artifact存储、依赖安装、付费AI、付费Telegram广播或云资源。最长单次2分钟。每天理论288次，30天8640次；按每次约1分钟计，私人仓库可达8640分钟，不能将它视为免费。

公开仓库标准GitHub-hosted runner当前免费，但账户策略/价格可能变更；此程序无法设置账户级账单硬限额。部署前在GitHub Billing核实Actions预算，并开启“Stop usage when budget limit is reached”（若该SKU提供），不要添加付费runner/提高存储额度。通知上限和7天到期不等同于账户账单限额。用户未明确批准前不得启用付费功能。

cron `2-57/5 * * * *` 为UTC每小时2、7…57分，避开整点；GitHub schedule可延迟、丢失，不提供严格5分钟SLA。定时只从默认分支运行，公开仓库60天无活动可能被停用。若美国runner无法访问Binance衍生品端点（例如451），需要停止部署并另选合规执行环境；不要使用代理绕过。

## 已执行验证

8项离线单元测试涵盖已收盘过滤、断档/过期/NaN拒绝、EMA/RSI/ATR、双周期信号、去重/冷却/日上限、GitHub SHA更新、离线AI及错误密钥保护。本次本机真实行情测试因DNS无法解析 fapi.binance.com 未通过；Actions及Telegram端到端仍待验证。

## 官方参考

- [GitHub Actions计费](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [GitHub schedule行为](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [Binance衍生品文档](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data)
- [Telegram Bot API](https://core.telegram.org/bots/api#sendmessage)
