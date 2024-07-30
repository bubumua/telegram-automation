import telebot
import logging
from telegram.ext import Updater
import requests

BOT_TOKEN = '7210857691:AAFPx7cYldNuVwX4d4msyL2jWcpB2tLVqM4'

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

bot = telebot.TeleBot(BOT_TOKEN)

def get_daily_horoscope(sign: str, day: str) -> dict:
    """通过特定的星座获取运势。

    关键字解释:
    sign:str - 星座
    day:str - 格式化的日期 (YYYY-MM-DD) 或 TODAY 或 TOMORROW 或 YESTERDAY
    Return:dict - JSON data
    """
    url = "https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily"
    params = {"sign": sign, "day": day}
    response = requests.get(url, params)

    return response.json()

def fetch_horoscope(message, sign):
    day = message.text
    horoscope = get_daily_horoscope(sign, day)
    data = horoscope["data"]
    horoscope_message = f'*运势:* {data["horoscope_data"]}\\n*星座:* {sign}\\n*日期:* {data["date"]}'
    bot.send_message(message.chat.id, "你的运势来啦!")
    bot.send_message(message.chat.id, horoscope_message, parse_mode="Markdown")

def day_handler(message):
    sign = message.text
    text = "你想知道哪天的呀？\\n选一个吧: *TODAY*, *TOMORROW*, *YESTERDAY*, 或其他 YYYY-MM-DD 格式的日期。"
    sent_msg = bot.send_message(message.chat.id, text, parse_mode="Markdown")
    bot.register_next_step_handler(sent_msg, fetch_horoscope, sign.capitalize())

@bot.message_handler(commands=['horoscope'])
def sign_handler(message):
    text = "你的星座是什么?\\n选一个: *Aries*, *Taurus*, *Gemini*, *Cancer,* *Leo*, *Virgo*, *Libra*, *Scorpio*, *Sagittarius*, *Capricorn*, *Aquarius*, and *Pisces*."
    sent_msg = bot.send_message(message.chat.id, text, parse_mode="Markdown")
    bot.register_next_step_handler(sent_msg, day_handler)

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.reply_to(message, "Howdy, how are you doing?")

@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    bot.reply_to(message, message.text)
    
def fetch_bilive_info(uid:str)->dict:
  """get bilibili live information through UPer uid

  Args:
      uid (str): UID of the liver

  Returns:
      dict: live information in json format
  """
  url='https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld'
  # url_example='https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid=27288782'
  params = {
    "mid": uid
  }
  header={
    'User-Agent': 'Mozilla/5.0',
  }
  res = requests.get(url, params=params, headers=header).json()
  info={
    'code': res['code'],
    'message': res['message'],
    'roomStatus': res['data']['roomStatus'],
    'liveStatus': res['data']['liveStatus'],
    'url': res['data']['url'],
    'roomid': res['data']['roomid'],
  }
  return info

def remind_UP_live(context):
  context.bot.send_message(
    chat_id='-1002222744081',
    text=str(fetch_bilive_info('27288782'))
  )

if __name__ == "__main__":
  # delete webhook
  bot.delete_webhook()

  print(fetch_bilive_info('27288782'))
  updater = Updater(bot)
  updater.job_queue.run_repeating(remind_UP_live, interval=60, first=0)
  updater.start_polling(poll_interval=3.0)
  updater.idle()
  # bot.infinity_polling()