# Этап сборки (Builder)
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Отключаем создание кэшей __pycache__, чтобы уменьшить вес
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Сначала копируем файлы зависимостей.
# Это позволяет Docker'у кэшировать установку библиотек.
# Если ты поменяешь код, но не библиотеки, этот шаг пропустится (сэкономит время).
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимости в виртуальное окружение внутри контейнера
# --frozen: гарантирует, что версии строго совпадут с uv.lock
# --no-dev: не ставим тестовые утилиты на прод
RUN uv sync --frozen --no-dev

# Копируем весь остальной код
COPY . .

# Этап запуска (Runtime)
# Берем чистый, легкий Linux (slim) без лишнего мусора
FROM python:3.12-slim-bookworm AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng libgl1-mesa-glx && rm -rf /var/lib/apt/lists/*

# Копируем виртуальное окружение из этапа сборки
COPY --from=builder /app /app

WORKDIR /app

# Добавляем виртуальное окружение в путь, чтобы python видел библиотеки
ENV PATH="/app/.venv/bin:$PATH"

# Запускаем бота
CMD ["python", "main.py"]
