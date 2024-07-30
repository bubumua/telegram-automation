import asyncio
from tarfile import data_filter
import configparser
import json
import os
# import telegram
import requests
import logging
from telegram import Update
import telegram
from telegram.request import HTTPXRequest
from telegram.ext import filters
from telegram.ext import MessageHandler
from telegram.ext import ApplicationBuilder
from telegram.ext import CommandHandler
from telegram.ext import ContextTypes

# read configuration file
config = configparser.ConfigParser()
config.read('config.ini')

# define configuration parameters
BOT_TOKEN = config.get('bot', 'bot_token')
CHAT_ID = config.get('bot', 'chatid')


def fetch_up_live_info(uid: str | int) -> dict:
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
        'liveStatus': res['data']['liveStatus'],
        'url': res['data']['url'],
        'roomid': res['data']['roomid'],
    }
    return info


def fetch_upname(uid: str | int) -> str:
    """get up username through UPer uid

    Args:
        uid (str): UID of the liver

    Returns:
        str: UPer username
    """
    url = 'https://api.live.bilibili.com/live_user/v1/Master/info'
    params = {
        "uid": uid
    }
    header = {
        'User-Agent': 'Mozilla/5.0',
    }
    res = requests.get(url, params=params, headers=header).json()
    return res['data']['info']['uname']


def init_upinfo():
    global upinfo
    upinfo = {}
    for up in uplist:
        uname = fetch_upname(up)
        upinfo[up] = {
            'uid': up,
            'uname': uname,
            'liveStatus': -1,
            'url': ""
        }


def add_up(uid):
    global uplist
    if uid not in uplist:
        uplist.append(uid)
        init_upinfo()
        with open('uplist.json', 'w') as json_file:
            json.dump(jsondata, json_file)
        return True
    else:
        return False


def remove_up(uid):
    global uplist
    if uid in uplist:
        uplist.remove(uid)
        init_upinfo()
        with open('uplist.json', 'w') as json_file:
            json.dump(jsondata, json_file)
        return True
    else:
        return False


# get UPer list
jsondata = {}
# 检查是否存在 uplist.json 文件
if os.path.exists('uplist.json'):
    logtext = "Existing data in uplist.json: "
    # 如果文件存在，则读取数据
    with open('uplist.json', 'r') as json_file:
        jsondata = json.load(json_file)
        if 'uplist' in jsondata:
            logtext = logtext+"uplist exists."
        else:
            logtext = logtext+"uplist does not exist."
            jsondata['uplist'] = []
            with open('uplist.json', 'w') as json_file:
                json.dump(jsondata, json_file)
    print(logtext)
else:
    # 如果文件不存在，则创建一个新文件并写入默认数据
    jsondata = {
        "uplist": []
    }
    with open('uplist.json', 'w') as json_file:
        json.dump(jsondata, json_file)
    print("Created uplist.json file with default data.")

uplist = jsondata['uplist']

upinfo = []

init_upinfo()

# log configuration
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


async def callback_minute(context: ContextTypes.DEFAULT_TYPE):
    # data = context.job.data
    for up in uplist:
        cur_info = fetch_up_live_info(up)
        if cur_info['liveStatus'] != upinfo[up]['liveStatus']:
            upinfo[up]['liveStatus'] = cur_info['liveStatus']
            upinfo[up]['url'] = cur_info['url']
            # edit forward text
            text = f"{upinfo[up]['uname']} ({up}) "
            if cur_info['liveStatus'] == 1:
                text += "正在直播："
                text += upinfo[up]['url']
            else:
                text += "已下播。"
            # forward notification
            await context.bot.send_message(chat_id=CHAT_ID, text=text)


if __name__ == '__main__':
    # get application
    application = ApplicationBuilder().token(
        BOT_TOKEN).get_updates_connection_pool_size(7).build()

    # define handlers
    start_handler = CommandHandler('start', start)
    caps_handler = CommandHandler('caps', caps)
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)

    # add handlers
    application.add_handler(start_handler)
    application.add_handler(echo_handler)
    application.add_handler(caps_handler)

    # get job_queue
    job_queue = application.job_queue

    # add job repeatedly
    job_minute = job_queue.run_repeating(
        callback_minute,
        interval=60,
        data=[uplist, upinfo])

    # run application
    application.bot.delete_webhook()
    application.run_polling()
