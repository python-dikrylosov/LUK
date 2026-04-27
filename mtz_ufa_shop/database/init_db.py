"""
MTZ_UFA_SHOP - Инициализация базы данных
"""
import asyncio
import os
import sys

# Добавляем родительскую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import db_manager


async def init_database():
    """Инициализация базы данных и создание таблиц"""
    print("🚀 Инициализация базы данных...")
    
    try:
        # Инициализация БД
        await db_manager.init_db()
        print("✅ База данных успешно инициализирована")
        
        # Создадим тестовые данные
        print("\n📦 Создание тестовых данных...")
        
        # Тестовый администратор (замените telegram_id на свой)
        admin = await db_manager.create_user(
            telegram_id=123456789,  # Замените на ваш Telegram ID
            full_name="Администратор",
            username="admin",
            role=db_manager.models.UserRole.ADMIN
        )
        print(f"✅ Создан администратор: {admin.full_name}")
        
        # Тестовые товары
        test_products = [
            {
                "article": "MTZ-80-001",
                "name": "Фильтр масляный МТЗ-80",
                "category": "Фильтры",
                "price": 450.0,
                "tractor_model": "MTZ",
                "stock_quantity": 25,
                "description": "Масляный фильтр для тракторов МТЗ-80/82"
            },
            {
                "article": "MTZ-80-002",
                "name": "Фильтр воздушный МТЗ-80",
                "category": "Фильтры",
                "price": 680.0,
                "tractor_model": "MTZ",
                "stock_quantity": 15,
                "description": "Воздушный фильтр для тракторов МТЗ-80/82"
            },
            {
                "article": "YMZ-236-001",
                "name": "Поршень ЯМЗ-236",
                "category": "Двигатель",
                "price": 2500.0,
                "tractor_model": "YMZ",
                "stock_quantity": 10,
                "description": "Поршень для двигателей ЯМЗ-236"
            },
            {
                "article": "KAMAZ-001",
                "name": "Колодка тормозная КАМАЗ",
                "category": "Тормозная система",
                "price": 350.0,
                "tractor_model": "KAMAZ",
                "stock_quantity": 50,
                "description": "Тормозная колодка для автомобилей КАМАЗ"
            },
            {
                "article": "T150-001",
                "name": "Гусеница Т-150",
                "category": "Ходовая часть",
                "price": 15000.0,
                "tractor_model": "T150",
                "stock_quantity": 4,
                "description": "Гусеничная лента для трактора Т-150"
            }
        ]
        
        for product_data in test_products:
            product = await db_manager.create_product(**product_data)
            print(f"✅ Создан товар: {product.name} ({product.article})")
        
        print("\n" + "="*50)
        print("🎉 База данных готова к работе!")
        print("="*50)
        print("\n📊 Статистика:")
        print(f"   - Пользователей: 1")
        print(f"   - Товаров: {len(test_products)}")
        print("\n💡 Для запуска бота выполните: python bot.py")
        
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(init_database())
