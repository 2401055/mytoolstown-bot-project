FROM mcr.microsoft.com/playwright/python:v1.55.0-jammy

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Ensure playwright browsers are installed (though they should be in the image)
RUN playwright install chromium

CMD ["python", "mytoolstown_bot.py"]
