"""Run privately on your machine after /start. Never prints the bot token."""
from getpass import getpass
from monitor import request, SafeError

if __name__ == '__main__':
    token = getpass('Telegram bot token (hidden input): ').strip()
    try:
        result = request('https://api.telegram.org/bot'+token+'/getUpdates')
        chats = {}
        for update in result.get('result', []):
            message = update.get('message', {})
            chat = message.get('chat', {})
            if chat.get('type') == 'private':
                chats[chat['id']] = chat.get('first_name', '')
        if not chats:
            print('先给自己的 Bot 发送 /start，再运行一次。')
        for chat_id, name in chats.items():
            print(f'Private chat: {name}; TELEGRAM_CHAT_ID={chat_id}')
    except SafeError as exc:
        print(str(exc))
