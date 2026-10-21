# CryptoBlower · ETHUSDT 每5分钟云端候选筛选

当前：每5分钟检查，非每5分钟发消息。`monitor.py`只读取Binance ETHUSDT USDⓈ-M永续已收盘5m/15m各200根，满足条件才发送Telegram。自动提醒尚未启用；Binance访问返回HTTP451，chat ID和通知验收尚未完成。没有付费AI、付费资源或自动下单。

## 筛选规则

EMA9/21以SMA初始化，RSI14和ATR14用Wilder平滑。5m/15m EMA同向，偏多RSI分别50–70/50–75，偏空30–50/25–50；5m量比（本根/之前20根均量）≥1.2，ATR/收盘介于0.1%–3%。其余静默观察。只有候选方向改变才通知，30分钟冷却，每UTC日最多24条。冷却期间出现且持续不变的候选可能被抑制。规则未经回测，不保证建仓适合性或盈利，不考虑用户资金和持仓。

以Binance服务器时间减2秒判断收盘；拒绝过期、重复、断档、NaN及无效数据。保留1m函数和runner作为未启用的旧版工具，当前云端运行不调用它们。

## Binance故障排查

2026-10-21 Actions美国eastus2节点返回HTTP451。官方USDⓈ-M文档仍列fapi.binance.com；data-api.binance.vision是现货，不可冒充永续行情。新增手动diagnose.yml，无密钥，只检查官方公开时间接口以及错误是否包含restricted-location。若确认地区限制，无法靠改频率或普通重试修复，需另选合规运行环境或经用户同意更换数据源。不要使用测试网、代理或未经验证的镜像替代正式行情。

## 验证（Python 3.10+，无第三方依赖）

```sh
python3 -m unittest discover -s tests -v
python3 monitor.py --demo
python3 monitor.py --dry-run
```

11项离线测试覆盖指标、双周期与保留的1m确认、已收盘筛选、断档/过期/NaN、去重/冷却/日上限、状态持久化和文件权限、GitHub条件更新、离线AI及密钥错误保护。真实行情本机DNS失败、Actions HTTP451；端到端未验收。

## Telegram安全配置

机器人 @CryptoBlower_bot。用户已发送/start，GitHub Secret名为 `TELEGRAM_CRYPTOBLOWER_TOKEN`，工作流将其映射为程序环境变量TELEGRAM_BOT_TOKEN。密钥不要发送到聊天、代码、Issue、日志或截图。还需要 `TELEGRAM_CHAT_ID` Secret。

可在私人本机终端执行 `python3 telegram_setup.py`，在隐藏提示中输入BotFather token，读取自己Bot的getUpdates并查看私聊ID；不要使用第三方查ID服务。将自己的ID存入TELEGRAM_CHAT_ID。该脚本不发送消息。创建机器人可在官方Telegram通过已验证@BotFather的/newbot完成。泄露token后从BotFather撤销。

## Actions五分钟部署

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
