# CryptoBlower · OKX ETH-USDT 永续每5分钟候选提醒

使用 **OKX ETH-USDT-SWAP USDT本位永续**公开行情，每5分钟筛选一次候选信号；只有符合规则的新候选才向 @CryptoBlower_bot 私聊发送提醒。行情和信号与Binance可能不同。没有自动下单。OpenAI GPT-5.4 mini已获用户批准启用条件复核，仅新的合格候选才调用；普通观察、重复信号和冷却期不调用。每天最多3次、累计最多9次，达到限额即停止；当前累计已用2次尝试，剩余7次。没有创建额外付费资源；配置和限额见 [AI_SETUP.md](AI_SETUP.md)。

2026-10-25已修复外部调度：cron-job.org定时触发GitHub Actions，原生GitHub schedule保留为备用。当前试运行截止 **2026-10-28T22:00:00Z（多伦多10月28日18:00）**，届时外部任务停止，程序也停止分析和发送。调度短期令牌10月29日到期；续期或付费步骤须另行确认。已验证多伦多时间20:36、20:41连续两轮真实自动分析成功；当前无新候选，按规则静默。具体配置及验收见 [EXTERNAL_SCHEDULER.md](EXTERNAL_SCHEDULER.md)。免费调度和GitHub排队可能延迟，不承诺严格每300秒执行。

## 提醒怎么读

Telegram提醒已改用中文解释：先给上涨/下跌方向候选和5分钟收盘参考价，再解释两个周期走势、成交量和平均波幅；不再堆叠EMA、RSI、ATR缩写。时间统一为America/Toronto并自动处理夏令时。平均波幅是历史计算值，不是目标价或止损价。筛选、去重和冷却规则不变。AI未实际复核时会明确标注；密钥已保存也不代表付费开关已启用。

## 筛选规则

EMA9/21以SMA初始化，RSI14和ATR14用Wilder平滑。5m/15m EMA同向，偏多RSI分别50–70/50–75，偏空30–50/25–50；5m量比（本根/之前20根均量）≥1.2，ATR/收盘介于0.1%–3%。其余静默观察。只有候选方向改变才通知，30分钟冷却，每UTC日最多24条。冷却期间出现且持续不变的候选可能被抑制。规则未经回测，不保证建仓适合性或盈利，不考虑用户资金和持仓。

以OKX服务器时间减2秒判断收盘；拒绝过期、重复、断档、NaN及无效数据。保留1m函数和runner作为未启用的旧版工具，当前云端运行不调用它们。

## 行情来源和收盘校验

只请求OKX官方公开GET接口：www.okx.com/api/v5/public/time、/api/v5/public/instruments（SWAP/ETH-USDT-SWAP）、/api/v5/market/candles（5m/15m各200根）。校验合约state=live、ctType=linear、settleCcy=USDT，不需要账户或API密钥。

OKX数据由新到旧，适配器排序为旧到新，只接收confirm=1的已完成K线，并同时以交易所时间减2秒过滤；仍拒绝断档/重复/过期/NaN。成交量字段vol为合约张数，量比比较同一合约历史张数，不能与Binance的ETH成交量混用。通知和去重ID包含OKX交易所标识。行情失败时不静默切换交易所。

此前Binance在Actions返回HTTP451和restricted-location，保留diagnose.yml供历史诊断；已不用Binance接口生成信号，没有使用代理/测试网/现货冒充永续。

## 验证（Python 3.10+，无第三方依赖）

```sh
python3 -m unittest discover -s tests -v
python3 monitor.py --demo
python3 monitor.py --dry-run
```

25项本地离线测试（包含8项新增AI接入测试）覆盖指标、双周期与保留的1m确认、已收盘筛选、断档/过期/NaN、去重/冷却/日上限、状态持久化和文件权限、GitHub条件更新、离线AI及密钥错误保护。OKX真实行情、Telegram测试投递和历史候选投递均已在Actions通过。自动调度的最新验收见上方链接。

## Telegram安全配置

机器人 @CryptoBlower_bot。用户已发送/start，GitHub Secret名为 `TELEGRAM_CRYPTOBLOWER_TOKEN`，工作流将其映射为程序环境变量TELEGRAM_BOT_TOKEN。密钥不要发送到聊天、代码、Issue、日志或截图。`TELEGRAM_CHAT_ID` Secret也已配置并验证。以下步骤供重新部署时使用。

推荐：Actions手动运行“Telegram private connection test”。它验证机器人为@CryptoBlower_bot，且过去24小时只有一个私聊发送/start时才发送一次连接测试，将chat ID仅发到该私聊，公开日志不包含token/ID。若零个或多个私聊候选则拒绝发送。将私聊里收到的数字直接存为TELEGRAM_CHAT_ID Secret，不在聊天或公开仓库粘贴。

也可在私人本机终端执行 `python3 telegram_setup.py`，在隐藏提示中输入BotFather token，读取自己Bot的getUpdates并查看私聊ID；不要使用第三方查ID服务。将自己的ID存入TELEGRAM_CHAT_ID。该脚本不发送消息。创建机器人可在官方Telegram通过已验证@BotFather的/newbot完成。泄露token后从BotFather撤销。

## Actions五分钟部署

仅允许独立公开仓库标准ubuntu-latest，私有仓库job跳过；不使用付费runner、artifact或cache。单次最长2分钟。配置Secrets如上；Variables为TRIAL_UNTIL（未来7天内）、BOOTSTRAP_STATE=false（仓库已初始化.state/state.json）、MONITOR_ENABLED=true（当前已启用）。分析工作流使用GITHUB_TOKEN的Contents写权限保存去重状态；外部调度另需单仓库、Actions读写的短期PAT，详见调度文档。不需要交易账户密钥。到期脚本不发通知，但仍应禁用workflow或设MONITOR_ENABLED=false停止runner启动。

公开仓库标准runner目前免费；账户级预算未由本项目设置，用户需在Billing核实并设置可用的预算停止选项。通知上限不等于账单硬限额。理论5分钟每天288次、30天8640次，不能将私人仓库按此频率运行视作免费。

## 投递与故障

发送前必须持久化reserved状态；Actions使用GitHub Contents SHA条件更新及concurrency串行，本机用锁及原子文件。发送仅尝试一次，显式allow_paid_broadcast=false；成功后写confirmed。超时或发送后写回失败可能漏发且保留reserved，需人工核查，不自动重试以避免重复，不承诺exactly-once。状态丢失时默认失败关闭，删除/重建状态可能重发。公开仓库的状态只有时间、方向和计数，无token/chat ID。

HTTP错误不输出URL和响应体，避免Telegram URL中的token泄露。不要开启HTTP调试追踪。没有自动下单或交易账户密钥。用户已批准按AI_SETUP.md的条件与限额调用OpenAI；更贵模型、增加额度及其他付费服务仍须单独获得明确批准。

## 参考

- [OKX官方API文档（confirm=1表示已完成）](https://app.okx.com/docs-v5/en/)

- [Actions schedule最短5分钟及延迟说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [Actions计费](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [Binance衍生品文档](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data)
- [Telegram Bot API](https://core.telegram.org/bots/api#sendmessage)
- [Actions真实行情失败记录](https://github.com/KiKiyo/ethusdt-alerts/actions/runs/39637113034)

