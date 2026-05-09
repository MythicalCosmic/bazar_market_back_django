FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for psycopg, pillow, escpos
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc libusb-1.0-0 libjpeg62-turbo-dev zlib1g-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Non-root user — limits blast radius of any RCE.
RUN groupadd -r app && useradd -r -g app -m -d /home/app app

COPY --chown=app:app . .

RUN chmod +x entrypoint.sh

USER app
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "bazar_market_django.asgi:application"]
