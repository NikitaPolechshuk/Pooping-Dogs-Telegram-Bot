import sqlite3


def init_database():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()

    # Удаляем существующие таблицы (если есть)
    cursor.execute("DROP TABLE IF EXISTS images")
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("DROP INDEX IF EXISTS idx_file_hash")

    # Создаём таблицу пользователей
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        ban_status BOOLEAN DEFAULT FALSE
    )
    """)

    # Создаём таблицу изображений с новым полем is_dog
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        file_hash TEXT NOT NULL UNIQUE,
        add_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        user_id INTEGER NOT NULL,
        is_dog BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    # Создаем индекс для быстрого поиска по хешу
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_file_hash ON images(file_hash)
    """)

    conn.commit()
    conn.close()
    print("База данных инициализирована!")


if __name__ == "__main__":
    init_database()
