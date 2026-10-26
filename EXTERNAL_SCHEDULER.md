# 独立免费调度配置

2026-10-25在用户明确批准后，创建单仓库短期令牌并保存到cron-job.org，测试返回HTTP204，任务已启用。Telegram token和chat ID仅保存在GitHub Secrets；没有传给调度服务。实际令牌值不存入本文档、聊天、仓库或日志。

## 当前配置

- 任务：CryptoBlower ETH-USDT monitor，ID 8696180，Enabled。
- 时区：America/Toronto；每小时第1、6、11、16、21、26、31、36、41、46、51、56分钟。
- 到期：2026-10-28 18:00多伦多时间（22:00 UTC）。GitHub变量TRIAL_UNTIL也为2026-10-28T22:00:00Z，MONITOR_ENABLED=true。
- POST URL：https://api.github.com/repos/KiKiyo/ethusdt-alerts/actions/workflows/external-monitor.yml/dispatches
- Headers：Accept: application/vnd.github+json；Content-Type: application/json；Authorization: Bearer 后跟已私密保存的短期令牌。
- JSON正文：`{"ref":"main"}`。超时30秒。
- 令牌仅限KiKiyo/ethusdt-alerts，Actions读写及必需Metadata只读，10月29日到期；没有Contents写权限或账户权限。Actions读写仍可管理此仓库其他工作流，试用结束后可提前撤销。

HTTP204仅表示GitHub接收触发请求；必须同时核对工作流success、分析日志及.state/state.json的last_analysis_at和run_id。手动Test Run不作为自动执行证据。

## 接收端与边界

.github/workflows/external-monitor.yml仅支持workflow_dispatch；使用与原工作流相同的concurrency组和持久去重状态，避免重叠重复提醒。不发送每次部署回执。只运行独立公开仓库标准ubuntu-latest，最长2分钟，无artifact/cache、付费AI或交易接口。

原生GitHub schedule曾出现数小时延迟，仍保留为备用，不能依赖其严格五分钟执行。外部调度也可能抖动，GitHub可能排队；查看连续记录只能证明已观察到的运行，不能保证未来可用性。到期程序停止分析通知；如需彻底停止原生备用runner，设置MONITOR_ENABLED=false或禁用工作流。

## 官方资料

- [cron-job.org FAQ](https://cron-job.org/en/faq/)
- [GitHub workflow dispatch接口](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)

## 自动运行验收（2026-10-25，多伦多时间）

| 计划时间 | 调度结果 | GitHub分析 | 状态更新时间（UTC） |
| --- | --- | --- | --- |
| 20:36 | 20:36:16成功，HTTP204 | [40250163932](https://github.com/KiKiyo/ethusdt-alerts/actions/runs/40250163932)，success | 2026-10-26 00:36:23 |
| 20:41 | 20:41:02成功，HTTP204 | [40250544995](https://github.com/KiKiyo/ethusdt-alerts/actions/runs/40250544995)，success | 2026-10-26 00:41:10 |

以上两次来自真实定时触发，不是手动测试。17项单元测试通过；两次均无符合条件的新候选，按规则静默。已完成两轮自动运行验收，未来仍可能受调度延迟和服务故障影响。
