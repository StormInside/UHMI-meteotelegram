# Використання базового образу Python 3.12
FROM python:3.12

# Оновлення та встановлення необхідних залежностей
RUN apt-get update && apt-get install -y \
    libasound2 libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 \
    libcups2 libdbus-1-3 libdrm2 libgbm1 libgtk-3-0 libnspr4 \
    libnss3 libu2f-udev libvulkan1 libxcomposite1 libxdamage1 \
    libxfixes3 libxkbcommon0 libxrandr2 xdg-utils \
    && apt-get clean

# Створення директорії для коду
RUN mkdir -p /opt/code/meteo_telegram

# Встановлення робочої директорії
WORKDIR /opt/code/meteo_telegram

# Встановлення та оновлення pip
RUN pip install --upgrade pip setuptools

# Копіювання файлу requirements.txt та встановлення залежностей
COPY requirements.txt /opt/code/meteo_telegram/
RUN pip install --no-cache-dir -r /opt/code/meteo_telegram/requirements.txt

# Копіювання всього коду в контейнер
COPY . /opt/code/meteo_telegram/

# Встановлення змінних середовища
ENV LANG C.UTF-8
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH "${PYTHONPATH}:$(pwd)"

# Відкриття порту 8000 для FastAPI
EXPOSE 8000

# Запуск FastAPI програми
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
