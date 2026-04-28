FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir fastapi uvicorn aiofiles python-multipart python-dotenv

COPY . .

RUN mkdir -p data/files/tmp

EXPOSE 6767

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "6767"]
