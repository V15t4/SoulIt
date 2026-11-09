# Image-Gen Telegram Bot

Telegram bot that generates images from text prompts using free image-generation APIs.

- Primary: Pollinations.ai (no API key)
- Optional fallback: Google Gemini 2.5 Flash Image (free tier) via `GEMINI_API_KEY`

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and set BOT_TOKEN
python bot.py
```

## Create a private GitHub repo

```bash
cd image-gen-telegram-bot
git init
git add .
git commit -m "Initial commit: image gen telegram bot"
# Create a PRIVATE repo on GitHub (web UI or gh cli), then:
git remote add origin https://github.com/<your-username>/<repo-name>.git
git branch -M main
git push -u origin main
```

Make sure the repository visibility is set to **Private**.

## Deploy on Railway

1. Sign in at https://railway.app and create a new project.
2. Choose **Deploy from GitHub repo** and select your private repo (grant Railway access to private repos).
3. Railway auto-detects Python via Nixpacks and installs `requirements.txt`.
4. In the service **Variables** tab, add:
   - `BOT_TOKEN` = your Telegram bot token
   - `GEMINI_API_KEY` = (optional)
5. Ensure the start command is `python bot.py` (set in `railway.toml` / Procfile).
6. Deploy. Logs should show the bot polling.

## Notes
- The bot runs as a worker (long polling), not a web server.
- For production scale, consider webhooks + a public URL instead of polling.
- Free tiers have rate limits; handle gracefully.
