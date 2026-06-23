# دليل تحديث بوت MyToolsTown

تم تحديث الكود الخاص بك لتعزيز الأمان من خلال نقل القيم الحساسة (مثل توكن البوت ومعرف القناة) من الكود المصدري إلى **متغيرات البيئة (Environment Variables)**. هذا الإجراء يمنع تسريب بياناتك في حال مشاركة الكود أو رفعه على منصات مثل GitHub.

## التغييرات الرئيسية

تم استبدال القيم الثابتة بالدالة `os.getenv()`، وأضفنا تحققات للتأكد من وجود هذه القيم قبل تشغيل البوت:

| المتغير | الوصف | القيمة السابقة (كمرجع) |
| :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | توكن بوت التيليجرام الخاص بك | `8654824252:AAHW...` |
| `YOUTUBE_CHANNEL_ID` | معرف قناة اليوتيوب | `UCaamCgppPAegiY5kFseaU2A` |
| `MYTOOLSTOWN_BASE_URL` | رابط الإحالة الخاص بالموقع | `https://mytoolstown.com/...` |

## كيفية إعداد متغيرات البيئة

يمكنك إعداد هذه القيم بناءً على بيئة التشغيل الخاصة بك:

### 1. نظام Linux أو macOS (Terminal)
يمكنك تشغيل البوت بعد ضبط المتغيرات مؤقتاً في الجلسة الحالية:
```bash
export TELEGRAM_BOT_TOKEN="8654824252:AAHW-sVgPwFweQOenNVpT3ZG5ASz1I701IA"
export YOUTUBE_CHANNEL_ID="UCaamCgppPAegiY5kFseaU2A"
export MYTOOLSTOWN_BASE_URL="https://mytoolstown.com/youtube?referral_id=2088732"
python3 mytoolstown_bot.py
```

### 2. نظام Windows (PowerShell)
```powershell
$env:TELEGRAM_BOT_TOKEN="8654824252:AAHW-sVgPwFweQOenNVpT3ZG5ASz1I701IA"
$env:YOUTUBE_CHANNEL_ID="UCaamCgppPAegiY5kFseaU2A"
$env:MYTOOLSTOWN_BASE_URL="https://mytoolstown.com/youtube?referral_id=2088732"
python mytoolstown_bot.py
```

### 3. استخدام ملف `.env` (موصى به)
يمكنك إنشاء ملف باسم `.env` في نفس مجلد البوت ووضع القيم فيه، ثم استخدام مكتبة `python-dotenv` لتحميلها تلقائياً.

---
**ملاحظة:** تأكد من عدم مشاركة ملف `.env` أو القيم التي تضعها في سطر الأوامر مع أي شخص لضمان أمان حساباتك.
