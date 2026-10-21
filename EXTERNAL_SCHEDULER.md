## 最新配置状态

cron-job.org账户已登录，任务8696180已创建，处于Inactive。已配置每5分钟、POST触发地址、JSON正文与Accept/Content-Type请求头；Authorization暂为Bearer占位，无实际令牌。任务在America/Toronto的2026-10-24 18:00到期。GitHub细粒度令牌表单已配置为单仓库ethusdt-alerts、Actions读写+必需Metadata只读、2026-10-24到期，尚未点击Generate token。待用户亲自生成并在cron-job.org Authorization中保存后，才能测试并启用。未声称自动运行恢复。

# 独立免费调度配置（待用户登录与短期令牌）

用户已明确批准将仅限 KiKiyo/ethusdt-alerts、Actions写权限、2026-10-24到期的短期GitHub令牌存入cron-job.org。Telegram token及chat ID仍只保存在GitHub Secrets；不得存入调度服务。令牌不发送到聊天、仓库文件或日志。

## 任务精确配置

- 名称：CryptoBlower ETH-USDT monitor
- 周期：每5分钟（可设UTC分钟1,6,11,16,21,26,31,36,41,46,51,56）
- 结束时间：2026-10-24 22:00 UTC；如服务不支持结束时间，届时手动禁用任务并撤销令牌。程序自身已设置TRIAL_UNTIL，到期不分析/不发送候选。
- 请求方法：POST
- URL：https://api.github.com/repos/KiKiyo/ethusdt-alerts/actions/workflows/external-monitor.yml/dispatches
- Headers：Accept: application/vnd.github+json；Content-Type: application/json；Authorization: Bearer 加用户亲自保存的短期令牌（切勿把实际值放进本文档）。
- Body：{"ref":"main"}
- 返回HTTP204仅表示GitHub接收触发请求，不等于分析成功。必须同时核对GitHub工作流success、.state/state.json中的last_analysis_at与run_id更新。
- 外部调度记录和GitHub连续至少两次按计划自动运行通过后，再认定调度恢复。不以手动运行作为自动稳定性证据。

## GitHub令牌最小范围

Fine-grained personal access token，Resource owner KiKiyo；Only select repositories → ethusdt-alerts；Repository permissions仅Actions: Read and write（Metadata read会自动包含）；有效期至2026-10-24。不要选择所有仓库、Contents写权限或账户权限。Actions写权限仍可触发/管理该仓库其他工作流，因此仅供此服务，测试结束撤销。

用户本人完成GitHub要求的身份验证、创建令牌；在cron-job.org私密Authorization配置中粘贴。不要把令牌输入URL，不复制进截图/聊天。cron-job.org账户新建时的密码及协议由用户本人完成。

## 已实现的接收端

.github/workflows/external-monitor.yml仅支持workflow_dispatch，无自带cron；使用与原工作流相同的全局concurrency，避免重叠，持久状态进行蜡烛/方向去重。不会每次发送部署回执。仅公开仓库标准ubuntu-latest，最长2分钟，无artifact/cache/付费AI/交易接口。

原生GitHub cron仍保留作备用，已通过用户浏览器于2026-10-21 22:20 UTC重新登记；22:23 UTC尚未观察到后续schedule事件。切勿声称已修复或稳定。

## 官方来源

https://cron-job.org/en/faq/ 明示服务免费、支持任意header及POST请求、每分钟最高60次/小时，但不承诺绝对准时。我们仅每5分钟触发一次。
https://docs.github.com/en/rest/actions/workflows 说明workflow dispatch接口及所需Actions写权限。
