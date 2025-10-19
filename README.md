# telegram-automation

Automation and robots for Telegram (collection of small bots and helpers).

This repository contains several automation scripts. The primary new component is
`bilivepusher.py`, a standalone Telegram bot that periodically polls Bilibili
live APIs and pushes notifications when tracked streamers go live or go offline.

---

## Features

- Periodic polling of Bilibili room information (configurable interval).
- Push notifications to a configured chat (group/channel/user) when a streamer
  starts or stops streaming.
- Simple Telegram commands to manage subscriptions: `/add`, `/rm`, `/ls`.
- Persists subscriptions in `uplist.json`.

## Requirements

- Python 3.8+ (the repository uses 3.10 in examples)
- Packages listed in `requirements.txt` (or install the minimal set below)

Minimal install (recommended):

```bash
pip install requests python-telegram-bot
```

Or install from the repo requirements:

```bash
pip install -r requirements.txt
```

(If you plan to use python-telegram-bot job queue features, install the optional extras as documented in their docs.)

---

## Configuration

`bilivepusher.py` reads configuration from `config.ini` (section `[bot]`) or
from environment variables. Example `config.ini` (add to your existing file):

```ini
[bot]
bot_token = 123456:ABC-DEFyour_bot_token_here
chatid = -1001234567890  # optional: chat id to receive notifications
interval = 60            # optional: polling interval in seconds (default 60)
```

Environment variables alternative:

- `TG_BOT_TOKEN` — your Telegram bot token
- `TG_CHAT_ID` — optional chat ID to receive notifications

Notes on `chatid`:

- If `chatid` is provided, notifications are sent there.
- If not provided, the bot logs notifications instead. You can extend the bot
  to send notifications to the chat that issued the `/add` command.

---

## `uplist.json` (subscriptions)

The bot persists the list of tracked UIDs in `uplist.json` next to the script.
It has this simple structure:

```json
{
  "uplist": [
    "27288782",
    "12345678"
  ]
}
```

You can pre-populate this file or manage subscriptions at runtime using the
Telegram commands described below.

---

## Usage

Run the bot from the repository root (adjust the path if needed):

```bash
python bilivepusher.py
```

Or provide configuration via environment variables and then run:

```bash
set TG_BOT_TOKEN=123456:ABC-DEFyour_bot_token_here
set TG_CHAT_ID=-1001234567890
python bilivepusher.py
```

After the bot starts, use Telegram to interact with it (from a chat where the
bot is present):

- `/start`  — show help message
- `/add <uid1> [uid2] ...` — add one or more Bilibili UIDs to the watch list
- `/rm <uid1> [uid2] ...` — remove one or more UIDs from the watch list
- `/ls` — list current subscriptions

Example (in a Telegram chat with the bot):

```
/add 27288782 12345678
/ls
/rm 12345678
```

When a tracked UID changes streaming status, the bot sends a plain text
notification with the username, UID and the stream URL (if available).

---

## Troubleshooting

- Bot token invalid or missing: make sure `config.ini` has a correct `bot_token`
  or set `TG_BOT_TOKEN` environment variable.
- Chat ID issues: use a correct numeric chat id (channels or supergroups usually
  need a `-100...` prefix). If notifications do not arrive, check bot
  permissions in the target chat.
- Network/API errors: Bilibili API calls use timeouts and are logged; the
  bot will continue running on transient failures.
- If the bot does not start, ensure dependencies are installed and Python can
  import `python-telegram-bot` and `requests`.

---

## Extending the bot

Ideas you may want to implement next:

- Per-chat subscriptions (so different chats can subscribe to different UIDs).
- Richer notifications with stream title, cover image, or inline buttons.
- Rate-limiting or backoff when hitting Bilibili API limits.
- Unit tests for Bilibili helpers and command handlers.

---

## License

This repository is provided under the license in the `LICENSE` file.

If you'd like, I can update this README with examples of per-chat subscription
behavior and demonstrate how to test the bot locally (including sample
uplist.json and sample config.ini).
