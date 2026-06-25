FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Install system dependencies if any are missing
RUN apt-get update && apt-get install -y     python3-pip     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure playwright browsers are installed
RUN playwright install chromium

ENV PYTHONUNBUFFERED=1

CMD ["python", "mytoolstown_bot.py"]
