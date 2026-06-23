import asyncio
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
from playwright.async_api import async_playwright

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv(\'BOT_TOKEN\')
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set.")
CHANNEL_ID = os.getenv('YOUTUBE_CHANNEL_ID')
if not CHANNEL_ID:
    raise ValueError("YOUTUBE_CHANNEL_ID environment variable not set.")
BASE_URL = os.getenv('MYTOOLSTOWN_BASE_URL')
if not BASE_URL:
    raise ValueError("MYTOOLSTOWN_BASE_URL environment variable not set.")

class MyToolsTownBot:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None

    async def init_browser(self):
        try:
            if not self.playwright:
                self.playwright = await async_playwright().start()
            
            if not self.browser:
                self.browser = await self.playwright.chromium.launch(headless=True)
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()
                
                # الدخول للموقع وإعداد القناة
                await self.page.goto(BASE_URL)
                await self.page.fill('#username', CHANNEL_ID)
                await self.page.click('#searchbtn')
                await self.page.wait_for_url('**/youtube/dashboard')
                
                # الذهاب لصفحة كسب النقاط وتفعيل التحقق التلقائي
                await self.page.goto('https://mytoolstown.com/youtube/earn')
                # تفعيل خيار التحقق التلقائي إذا لم يكن مفعلاً
                checkbox = await self.page.query_selector('input[type="checkbox"]')
                if checkbox:
                    is_checked = await checkbox.is_checked()
                    if not is_checked:
                        await self.page.click('label:has-text("Automatically verify")')
        except Exception as e:
            logging.error(f"Error initializing browser: {e}")
            # إعادة التصفير للمحاولة مرة أخرى
            self.browser = None
            raise e

    async def ensure_initialized(self):
        if not self.page:
            await self.init_browser()

    async def get_task(self):
        await self.ensure_initialized()
        await self.page.reload()
        # البحث عن زر الاشتراك أو الإعجاب
        earn_btn = await self.page.query_selector('#earnBtn')
        if not earn_btn:
            # محاولة العودة لصفحة الكسب إذا تهنا
            await self.page.goto('https://mytoolstown.com/youtube/earn')
            earn_btn = await self.page.query_selector('#earnBtn')
            if not earn_btn:
                return None, "لا توجد مهام حالياً أو حدث خطأ في تحميل الصفحة."
        
        task_text = await self.page.inner_text('.card-body b')
        
        # استخراج الرابط بالضغط على الزر في نافذة جديدة
        async with self.context.expect_page() as new_page_info:
            await earn_btn.click()
        new_page = await new_page_info.value
        youtube_url = new_page.url
        await new_page.close()
        
        return youtube_url, task_text

    async def verify_task(self):
        await self.ensure_initialized()
        verify_btn = await self.page.query_selector('#verifybtn')
        if verify_btn:
            await verify_btn.click()
            await asyncio.sleep(3) # انتظار معالجة الطلب
            credits_text = await self.page.inner_text('h2:has-text("Your Credits")')
            return f"تم التحقق! {credits_text}"
        return "لم يتم العثور على زر التحقق. جرب طلب مهمة جديدة."

bot_logic = MyToolsTownBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً بك! اضغط على الزر أدناه للبدء.")
    keyboard = [[InlineKeyboardButton("الحصول على مهمة جديدة 🚀", callback_data='get_task')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("البوت جاهز لخدمتك.", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'get_task':
        await query.edit_message_text("جاري البحث عن مهمة... (قد يستغرق ذلك بضع ثوانٍ)")
        try:
            url, text = await bot_logic.get_task()
            if url:
                msg = f"المهمة: {text}\n\nالرابط: {url}\n\nقم بتنفيذ المهمة ثم اضغط على الزر أدناه للتحقق."
                keyboard = [[InlineKeyboardButton("تم التنفيذ ✅ - تحقق الآن", callback_data='verify_task')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.reply_text(msg, reply_markup=reply_markup)
            else:
                await query.edit_message_text(f"عذراً: {text}")
        except Exception as e:
            await query.edit_message_text(f"حدث خطأ أثناء الاتصال بالموقع: {str(e)}\nيرجى المحاولة مرة أخرى.")
            
    elif query.data == 'verify_task':
        await query.edit_message_text("جاري التحقق من الموقع...")
        try:
            result = await bot_logic.verify_task()
            keyboard = [[InlineKeyboardButton("مهمة أخرى 🔄", callback_data='get_task')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(result, reply_markup=reply_markup)
        except Exception as e:
            await query.edit_message_text(f"خطأ أثناء التحقق: {str(e)}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("Bot is running...")
    application.run_polling()
