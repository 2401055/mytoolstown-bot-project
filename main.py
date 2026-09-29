import asyncio
import logging
import os
import re
from pathlib import Path

from playwright.async_api import async_playwright
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN", "").strip().strip('"').strip("'").strip()
CHANNEL_ID = os.getenv("CHANNEL_ID", "UCFC9ZmSS4r3m_0BytjW4U3g").strip()
BASE_URL = os.getenv(
    "BASE_URL", "https://mytoolstown.com/youtube"
).strip()
GIF_PATH = Path(os.getenv("SUCCESS_GIF", "assets/success.gif"))


class MyToolsTownBot:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.lock = asyncio.Lock()

    async def init_browser(self):
        if not CHANNEL_ID:
            raise RuntimeError("CHANNEL_ID غير مضبوط في متغيرات البيئة")
        try:
            if not self.playwright:
                self.playwright = await async_playwright().start()
            if not self.browser:
                self.browser = await self.playwright.chromium.launch(headless=True)
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()

            await self.page.goto(BASE_URL, wait_until="domcontentloaded")
            username = self.page.locator("#username")
            if await username.count():
                await username.fill(CHANNEL_ID)
                await self.page.locator("#searchbtn").click()
                try:
                    await self.page.wait_for_url("**/youtube/dashboard", timeout=15000)
                except Exception:
                    logger.warning("لم يتم الانتقال إلى dashboard بعد إدخال القناة")

            await self.page.goto(
                "https://mytoolstown.com/youtube/earn", wait_until="domcontentloaded"
            )
            checkbox = self.page.locator('input[type="checkbox"]')
            if await checkbox.count() and not await checkbox.first.is_checked():
                label = self.page.locator('label:has-text("Automatically verify")')
                if await label.count():
                    await label.first.click()
        except Exception:
            logger.exception("Error initializing browser")
            await self.close_browser()
            raise

    async def close_browser(self):
        if self.browser:
            await self.browser.close()
        self.browser = self.context = self.page = None

    async def ensure_initialized(self):
        if not self.page:
            await self.init_browser()

    async def get_task(self):
        async with self.lock:
            await self.ensure_initialized()
            await self.page.reload(wait_until="domcontentloaded")
            earn_btn = self.page.locator("#earnBtn")
            if not await earn_btn.count():
                await self.page.goto(
                    "https://mytoolstown.com/youtube/earn", wait_until="domcontentloaded"
                )
                earn_btn = self.page.locator("#earnBtn")
            if not await earn_btn.count():
                return None, "لا توجد مهام حالياً أو حدث خطأ في تحميل الصفحة."

            task_text = await self.page.locator(".card-body b").first.inner_text()
            try:
                async with self.context.expect_page(timeout=15000) as new_page_info:
                    await earn_btn.click()
                new_page = await new_page_info.value
                await new_page.wait_for_load_state("domcontentloaded")
                youtube_url = new_page.url
                await new_page.close()
            except Exception:
                youtube_url = await earn_btn.get_attribute("href") or ""
            return youtube_url, task_text

    async def verify_task(self):
        async with self.lock:
            await self.ensure_initialized()
            verify_btn = self.page.locator("#verifybtn")
            if not await verify_btn.count():
                return "لم يتم العثور على زر التحقق. جرب طلب مهمة جديدة.", False
            await verify_btn.click()
            await asyncio.sleep(3)
            credits = self.page.locator('h2:has-text("Your Credits")')
            credits_text = await credits.first.inner_text() if await credits.count() else ""
            return f"تم التحقق بنجاح! {credits_text}".strip(), True

    async def claim_daily_bonus(self):
        """Find and claim the site's daily reward when it is exposed for this account.

        The site can expose the feature under different routes depending on the account,
        so the method first discovers matching links and then falls back to known routes.
        """
        async with self.lock:
            await self.ensure_initialized()
            await self.page.goto(
                "https://mytoolstown.com/youtube/dashboard", wait_until="domcontentloaded"
            )
            candidates = []
            links = self.page.locator("a[href]")
            for i in range(await links.count()):
                link = links.nth(i)
                text = (await link.inner_text()).strip()
                href = await link.get_attribute("href") or ""
                if re.search(r"daily|bonus|reward", f"{text} {href}", re.I):
                    candidates.append(href)

            candidates += [
                "/youtube/daily-bonus",
                "/youtube/dailybonus",
                "/youtube/bonus",
                "/daily-bonus",
                "/bonus",
            ]
            seen = set()
            for href in candidates:
                if not href or href in seen:
                    continue
                seen.add(href)
                url = href if href.startswith("http") else f"https://mytoolstown.com{href}"
                try:
                    response = await self.page.goto(url, wait_until="domcontentloaded")
                    if response and response.status >= 400:
                        continue
                    body = (await self.page.locator("body").inner_text()).lower()
                    if not re.search(r"daily|bonus|reward", body):
                        continue
                    buttons = self.page.locator("button, input[type=submit], a")
                    for i in range(await buttons.count()):
                        button = buttons.nth(i)
                        label = (await button.inner_text()).strip()
                        if re.search(r"claim|collect|daily|bonus|reward", label, re.I):
                            await button.click()
                            await asyncio.sleep(2)
                            result = await self.page.locator("body").inner_text()
                            return f"تمت محاولة تحصيل الـ Daily Bonus.\n{result[-500:]}"
                    return "تم العثور على صفحة الـ Daily Bonus، لكن لم يظهر زر التحصيل."
                except Exception as exc:
                    logger.info("Daily bonus route failed %s: %s", url, exc)
            return "لم يظهر الـ Daily Bonus في حساب الموقع حالياً."


bot_logic = MyToolsTownBot()


def main_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("الحصول على مهمة جديدة 🚀", callback_data="get_task")],
            [InlineKeyboardButton("Daily Bonus 🎁", callback_data="daily_bonus")],
        ]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحباً بك! اختر العملية المطلوبة من الأزرار التالية.",
        reply_markup=main_keyboard(),
    )


async def daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    await message.reply_text("جاري البحث عن الـ Daily Bonus في الموقع...")
    try:
        result = await bot_logic.claim_daily_bonus()
        await message.reply_text(result, reply_markup=main_keyboard())
    except Exception as exc:
        logger.exception("Daily bonus failed")
        await message.reply_text(f"تعذر تحصيل الـ Daily Bonus حالياً: {exc}", reply_markup=main_keyboard())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "get_task":
        await query.edit_message_text("جاري البحث عن مهمة... (قد يستغرق ذلك بضع ثوانٍ)")
        try:
            url, text = await bot_logic.get_task()
            if url:
                keyboard = [[InlineKeyboardButton("تم التنفيذ ✅ - تحقق الآن", callback_data="verify_task")]]
                await query.message.reply_text(
                    f"المهمة: {text}\n\nالرابط: {url}\n\nقم بتنفيذ المهمة ثم اضغط على الزر أدناه للتحقق.",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            else:
                await query.edit_message_text(text, reply_markup=main_keyboard())
        except Exception as exc:
            logger.exception("Get task failed")
            await query.edit_message_text(
                f"حدث خطأ أثناء الاتصال بالموقع: {exc}\nيرجى المحاولة مرة أخرى.",
                reply_markup=main_keyboard(),
            )

    elif query.data == "verify_task":
        await query.edit_message_text("جاري التحقق من الموقع...")
        try:
            result, success = await bot_logic.verify_task()
            await query.message.reply_text(result, reply_markup=main_keyboard())
            if success and GIF_PATH.exists():
                with GIF_PATH.open("rb") as animation:
                    await query.message.reply_animation(
                        animation=animation,
                        caption="أحسنت! تم إنجاز المهمة بنجاح 🎉",
                    )
        except Exception as exc:
            logger.exception("Verify task failed")
            await query.edit_message_text(f"خطأ أثناء التحقق: {exc}", reply_markup=main_keyboard())

    elif query.data == "daily_bonus":
        await query.edit_message_text("جاري البحث عن الـ Daily Bonus في الموقع...")
        try:
            result = await bot_logic.claim_daily_bonus()
            await query.message.reply_text(result, reply_markup=main_keyboard())
        except Exception as exc:
            logger.exception("Daily bonus failed")
            await query.message.reply_text(
                f"تعذر تحصيل الـ Daily Bonus حالياً: {exc}", reply_markup=main_keyboard()
            )


async def post_init(application):
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN غير مضبوط. أضفه في Railway Variables.")


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("BOT_TOKEN is missing. Add the raw BotFather token in Railway Variables, then redeploy.")
    if not CHANNEL_ID:
        raise SystemExit("CHANNEL_ID is required")

    application = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("dailybonus", daily_bonus))
    application.add_handler(CallbackQueryHandler(button_handler))
    logger.info("Bot is running")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
