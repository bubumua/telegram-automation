"""bilivepusher.py

Standalone Telegram bot that periodically polls Bilibili live APIs and pushes
notifications to a configured chat when streamers go live / go offline.

Usage:
  - Configure `config.ini` with [bot] bot_token and chatid (optional).
  - Run: python bilivepusher.py

Features:
  - Polls Bilibili room info every INTERVAL seconds (default 60).
  - Keeps `uplist.json` for subscribed UIDs.
  - Telegram commands: /start, /add <uid>..., /rm <uid>..., /ls

This file is independent and does not modify other project files.

Updated:

2025-10-19: Use PTB (python-telegram-bot) v22.5.
"""

import configparser
import json
import logging
import os
from typing import Dict, List

import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Constants
DEFAULT_UPLIST_FILE = "uplist.json"
DEFAULT_INTERVAL = 60  # seconds

logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_config(path: str = "config.ini") -> Dict[str, str]:
	cfg = configparser.ConfigParser()
	cfg.read(path)
	bot_token = None
	chatid = None
	interval = DEFAULT_INTERVAL

	if cfg.has_section("bot"):
		bot_token = cfg.get("bot", "bot_token", fallback=None)
		chatid = cfg.get("bot", "chatid", fallback=None)
	# try:
	# 	interval = int(cfg.get("bot", "interval", fallback=str(DEFAULT_INTERVAL)))
	# except Exception:
	# 	interval = DEFAULT_INTERVAL

	# allow environment variable fallback
	bot_token = bot_token or os.environ.get("TG_BOT_TOKEN")
	chatid = chatid or os.environ.get("TG_CHAT_ID")

	return {"bot_token": bot_token, "chatid": chatid, "interval": interval}


def load_uplist(path: str = DEFAULT_UPLIST_FILE) -> List[str]:
	"""
	Load the uplist from JSON file.

	Args:
		path: str - path to the JSON file

	Returns:
		List[str] - list of subscribed UIDs

	"""
	if not os.path.exists(path):
		with open(path, "w", encoding="utf-8") as f:
			json.dump({"uplist": []}, f, ensure_ascii=False, indent=2)
		return []

	with open(path, "r", encoding="utf-8") as f:
		try:
			data = json.load(f)
			return list(data.get("uplist", []))
		except Exception:
			return []


def save_uplist(uplist: List[str], path: str = DEFAULT_UPLIST_FILE) -> None:
	with open(path, "w", encoding="utf-8") as f:
		json.dump({"uplist": uplist}, f, ensure_ascii=False, indent=2)


# Bilibili helper functions
def fetch_live_info_by_uid(uid: str | int) -> Dict:
	"""
	Call Bilibili API to fetch basic room info for a given uid (mid).
	Returns a dict with keys: code, message, liveStatus, url, roomid

	Args:
		uid: str | int - UID of the liver
	Returns:
		dict: live information in json format

	"""
	url = "https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld"
	params = {"mid": uid}
	headers = {"User-Agent": "Mozilla/5.0"}
	try:
		resp = requests.get(url, params=params, headers=headers, timeout=10)
		resp.raise_for_status()
		j = resp.json()
		room = j.get("data") or {}
		return {
			"code": j.get("code", -1),
			"message": j.get("message", ""),
			"liveStatus": room.get("liveStatus", 0),
			"url": room.get("url", ""),
			"roomid": room.get("roomid", 0),
		}
	except Exception as e:
		logger.exception("fetch_live_info_by_uid failed for %s", uid)
		return {"code": -1, "message": str(e), "liveStatus": 0, "url": "", "roomid": 0}


def fetch_uname_by_uid(uid: str | int) -> str:
	"""
	Fetch the username (uname) of a Bilibili user by their UID.
	Args:
		uid: str | int - UID of the liver

	Returns:
		str: username if found, else str(uid)
	"""
	url = "https://api.live.bilibili.com/live_user/v1/Master/info"
	params = {"uid": uid}
	headers = {"User-Agent": "Mozilla/5.0"}
	try:
		resp = requests.get(url, params=params, headers=headers, timeout=10)
		resp.raise_for_status()
		j = resp.json()
		return j.get("data", {}).get("info", {}).get("uname", str(uid))
	except Exception:
		logger.exception("fetch_uname_by_uid failed for %s", uid)
		return str(uid)


class BiliLivePusher:
	def __init__(self, bot_token: str, chat_id: str | int | None, interval: int = DEFAULT_INTERVAL):
		if not bot_token:
			raise ValueError("bot_token is required")
		self.bot_token = bot_token
		self.chat_id = int(chat_id) if chat_id is not None else None
		self.interval = interval
		self.uplist = load_uplist()
		# mapping uid -> info (liveStatus and url and uname)
		self.last_infos: Dict[str, Dict] = {}
		for uid in self.uplist:
			self.last_infos[uid] = {"liveStatus": -1, "url": "", "uname": fetch_uname_by_uid(uid)}

		self.app = ApplicationBuilder().token(self.bot_token).build()

		# register handlers
		self.app.add_handler(CommandHandler("start", self.cmd_start))
		self.app.add_handler(CommandHandler("add", self.cmd_add))
		self.app.add_handler(CommandHandler("rm", self.cmd_rm))
		self.app.add_handler(CommandHandler("ls", self.cmd_ls))

	async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
		await update.message.reply_text(
			"你好，我会定期检查 B 站主播开播状态并通知你。使用：\n\n /add <uid> 添加订阅 \n\n /ls 查看所有订阅 \n\n /rm <uid> 删除订阅。")

	async def cmd_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
		args = context.args
		if not args:
			await update.message.reply_text("用法: /add <uid1> [uid2] ...")
			return
		added = []
		for uid in args:
			if uid not in self.uplist:
				self.uplist.append(uid)
				self.last_infos[uid] = {"liveStatus": -1, "url": "", "uname": fetch_uname_by_uid(uid)}
				added.append(uid)
		save_uplist(self.uplist)
		await update.message.reply_text("已添加: %s" % (", ".join(added) if added else "(无)"))

	async def cmd_rm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
		args = context.args
		if not args:
			await update.message.reply_text("用法: /rm <uid1> [uid2] ...")
			return
		removed = []
		for uid in args:
			if uid in self.uplist:
				self.uplist.remove(uid)
				self.last_infos.pop(uid, None)
				removed.append(uid)
		save_uplist(self.uplist)
		await update.message.reply_text("已删除: %s" % (", ".join(removed) if removed else "(无)"))

	async def cmd_ls(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
		if not self.uplist:
			await update.message.reply_text("订阅列表为空。")
			return
		lines = []
		for uid in self.uplist:
			uname = self.last_infos.get(uid, {}).get("uname") or fetch_uname_by_uid(uid)
			lines.append(f"{uname} ({uid})")
		await update.message.reply_text("\n".join(lines))

	async def _job_poll(self, context: ContextTypes.DEFAULT_TYPE):
		# Called by the JobQueue periodically
		try:
			for uid in list(self.uplist):
				info = fetch_live_info_by_uid(uid)
				prev = self.last_infos.get(uid, {"liveStatus": -1, "url": ""})
				# if status changes, send notification
				if info.get("liveStatus") != prev.get("liveStatus"):
					uname = self.last_infos.get(uid, {}).get("uname") or fetch_uname_by_uid(uid)
					self.last_infos[uid] = {"liveStatus": info.get("liveStatus"), "url": info.get("url", ""),
											"uname": uname}
					if info.get("liveStatus") == 1:
						text = f"{uname} ({uid}) 正在直播：{info.get('url', '')}"
					else:
						text = f"{uname} ({uid}) 已下播。"

					# send notification to configured chat or to bot admin if update exists
					try:
						if self.chat_id is not None:
							await context.bot.send_message(chat_id=self.chat_id, text=text)
						else:
							# no configured chat: try to send to the last user who issued a command
							# we skip complex user-management: just log
							logger.info("No chat_id configured, would send: %s", text)
					except Exception:
						logger.exception("Failed to send notification for %s", uid)
		except Exception:
			logger.exception("Error while polling live statuses")

	def run(self):
		# schedule job
		job_queue = self.app.job_queue
		job_queue.run_repeating(self._job_poll, interval=self.interval, first=5)
		# start polling
		self.app.run_polling()


if __name__ == "__main__":
	cfg = load_config()
	token = cfg.get("bot_token")
	chatid = cfg.get("chatid")
	interval = cfg.get("interval", DEFAULT_INTERVAL)

	if not token:
		print("Error: bot token not found in config.ini or TG_BOT_TOKEN env var")
		raise SystemExit(1)

	pusher = BiliLivePusher(bot_token=token, chat_id=chatid, interval=interval)
	pusher.run()
