import os
import io
import json
import asyncio
import logging
import random
import base64
import urllib.parse
import urllib.request
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"
WIDTH = 1024
HEIGHT = 1024


def _fetch_sync(url: str, timeout_sec: int = 180) -> Optional[bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = resp.read()
            if resp.status == 200 and data and len(data) > 1000:
                return data
            logger.warning("HTTP %s from %s", getattr(resp, "status", "?"), url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Download error: %s", exc)
    return None


async def _download(url: str, timeout_sec: int = 180) -> Optional[bytes]:
    return await asyncio.to_thread(_fetch_sync, url, timeout_sec)


async def generate_pollinations(prompt: str) -> Optional[bytes]:
    """Free, no-key image generation via Pollinations.ai."""
    encoded = urllib.parse.quote(prompt, safe="")
    url = (
        f"{POLLINATIONS_BASE}/{encoded}"
        f"?width={WIDTH}&height={HEIGHT}&nologo=true&seed={random.randint(0, 10**9)}"
    )
    for attempt in range(3):
        data = await _download(url)
        if data:
            return data
        await asyncio.sleep(2)
    return None


def _gemini_sync(prompt: str, key: str) -> Optional[bytes]:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash-image:generateContent?key={key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = resp.read()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gemini error: %s", exc)
        return None
    try:
        obj = json.loads(body.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gemini parse error: %s", exc)
        return None
    for cand in obj.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData")
            if inline and inline.get("data"):
                try:
                    return base64.b64decode(inline["data"])
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Gemini decode error: %s", exc)
    return None


async def generate_gemini(prompt: str) -> Optional[bytes]:
    """Optional higher-quality fallback using Gemini 2.5 Flash Image (free tier)."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    return await asyncio.to_thread(_gemini_sync, prompt, key)


async def generate_image(prompt: str) -> Optional[bytes]:
    data = await generate_pollinations(prompt)
    if data:
        return data
    logger.info("Pollinations failed, trying Gemini fallback")
    return await generate_gemini(prompt)


async def handle_prompt(update: Update, prompt: str) -> None:
    prompt = prompt.strip()
    if not prompt:
        await update.message.reply_text("Please send a non-empty prompt.")
        return
    status = await update.message.reply_text("🎨 Generating image, please wait...")
    data = await generate_image(prompt)
    if not data:
        try:
            await status.edit_text(
                "❌ Failed to generate image. Try again in a moment."
            )
        except Exception:  # noqa: BLE001
            pass
        return
    try:
        await status.delete()
    except Exception:  # noqa: BLE001
        pass
    await update.message.reply_photo(
        photo=io.BytesIO(data), caption=prompt[:1024]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi! Send me any text and I'll turn it into an image.\n"
        "Or use /img <prompt>.\n\n"
        "Powered by free image-generation APIs."
    )


async def img_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prompt = " ".join(context.args or [])
    await handle_prompt(update, prompt)


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message and update.message.text:
        await handle_prompt(update, update.message.text)


def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is required")
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("img", img_cmd))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)
    )
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
