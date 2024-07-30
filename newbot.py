import asyncio
from tarfile import data_filter
import telegram
import requests
import logging
from telegram import Update
from telegram.ext import filters
from telegram.ext import MessageHandler
from telegram.ext import ApplicationBuilder
from telegram.ext import CommandHandler
from telegram.ext import ContextTypes


BOT_TOKEN = '7210857691:AAFPx7cYldNuVwX4d4msyL2jWcpB2tLVqM4'
CHAT_ID = '-1002222744081'


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="您好，我是B站直播提醒机器人。"
    )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=update.message.text)


async def caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_caps = ' '.join(context.args).upper()
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=text_caps)


def fetch_bilive_info(uid: str | int) -> dict:
    """get bilibili live information through UPer uid

    Args:
        uid (str): UID of the liver

    Returns:
        dict: live information in json format
    """
    url = 'https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld'
    # url_example='https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid=27288782'
    params = {
        "mid": uid
    }
    header = {
        'User-Agent': 'Mozilla/5.0',
    }
    res = requests.get(url, params=params, headers=header).json()
    info = {
        'code': res['code'],
        'message': res['message'],
        'roomStatus': res['data']['roomStatus'],
        'liveStatus': res['data']['liveStatus'],
        'url': res['data']['url'],
        'roomid': res['data']['roomid'],
    }
    return info


async def callback_minute(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    last_live_status = data['last_live_status']
    # count = data['count']
    live_info = fetch_bilive_info('27288782')
    if last_live_status != live_info['liveStatus']:
        if live_info['liveStatus'] == 0:
            await context.bot.send_message(chat_id=CHAT_ID, text=f'B站主播下播了')
        else:
            await context.bot.send_message(chat_id=CHAT_ID, text=f'B站主播开播了，直播间：{live_info['url']}')
        data['last_live_status'] = live_info['liveStatus']
    # data['count'] += 1

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    job_queue = application.job_queue

    # define handlers
    start_handler = CommandHandler('start', start)
    caps_handler = CommandHandler('caps', caps)
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)

    # add handlers
    application.add_handler(start_handler)
    application.add_handler(echo_handler)
    application.add_handler(caps_handler)

    # add job repeatedly
    last_live_status = -1
    count = 0
    job_minute = job_queue.run_repeating(
        callback_minute, interval=60,
        data={'last_live_status': last_live_status,
              'count': count})

    # run application
    application.run_polling()
