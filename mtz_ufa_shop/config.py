"""
MTZ_UFA_SHOP - Конфигурация проекта
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Загрузка переменных окружения
load_dotenv()


class Config:
    """Конфигурация приложения"""
    
    # Telegram Bot
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    # Администраторы
    ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
    
    # База данных
    DATABASE_PATH = os.getenv("DATABASE_PATH", "data/shop.db")
    
    # Директории
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / "data"
    IMAGES_DIR = Path(os.getenv("IMAGES_DIR", DATA_DIR / "images"))
    EXPORTS_DIR = Path(os.getenv("EXPORTS_DIR", DATA_DIR / "exports"))
    LOGS_DIR = Path(os.getenv("LOGS_DIR", BASE_DIR / "logs"))
    
    # Валюта
    CURRENCY_SYMBOL = os.getenv("CURRENCY_SYMBOL", "₽")
    
    # Настройки бота
    BOT_NAME = "MTZ_UFA_SHOP"
    BOT_VERSION = "1.0.0"
    
    # Пагинация
    PAGE_SIZE = 10
    
    @classmethod
    def create_directories(cls):
        """Создание необходимых директорий"""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        cls.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def is_admin(cls, telegram_id: int) -> bool:
        """Проверка является ли пользователь администратором"""
        return telegram_id in cls.ADMIN_IDS


# Глобальный объект конфигурации
config = Config()
config.create_directories()
