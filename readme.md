![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white&style=flat)
![Telegram API](https://img.shields.io/badge/Telegram_Bot_API-26A5E4?logo=telegram&logoColor=white&style=flat)
![YOLOv8](https://img.shields.io/badge/YOLOv8-00FFFF?logo=ultralytics&logoColor=black&style=flat)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white&style=flat)
![NumPy](https://img.shields.io/badge/NumPy-013243?logo=numpy&logoColor=white&style=flat)
![Pillow](https://img.shields.io/badge/Pillow-8F2D4D?logo=pillow&logoColor=white&style=flat)

# Pooping Dogs Bot 🐕💩

Телеграм-бот для сбора фотографий собак в процессе дефекации с целью обучения нейросети для выявления недобросовестных хозяев.

## Описание проекта

Бот собирает фотографии собак "в процессе" для обучения модели компьютерного зрения (YOLOv8), которая сможет автоматически обнаруживать подобные ситуации в городской среде. Это поможет в борьбе с нарушителями чистоты в общественных местах.

## Функционал

- 📸 Прием фотографий от пользователей
- 🖼️ Проверка наличия собаки на фото с помощью YOLOv8
- 🗄️ Хранение данных в SQLite базе
- 📊 Статистика по загруженным фото
- ⚠️ Автоматический бан пользователей, загружающих много фото без собак

## Установка и запуск

### 1. Клонирование репозитория
```
git clone https://github.com/NikitaPolechshuk/Pooping-Dogs-Telegram-Bot.git
cd Pooping-Dogs-Telegram-Bot
```

### 2. Cоздать и активировать виртуальное окружение:

```
python3 -m venv venv   # Для Linux/Mac
python -m venv venv   # Для Windows
```

```
source venv/bin/activate   # Для Linux/Mac
venv\Scripts\activate.bat   # Для Windows
```

### 3. Установить зависимости из файла requirements.txt:

```
pip install -r requirements.txt
```
### 4. Настройка окружения
Создайте файл .env в корне проекта и добавьте токен бота:
```
TELEGRAM_BOT_TOKEN="ваш_токен_бота"
```

### 5. Инициализация базы данных
```
python init_db.py
```
(Создаст файл bot_database.db и необходимые таблицы)

### 6. Запуск бота
```
python poopingdogs_bot.py
```