"""Manual deployment receipt using the saved recipient Secret. No logs of IDs."""
import os
from monitor import request, SafeError

if __name__ == '__main__':
    try:
        base='https://api.telegram.org/bot'+os.environ['TELEGRAM_BOT_TOKEN']
        bot=request(base+'/getMe')
        if not bot.get('ok') or bot['result'].get('username','').lower()!='cryptoblower_bot':
            raise SafeError('Bot identity mismatch')
        chat=os.environ['TELEGRAM_CHAT_ID'].strip()
        info=request(base+'/getChat',{'chat_id':chat})
        if not info.get('ok') or info['result'].get('type')!='private':
            raise SafeError('Saved recipient is not an available private chat')
        result=request(base+'/sendMessage',{
            'chat_id':chat,
            'text':'CryptoBlower 配置验证成功。\n行情：OKX ETH-USDT-SWAP 永续。\n计划每5分钟检查，仅规则候选触发通知；无自动下单、AI复核未启用。\n免费测试截止（UTC）：'+os.environ['TRIAL_UNTIL']+'\n本条是部署测试回执，不是建仓信号；正式运行结果请以GitHub Actions为准。',
            'protect_content':True,'allow_paid_broadcast':False})
        if not result.get('ok'):
            raise SafeError('Deployment receipt rejected')
        print('Saved private recipient verified; test receipt confirmed. No IDs/tokens logged.')
    except Exception as exc:
        print(str(exc) if isinstance(exc,SafeError) else 'Private recipient validation failed (details suppressed)')
        raise SystemExit(1)
