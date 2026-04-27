# Конфигурация Telegram-бота MTZ_UFA

import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Токен вашего бота от BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "ВАШ_ТОКЕН_ЗДЕСЬ")

# ID админ-группы для отправки отчётов (опционально)
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", 0))

# Путь к базе данных товаров
PRODUCTS_FILE = "data/products.xlsx"

# Пути к файлам данных
USERS_FILE = "data/users.json"
CARTS_FILE = "data/carts.json"

# Папка с изображениями
IMAGES_FOLDER = "data/product_images"

# Лог-файл
LOG_FILE = "logs/bot.log"

# Настройки логирования
LOG_LEVEL = "INFO"

# Таймауты и ограничения
SEARCH_RESULTS_LIMIT = 10
MAX_CART_ITEMS = 50
