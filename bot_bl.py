import asyncio
import os
import json
import configparser
from tarfile import data_filter
# import telegram
import logging
import requests
from telegram import Update
from telegram.ext import filters
from telegram.ext import MessageHandler
from telegram.ext import ApplicationBuilder
from telegram.ext import CommandHandler
from telegram.ext import ContextTypes
# from telegram.request import HTTPXRequest


# read configuration file
config = configparser.ConfigParser()
config.read('config.ini')

# define configuration parameters
BOT_TOKEN = config.get('bot', 'bot_token')
CHAT_ID = config.get('bot', 'chatid')

# begin: define subscription operations


def get_json_data(filename='uplist') -> dict:
    jsondata = {}
    full_filename = filename+'.json'
    # 检查是否存在 json 文件
    if os.path.exists(full_filename):
        logtext = f"Existing data in {full_filename}: "
        # 如果文件存在，则读取数据
        with open(full_filename, 'r') as json_file:
            jsondata = json.load(json_file)
            if 'uplist' in jsondata:
                logtext = logtext+"uplist exists."
            else:
                logtext = logtext+"uplist does not exist."
                jsondata['uplist'] = []
                with open(full_filename, 'w') as json_file:
                    json.dump(jsondata, json_file)
        print(logtext)
    else:
        # 如果文件不存在，则创建一个新文件并写入默认数据
        jsondata = {
            "uplist": []
        }
        with open(full_filename, 'w') as json_file:
            json.dump(jsondata, json_file)
        print(f"Created {full_filename} file with default data.")

    return jsondata


def fetch_live_info_by_uid(uid: str | int) -> dict:
    """get bilibili live information through UPer uid

    Args:
        uid (str): UID of the liver

    Returns:
        dict: live information in json format
    """
    # url_example='https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid=27288782'
    url = 'https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld'
    params = {
        "mid": uid
    }
    header = {
        'User-Agent': 'Mozilla/5.0',
    }
    res = requests.get(url, params=params, headers=header, verity=False).json()
    info = {
        'code': res['code'],
        'message': res['message'],
        'liveStatus': res['data']['liveStatus'],
        'url': res['data']['url'],
        'roomid': res['data']['roomid'],
    }
    return info


def fetch_uname_by_uid(uid: str | int) -> str:
    """get LSer's username on Bili by uid

    Args:
        uid (str): LSer's UID

    Returns:
        str: LSer's username on Bili
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


def init_LS_infos():
    global last_LS_infos
    last_LS_infos = {}
    for up in uplist:
        uname = fetch_uname_by_uid(up)
        last_LS_infos[up] = {
            'uid': up,
            'uname': uname,
            'liveStatus': -1,
            'url': ""
        }


def add_uid_into_list(uid):
    global uplist
    if uid not in uplist:
        uplist.append(uid)
        init_LS_infos()
        with open('uplist.json', 'w') as json_file:
            json.dump(jsondata, json_file)
        return True
    else:
        return False


def remove_uid_from_list(uid):
    global uplist
    if uid in uplist:
        uplist.remove(uid)
        init_LS_infos()
        with open('uplist.json', 'w') as json_file:
            json.dump(jsondata, json_file)
        return True
    else:
        return False

# end: define subscription operations


# get json data
jsondata = get_json_data()
# get UPer list
uplist = jsondata['uplist']
# save last live infos
last_LS_infos = []
# init live infos
init_LS_infos()

# log configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# begin: define bot function


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="您好，我是B站直播提醒机器人。"
    )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(update.message.text)
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=update.message.text)


async def caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_caps = ' '.join(context.args).upper()
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=text_caps)


async def handle_list_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ""
    for uid in uplist:
        text += f"{last_LS_infos[uid]['uname']} ({uid})\n"
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=text)


async def handle_add_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"add uid: {context.args}")
    for uid in context.args:
        add_uid_into_list(uid)
    await handle_list_uid(update, context)


async def handle_remove_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"delete uid: {context.args}")
    for uid in context.args:
        remove_uid_from_list(uid)
    await handle_list_uid(update, context)


async def callback_minute(context: ContextTypes.DEFAULT_TYPE):
    # data = context.job.data
    for up in uplist:
        cur_live_info = fetch_live_info_by_uid(up)
        if cur_live_info['liveStatus'] != last_LS_infos[up]['liveStatus']:
            last_LS_infos[up]['liveStatus'] = cur_live_info['liveStatus']
            last_LS_infos[up]['url'] = cur_live_info['url']
            # edit forward text
            text = f"{last_LS_infos[up]['uname']} ({up}) "
            if cur_live_info['liveStatus'] == 1:
                text += "正在直播："
                text += last_LS_infos[up]['url']
            else:
                text += "已下播。"
            # forward notification
            await context.bot.send_message(chat_id=CHAT_ID, text=text)

# end: define bot function

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
    application.add_handler(CommandHandler('add', handle_add_uid))
    application.add_handler(CommandHandler('rm', handle_remove_uid))
    application.add_handler(CommandHandler('ls', handle_list_uid))

    # get job_queue
    job_queue = application.job_queue

    # add job repeatedly
    job_minute = job_queue.run_repeating(
        callback_minute,
        # data=[uplist, last_LS_infos],
        interval=60
    )

    # run application
    application.bot.delete_webhook()
    application.run_polling()
