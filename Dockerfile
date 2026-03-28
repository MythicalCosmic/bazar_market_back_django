FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir \
    "django>=6.0.3" \
    "django-redis>=6.0.0" \
    "psycopg[binary]>=3.3.3" \
    gunicorn

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
CMD ["gunicorn", "bazar_market_django.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
