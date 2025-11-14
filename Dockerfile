FROM python:3.11-slim
WORKDIR /app
RUN pip install feedparser requests
COPY bot.py .
CMD ["python", "-u", "bot.py"]
