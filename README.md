# CryptoBlower · ETHUSDT 每分钟候选筛选

2026-10-21：代码已支持每分钟检查，11项离线测试通过；**尚未启动**。Actions美国eastus2节点访问Binance返回HTTP 451；Telegram只配置了token，接收chat ID及通知验收尚未完成。AI保持关闭，无自动下单。

## 检查与通知

每分钟约第3秒读取Binance USDⓈ-M ETHUSDT永续已收盘1m/5m/15m各200根。1m用于最新入场确认，5m/15m用于趋势过滤。以Binance服务器时间减2秒判定收盘；拒绝断档、重复、NaN、无效价格、过期及少于100根的数据。行情错误时不发送候选，不替换为现货。

EMA9/21以SMA初始化；RSI14/ATR14使用Wilder平滑；量比为本根成交量/之前20根均量。基础规则：5m/15m EMA同向；偏多RSI分别50–70/50–75，偏空30–50/25–50；5m量比≥1.2、ATR/收盘介于0.1%–3%。进一步要求1m量比≥1.2；偏多收盘>EMA9>EMA21且RSI50–68；偏空收盘<EMA9<EMA21且RSI32–50。

只有通过全部规则的方向变化才通知，平时静默。30分钟冷却、每UTC日最多24条。同方向持续成立不重复发送；冷却期出现而后持续不变的信号会被抑制。通知含三个周期指标与数据时间。“建仓候选”仅表示规则匹配，未经回测，无盈利保证；不评估你的持仓、杠杆、资金费率、价差或实际成交成本。AI `review_candidate()` 仅离线占位，通知明确标注未启用；不调用TradingCursor或任何付费AI。

## 免费部署边界

GitHub Actions schedule最短5分钟，且可延迟/丢失，**不能承担本项目的一分钟持续分析**。仓库内monitor.yml仅保留5分钟检查的备用方案，不应宣称已实现一分钟部署。此方案还被当前HTTP451阻挡，保持MONITOR_ENABLED未启用。

一分钟模式由 `runner.py` 在用户自己的Linux/macOS电脑或已有服务器运行。不会创建云资源或付费服务；电脑需持续开机联网，耗电和原有网络/主机费用由用户承担。需要该用户和运行环境依法依约有权访问Binance数据；不要通过代理绕过限制。没有合适环境时，先讨论替代数据源或部署方式，任何付费步骤需单独明确批准。

## 验证（Python 3.10+，无第三方依赖）

```sh
python3 -m unittest discover -s tests -v
python3 monitor.py --demo
python3 monitor.py --dry-run
```

11项测试覆盖指标、双周期与1m确认、已收盘筛选、断档/过期/NaN、去重/冷却/日上限、状态持久化和文件权限、GitHub条件更新、离线AI及密钥错误保护。真实行情本机DNS失败、Actions HTTP451；端到端未验收。

## Telegram安全配置

机器人 @CryptoBlower_bot。用户已发送/start，GitHub Secret名为 `TELEGRAM_CRYPTOBLOWER_TOKEN`，工作流将其映射为程序环境变量TELEGRAM_BOT_TOKEN。密钥不要发送到聊天、代码、Issue、日志或截图。还需要 `TELEGRAM_CHAT_ID` Secret。

可在私人本机终端执行 `python3 telegram_setup.py`，在隐藏提示中输入BotFather token，读取自己Bot的getUpdates并查看私聊ID；不要使用第三方查ID服务。将自己的ID存入TELEGRAM_CHAT_ID。该脚本不发送消息。创建机器人可在官方Telegram通过已验证@BotFather的/newbot完成。泄露token后从BotFather撤销。

## 本机一分钟模式（尚未配置或启动）

1. 在允许访问Binance的环境先运行dry-run，确认真实1m/5m/15m已收盘数据正常。
2. 通过该主机的安全凭据管理方式提供 `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`、`MONITOR_ENABLED=true`、`TRIAL_UNTIL`（带时区的ISO UTC时间，未来7天以内）。不要将token写进命令历史；本项目不自动加载.env。
3. `STATE_FILE`默认runtime/state.json；首次无文件时临时设置BOOTSTRAP_STATE=true初始化，成功后改为false。runtime已gitignore，不上传。
4. 运行 `python3 runner.py`。它持有独占文件锁，每分钟第3秒调用分析；到试验截止自动退出，连续三次失败停止。睡眠/断网会中断检查，不回补历史，不提供严格60秒SLA。Ctrl+C停止。不要同时运行Actions及本机通知，二者状态不共享。
5. 首条实际通知收到后再宣称端到端验收成功。保持AI_ENABLED=false；设true会失败。

程序默认GithubState只供Actions使用；runner强制使用本机LocalState，私有文件0600、目录0700，临时文件fsync后原子替换。每个分析进程最长55秒，无限重试和高频请求均未启用。

## Actions五分钟备用模式

仅允许独立公开仓库标准ubuntu-latest，私有仓库job跳过；不使用付费runner、artifact或cache。单次最长2分钟。配置Secrets如上；Variables为TRIAL_UNTIL（未来7天内）、BOOTSTRAP_STATE=false（仓库已初始化.state/state.json）、MONITOR_ENABLED=true（当前不要启用）。工作流需要Contents写权限保存去重状态，不需要PAT或Binance账户密钥。到期脚本不发通知，但仍应禁用workflow或设MONITOR_ENABLED=false停止runner启动。

免费标准公开runner目前免费；账户级预算未由本项目设置，用户需在Billing核实并设置可用的预算停止选项。通知上限不等于账单硬限额。理论5分钟每天288次、30天8640次，不能将私人仓库按此频率运行视作免费。

## 投递与故障

发送前必须持久化reserved状态；Actions使用GitHub Contents SHA条件更新及concurrency串行，本机用锁及原子文件。发送仅尝试一次，显式allow_paid_broadcast=false；成功后写confirmed。超时或发送后写回失败可能漏发且保留reserved，需人工核查，不自动重试以避免重复，不承诺exactly-once。状态丢失时默认失败关闭，删除/重建状态可能重发。公开仓库的状态只有时间、方向和计数，无token/chat ID。

HTTP错误不输出URL和响应体，避免Telegram URL中的token泄露。不要开启HTTP调试追踪。没有自动下单、交易账户密钥、付费模型或新建付费资源。后续任何付费服务均须单独获得用户明确批准。

## 参考

- [Actions schedule最短5分钟及延迟说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [Actions计费](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [Binance衍生品文档](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data)
- [Telegram Bot API](https://core.telegram.org/bots/api#sendmessage)
- [Actions真实行情失败记录](https://github.com/KiKiyo/ethusdt-alerts/actions/runs/39637113034)
