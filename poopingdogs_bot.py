import os
import time
import sqlite3
import telebot
import logging
import hashlib
import random
import string
import numpy as np
from telebot import types
from dotenv import load_dotenv
from PIL import Image
from model_utils import load_yolo_model


LOG_FILE = "bot_debug.log"
IMAGES_DIR = "images"
BAN_PROCENT = 30  # процент фото без собак, когда забанит

# Текстовые константы
WELCOME_MESSAGE = """
🐕‍🦺 Привет, друг! 🐩

Нам необходимо собрать много фото какающих собак 💩🐶.
Помоги нам обучить нейросеть, которая будет находить недобросовестных хозяев,
не убирающих за своими питомцами! 🕵️‍♂️🔍

📸 Отправьте мне фото собаки "в процессе", можно с разных ракурсов
🗄️ Я сохраню его в нашей базе данных
🖼️ Чем больше кадров - тем точнее будет наша нейросеть
📊 Вы сможете посмотреть свою статистику

🚀 Вместе научим ИИ находить нарушителей чистоты! ♻️

P.S. Каждая отправленная фотография - это шаг к цивилизованному выгулу собак! 🏆
"""

# Загрузка модели YOLOv8
model = load_yolo_model()

# Загружаем переменные окружения из .env файла
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Не найден TELEGRAM_BOT_TOKEN в переменных окружения!")

# Инициализация бота
bot = telebot.TeleBot(TOKEN)
os.makedirs(IMAGES_DIR, exist_ok=True)

# Настройка расширенного логирования
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Кастомное исключение для ошибок БД"""

    pass


def generate_random_string(length=8):
    """Генерирует случайную строку из букв и цифр"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def is_dog_on_image(image_path):
    """
    Проверяет, есть ли собака на изображении с помощью YOLOv8
    Возвращает True если найдена хотя бы одна собака
    """
    try:
        # Открываем изображение
        img = Image.open(image_path)

        # Преобразуем в numpy array
        img_array = np.array(img)

        # Детекция объектов
        results = model(img_array)

        # Класс "собака" в COCO dataset имеет индекс 16
        dog_class_id = 16

        # Проверяем все обнаруженные объекты
        for result in results:
            for box in result.boxes:
                if int(box.cls) == dog_class_id:
                    return True
        return False

    except Exception as e:
        logger.error(f"Ошибка при анализе изображения: {str(e)}")
        return False


def get_db_connection():
    """Устанавливает соединение с БД с детальным логированием"""
    try:
        conn = sqlite3.connect("bot_database.db")
        conn.row_factory = sqlite3.Row
        logger.debug("Успешное подключение к БД")
        return conn
    except sqlite3.Error as e:
        error_msg = f"Ошибка подключения к БД: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise DatabaseError(error_msg)


def execute_db_query(query, params=(), commit=False):
    """Универсальная функция для выполнения запросов с логированием"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        logger.debug(f"Выполнение запроса: {query}")
        logger.debug(f"Параметры: {params}")

        cursor.execute(query, params)

        if commit:
            conn.commit()
            logger.debug("Запрос успешно выполнен и закоммичен")
            return None
        else:
            result = cursor.fetchall()
            logger.debug("Запрос на получение данных успешно выполнен")
            return result

    except sqlite3.Error as e:
        error_msg = f"Ошибка выполнения запроса: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise DatabaseError(error_msg)
    finally:
        if conn:
            conn.close()
            logger.debug("Соединение с БД закрыто")


def get_or_create_user(telegram_id):
    """Получаем или создаем пользователя с расширенным логированием"""
    try:
        logger.info(f"Поиск пользователя с telegram_id={telegram_id}")

        # Проверяем существование пользователя
        user = execute_db_query(
            "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
        )

        if user:
            user_id = user[0]["id"]
            logger.info(f"Найден существующий пользователь: ID={user_id}")
            return user_id
        else:
            logger.info("Пользователь не найден, создаем нового")

            # Вставляем нового пользователя и сразу получаем его ID
            execute_db_query(
                "INSERT INTO users (telegram_id) VALUES (?)",
                (telegram_id,),
                commit=True,
            )

            # Получаем ID только что созданного пользователя
            new_user = execute_db_query(
                "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
            )

            if not new_user:
                raise DatabaseError("Не удалось получить ID "
                                    "созданного пользователя")

            user_id = new_user[0]["id"]
            logger.info(f"Создан новый пользователь: ID={user_id}")
            return user_id

    except DatabaseError as e:
        logger.critical(
            f"Критическая ошибка при работе с пользователем: {str(e)}",
            exc_info=True
        )
        raise


def save_photo_to_db(user_id, file_name, file_hash):
    """Сохраняет информацию о фото с проверкой на собак"""
    try:
        file_path = os.path.join(IMAGES_DIR, file_name)

        # Проверяем, есть ли собака на фото
        is_dog = is_dog_on_image(file_path)

        logger.info(
            f"Сохранение фото для user_id={user_id}, "
            f"имя={file_name}, is_dog={is_dog}"
        )

        execute_db_query(
            """
            INSERT INTO images (name, user_id, is_dog, file_hash)
            VALUES (?, ?, ?, ?)
            """,
            (file_name, user_id, int(is_dog), file_hash),
            commit=True,
        )

        logger.info("Фото успешно сохранено в БД")
        return is_dog  # Возвращаем также информацию о наличии собаки

    except DatabaseError as e:
        logger.error(f"Ошибка при сохранении фото в БД: {str(e)}",
                     exc_info=True)
        raise


def get_user_photo_stats(db_user_id):
    """
    Возвращает статистику по фотографиям пользователя
    :param db_user_id: ID пользователя в БД (не telegram_id)
    :return: tuple (total_photos, dog_photos) или None при ошибке
    """
    try:
        # Получаем общее количество фото и количество фото с собаками
        result = execute_db_query(
            """
            SELECT
                COUNT(*) as total_photos,
                SUM(CASE WHEN is_dog = 1 THEN 1 ELSE 0 END) as dog_photos
            FROM images
            WHERE user_id = ?
            """,
            (db_user_id,),
        )

        if result and len(result) > 0:
            return result[0]["total_photos"], result[0]["dog_photos"]
        return 0, 0  # Если у пользователя нет фото

    except DatabaseError as e:
        logger.error(f"Ошибка получения статистики для user_id={db_user_id}: "
                     f"{str(e)}")
        return None


def ban_user(db_user_id):
    """
    Устанавливает бан пользователю
    :param user_db_id: ID пользователя в БД (не telegram_id)
    :return: True если успешно, False при ошибке
    """
    try:
        execute_db_query(
            "UPDATE users SET ban_status = 1 WHERE id = ?",
            (db_user_id,),
            commit=True
        )
        logger.info(f"Пользователь с ID {db_user_id} 'забанен'")
        return True
    except DatabaseError as e:
        logger.error(f"Ошибка изменения ban_status для user_id={db_user_id}: "
                     f"{str(e)}")
        return False


def is_user_banned(db_user_id):
    """
    Проверяет, забанен ли пользователь
    :param db_user_id: ID пользователя в БД
    :return: True если забанен, False если нет или ошибка
    """
    try:
        result = execute_db_query(
            "SELECT ban_status FROM users WHERE id = ?", (db_user_id,)
        )
        if result and len(result) > 0:
            # В SQLite булево значение хранится как 0/1
            return bool(result[0]["ban_status"])
        return False
    except DatabaseError as e:
        logger.error(f"Ошибка проверки бана для user_id={db_user_id}: "
                     f"{str(e)}")
        return False


def calculate_file_hash(file_content):
    """Вычисляет SHA-256 хеш файла из его содержимого"""
    sha256 = hashlib.sha256()
    sha256.update(file_content)
    return sha256.hexdigest()


@bot.message_handler(commands=["start"])
def handle_start(message):
    """Обработчик команды /start с кнопкой"""
    try:
        user_id = message.from_user.id
        logger.info(f"Обработка /start от user_id={user_id}")

        # Создаем клавиатуру с кнопками
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = [
            types.KeyboardButton("Старт"),
            types.KeyboardButton("Ваша статистика"),
        ]
        markup.add(*buttons)

        # Отправляем приветственное сообщение
        bot.send_message(message.chat.id, WELCOME_MESSAGE, reply_markup=markup)

        logger.debug(f"Приветственное сообщение отправлено user_id={user_id}")

    except Exception as e:
        logger.error(f"Ошибка в handle_start: {str(e)}", exc_info=True)
        bot.reply_to(message, "❌ Произошла ошибка при обработке команды")


@bot.message_handler(func=lambda message: message.text == "Старт")
def handle_start_button(message):
    """Обработчик кнопки Старт"""
    handle_start(message)  # Используем ту же логику, что и для /start


@bot.message_handler(func=lambda message: message.text == "Ваша статистика")
def handle_stats_button(message):
    """Обработчик кнопки статистики"""
    try:
        user_id = message.from_user.id
        user_db_id = get_or_create_user(user_id)
        stats = get_user_photo_stats(user_db_id)

        if stats is None:
            bot.reply_to(message, "❌ Ошибка статистики")
            return

        total, dogs = stats

        # Формируем красивое сообщение со статистикой
        if total > 0:
            percentage = (dogs / total) * 100
            response = (
                f"📊 <b>Ваша статистика:</b>\n\n"
                f"📸 Всего фото: <b>{total}</b>\n"
                f"🐶 Фото с собаками: <b>{dogs}</b>\n"
                f"📈 Процент собак: <b>{percentage:.1f}%</b>\n\n"
                f"{'🐾Вы большой любитель собак!🐕' if percentage > 90 else ''}"
            )
        else:
            response = "📊 Вы еще не загрузили ни одного фото"

        bot.reply_to(message, response, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка в handle_stats_button: {str(e)}", exc_info=True)
        bot.reply_to(message, "❌ Произошла ошибка при получении статистики")


@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    """Обработчик фотографий с расширенным логированием"""
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "без username"
        current_time = time.time()

        logger.info(f"Получено фото от user_id={user_id} (@{username})")

        # Получаем или создаём пользователя в БД
        try:
            db_user_id = get_or_create_user(user_id)
        except DatabaseError:
            logger.error("Не удалось получить/создать пользователя")
            bot.reply_to(message, "⛔ Ошибка сервера. Попробуйте позже.")
            return

        # Проверка на бан
        ban_status = is_user_banned(db_user_id)
        if ban_status:
            logger.warning(
                f"Заблокированный пользователь пытался отправить фото: "
                f"telegram_id={user_id}"
            )
            bot.reply_to(message, "⛔ Вы заблокированы!")
            return

        # Обработка фото
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_extension = file_info.file_path.split(".")[-1]
        random_str = generate_random_string()  # Генерируем случайную строку
        file_name = f"photo_{user_id}_{int(current_time)}_{random_str}.{file_extension}"
        file_path = os.path.join(IMAGES_DIR, file_name)

        logger.debug(f"Сохранение фото: {file_name}")

        try:
            downloaded_file = bot.download_file(file_info.file_path)

            # Вычисляем хеш файла
            file_hash = calculate_file_hash(downloaded_file)

            # Проверяем дубликат в БД
            duplicate = execute_db_query(
                "SELECT 1 FROM images WHERE file_hash = ?",
                (file_hash,)
            )
            if duplicate:
                bot.reply_to(message, "⏭️ Это фото уже было загружено ранее")
                return

            with open(file_path, "wb") as new_file:
                new_file.write(downloaded_file)

            # Сохраняем в БД с проверкой на собак
            try:
                is_dog = save_photo_to_db(db_user_id, file_name, file_hash)
                if is_dog:
                    bot.reply_to(message, "✅ Фото сохранено! "
                                          "🐶 Обнаружена собака!")
                else:
                    bot.reply_to(message, "✅ Фото сохранено! "
                                          "(Собака не обнаружена)")
            except DatabaseError:
                bot.reply_to(
                    message, "✅ Фото сохранено, "
                             "но возникла проблема с базой данных"
                )

            # Проверим, надо ли забанить пользователя
            total_photos, dog_photos = get_user_photo_stats(db_user_id)
            logger.info(
                f"Статистика пользоватля c ID {db_user_id}: "
                f"всего {total_photos}, c собаками {dog_photos}"
            )
            if (
                total_photos > 20
                and 100*(total_photos-dog_photos)/total_photos > BAN_PROCENT
            ):
                ban_user(db_user_id)

        except Exception as e:
            logger.error(f"Ошибка сохранения файла: {str(e)}", exc_info=True)
            bot.reply_to(message, "❌ Ошибка при сохранении фото")

    except Exception as e:
        logger.critical(
            f"Необработанная ошибка в handle_photo: {str(e)}", exc_info=True
        )
        bot.reply_to(message, "❌ Произошла непредвиденная ошибка")


if __name__ == "__main__":
    try:
        logger.info("----- Бот запущен -----")
        logger.debug(f"Папка для изображений: {IMAGES_DIR}")
        bot.infinity_polling()
    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}", exc_info=True)
    finally:
        logger.info("----- Бот остановлен -----")
