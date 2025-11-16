FROM python:3.11-slim
WORKDIR /app

RUN pip install feedparser requests Flask

COPY bot.py app.py requirements.txt ./
COPY templates/ ./templates/

EXPOSE 5000

# Lance bot.py et app.py en même temps
CMD sh -c "python -u bot.py & python -u app.py"
