import os
import re
import logging
import requests
import asyncio
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── Config ─────────────────────────────────────────────────────────────────
# Using the token provided in the first message
TOKEN = "8946991654:AAHccnC-8DRM2RFyFfmPSB5-wvMTnU1CUB8"
TARGET_URL = "https://yassa-hany.com/SCR/Others/DataNum2/"

# ─── Helpers ─────────────────────────────────────────────────────────────────
def is_valid_egyptian_number(phone: str) -> bool:
    """Return True if phone is a valid Egyptian mobile number."""
    return bool(re.match(r"^(010|011|012|015)\d{8}$", phone))

def lookup_phone_http(phone: str) -> str:
    """Search for phone info using direct HTTP requests."""
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": TARGET_URL,
        "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
    }

    try:
        logger.info(f"Fetching initial page for {phone}")
        response = session.get(TARGET_URL, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        
        token_input = soup.find("input", {"id": "recaptcha-token"})
        token_value = token_input.get("value", "") if token_input else ""
        
        data = {
            "phone": phone,
            "recaptcha-token": token_value,
            "g-recaptcha-response": "", 
            "add": "" 
        }

        logger.info(f"Sending POST request for {phone}")
        post_response = session.post(TARGET_URL, data=data, headers=headers, timeout=15)
        
        if post_response.status_code != 200:
            return f"خطأ في الاتصال بالموقع (Status: {post_response.status_code})"

        result_soup = BeautifulSoup(post_response.text, "html.parser")
        
        if "reCAPTCHA" in post_response.text and len(post_response.text) < 2000:
            return "⚠️ الموقع يطلب حل كابتشا (reCAPTCHA). استخدام HTTP المباشر قد لا يعمل بدون حلها."

        for tag in result_soup.select("nav, footer, script, style"):
            tag.decompose()

        result_text = ""
        for div in result_soup.find_all("div", class_=re.compile(r"alert|result|info|card|output", re.I)):
            t = div.get_text(separator=" ", strip=True)
            if t and "reCAPTCHA" not in t and len(t) > 4:
                result_text += t + "\n"

        for table in result_soup.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cells:
                    rows.append(" | ".join(cells))
            if rows:
                result_text += "\n".join(rows) + "\n"

        if not result_text:
            for p in result_soup.find_all("p"):
                t = p.get_text(strip=True)
                if re.search(r"[\u0600-\u06FF]", t) and len(t) > 3:
                    result_text += t + "\n"

        return result_text.strip() if result_text.strip() else "لم يتم العثور على نتيجة."

    except Exception as e:
        logger.error(f"HTTP lookup error: {e}")
        return f"حدث خطأ أثناء الاتصال: {e}"

# ─── Bot Handlers ─────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 أهلاً!\n\n"
        "أرسل لي رقم هاتف مصري (11 رقم يبدأ بـ 010 أو 011 أو 012 أو 015) "
        "وسأبحث لك عن اسم صاحبه."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    phone = update.message.text.strip()

    if not is_valid_egyptian_number(phone):
        await update.message.reply_text("❌ يرجى إرسال رقم مصري صحيح.")
        return

    msg = await update.message.reply_text("🔍 جاري البحث …")
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lookup_phone_http, phone)
    
    await msg.edit_text(f"📋 نتيجة البحث عن {phone}:\n\n{result}")

# ─── Entry Point ─────────────────────────────────────────────────────────────
def main() -> None:
    # Use a try-except block to catch invalid token errors early
    try:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", cmd_start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info(f"Bot is starting with token: {TOKEN[:10]}...")
        app.run_polling()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")

if __name__ == "__main__":
    main()
