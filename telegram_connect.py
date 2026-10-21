"""Manual private setup: deliver chat ID inside Telegram, never public Actions logs."""
import os
import time
from monitor import request, SafeError


def candidate_chat(updates, now):
    chats=set()
    for update in updates:
        message=update.get('message',{})
        chat=message.get('chat',{})
        sender=message.get('from',{})
        age=now-message.get('date',0)
        if (chat.get('type')=='private' and chat.get('id')==sender.get('id')
                and not sender.get('is_bot',True) and 0<=age<=86400
                and message.get('text','').strip()=='/start'):
            chats.add(chat['id'])
    if len(chats)!=1:
        raise SafeError('Need exactly one private /start sender in the past 24 hours; no message sent')
    return chats.pop()


def main():
    token=os.environ['TELEGRAM_BOT_TOKEN']
    base='https://api.telegram.org/bot'+token
    bot=request(base+'/getMe')
    if not bot.get('ok') or bot['result'].get('username','').lower()!='cryptoblower_bot':
        raise SafeError('Bot identity mismatch; no message sent')
    updates=request(base+'/getUpdates',{'limit':100,'timeout':0,'allowed_updates':['message']})
    if not updates.get('ok'):
        raise SafeError('Cannot read private setup message')
    chat=candidate_chat(updates['result'],int(time.time()))
    result=request(base+'/sendMessage',{
        'chat_id':chat,
        'text':f'CryptoBlower 连接测试成功。\n你的 TELEGRAM_CHAT_ID：{chat}\n请将这个数字保存到 GitHub 仓库 Actions Secret：TELEGRAM_CHAT_ID。\n当前仅为连接测试，尚未启用行情提醒或自动下单。',
        'protect_content':True,'allow_paid_broadcast':False})
    if not result.get('ok'):
        raise SafeError('Telegram delivery rejected')
    print('Private setup notification confirmed. Chat ID/token omitted from public logs.')


if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        print(str(exc) if isinstance(exc,SafeError) else 'Setup failed (details suppressed)')
        raise SystemExit(1)
