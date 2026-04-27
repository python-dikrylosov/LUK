"""
MTZ_UFA_SHOP - Обработчики для продавцов
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

from config import config
from database.db_manager import db_manager
from database.models import UserRole

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
ADD_PRODUCT_ARTICLE, ADD_PRODUCT_NAME, ADD_PRODUCT_CATEGORY, ADD_PRODUCT_TRACTOR_MODEL = range(4)
ADD_PRODUCT_PRICE, ADD_PRODUCT_STOCK, ADD_PRODUCT_DESCRIPTION = range(4, 7)


async def seller_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Панель продавца"""
    user = update.effective_user
    db_user = await db_manager.get_user_by_telegram_id(user.id)
    
    if not db_user or db_user.role not in [UserRole.SELLER.value, UserRole.ADMIN.value]:
        await update.message.reply_text(
            "❌ У вас нет прав доступа к панели продавца.\n\n"
            "Обратитесь к администратору для получения прав."
        )
        return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить товар", callback_data="seller_add_product")],
        [InlineKeyboardButton("📦 Управление складом", callback_data="seller_stock_manage")],
        [InlineKeyboardButton("📋 Мои товары", callback_data="seller_my_products")],
        [InlineKeyboardButton("📊 Статистика продаж", callback_data="seller_stats")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
    ])
    
    await update.message.reply_text(
        f"🏪 **Панель продавца**\n\n"
        f"Добро пожаловать, {db_user.full_name}!\n\n"
        f"Выберите действие:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
    logger.info(f"Продавец {db_user.username} открыл панель продавца")


async def start_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать процесс добавления товара"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "➕ **Добавление нового товара**\n\n"
        "Введите **артикул** товара:\n\n"
        "_Пример: MTZ-80-001_",
        parse_mode='Markdown'
    )
    
    return ADD_PRODUCT_ARTICLE


async def get_article(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение артикула"""
    article = update.message.text.strip()
    
    # Проверяем, не занят ли артикул
    existing_product = await db_manager.get_product_by_article(article)
    if existing_product:
        await update.message.reply_text(
            f"❌ Товар с артикулом `{article}` уже существует!\n\n"
            f"Название: {existing_product.name}\n"
            f"Цена: {existing_product.price}{config.CURRENCY_SYMBOL}\n\n"
            "Введите другой артикул или измените существующий товар:",
            parse_mode='Markdown'
        )
        return ADD_PRODUCT_ARTICLE
    
    context.user_data['new_product'] = {'article': article}
    
    await update.message.reply_text(
        f"✅ Артикул: `{article}`\n\n"
        "Теперь введите **название товара**:\n\n"
        "_Пример: Фильтр масляный МТЗ-80_",
        parse_mode='Markdown'
    )
    
    return ADD_PRODUCT_NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение названия"""
    name = update.message.text.strip()
    context.user_data['new_product']['name'] = name
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚜 МТЗ", callback_data="cat_mtz")],
        [InlineKeyboardButton("⚙️ ЯМЗ", callback_data="cat_ymz")],
        [InlineKeyboardButton("🚛 КАМАЗ", callback_data="cat_kamaz")],
        [InlineKeyboardButton("🔧 Т-150", callback_data="cat_t150")],
        [InlineKeyboardButton("🔩 Прочее", callback_data="cat_other")]
    ])
    
    await update.message.reply_text(
        f"✅ Название: {name}\n\n"
        "Выберите **категорию** товара:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
    return ADD_PRODUCT_CATEGORY


async def get_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение категории (callback)"""
    query = update.callback_query
    await query.answer()
    
    category_map = {
        'cat_mtz': 'Двигатель',
        'cat_ymz': 'Трансмиссия',
        'cat_kamaz': 'Ходовая часть',
        'cat_t150': 'Электрооборудование',
        'cat_other': 'Прочее'
    }
    
    category = category_map.get(query.data, 'Прочее')
    context.user_data['new_product']['category'] = category
    
    await query.edit_message_text(
        f"✅ Категория: {category}\n\n"
        "Выберите **модель трактора**:\n\n"
        "Или введите текстом, если нужной модели нет в списке.",
        parse_mode='Markdown'
    )
    
    # Сохраняем следующее состояние
    context.user_data['next_state'] = ADD_PRODUCT_TRACTOR_MODEL
    return ADD_PRODUCT_TRACTOR_MODEL


async def get_tractor_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение модели трактора"""
    # Проверяем, это callback или текст
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        tractor_model = query.data.replace("tractor_", "").upper()
        await query.edit_message_text(
            f"✅ Модель: {tractor_model}\n\n"
            "Теперь введите **цену** товара (только число):\n\n"
            f"_Пример: 1500_",
            parse_mode='Markdown'
        )
    else:
        tractor_model = update.message.text.strip().upper()
        await update.message.reply_text(
            f"✅ Модель: {tractor_model}\n\n"
            "Теперь введите **цену** товара (только число):\n\n"
            f"_Пример: 1500_",
            parse_mode='Markdown'
        )
    
    context.user_data['new_product']['tractor_model'] = tractor_model
    
    return ADD_PRODUCT_PRICE


async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение цены"""
    try:
        price = float(update.message.text.strip())
        if price <= 0:
            raise ValueError("Цена должна быть положительной")
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат цены!\n\n"
            "Введите положительное число:\n"
            "_Пример: 1500 или 1500.50_",
            parse_mode='Markdown'
        )
        return ADD_PRODUCT_PRICE
    
    context.user_data['new_product']['price'] = price
    
    await update.message.reply_text(
        f"✅ Цена: {price}{config.CURRENCY_SYMBOL}\n\n"
        "Введите **количество на складе**:\n\n"
        "_Пример: 50_",
        parse_mode='Markdown'
    )
    
    return ADD_PRODUCT_STOCK


async def get_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение количества на складе"""
    try:
        stock = int(update.message.text.strip())
        if stock < 0:
            raise ValueError("Количество не может быть отрицательным")
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат количества!\n\n"
            "Введите целое неотрицательное число:\n"
            "_Пример: 50_",
            parse_mode='Markdown'
        )
        return ADD_PRODUCT_STOCK
    
    context.user_data['new_product']['stock_quantity'] = stock
    
    await update.message.reply_text(
        f"✅ Количество: {stock} шт.\n\n"
        "Введите **описание товара** (или пропустите, нажав /skip):\n\n"
        "_Пример: Масляный фильтр для двигателя Д-240_",
        parse_mode='Markdown'
    )
    
    return ADD_PRODUCT_DESCRIPTION


async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение описания и завершение"""
    description = update.message.text.strip()
    
    if description == "/skip":
        description = None
    
    # Получаем данные товара
    product_data = context.user_data.get('new_product', {})
    
    # Создаем товар в БД
    try:
        new_product = await db_manager.create_product(
            article=product_data['article'],
            name=product_data['name'],
            category=product_data['category'],
            price=product_data['price'],
            description=description,
            tractor_model=product_data.get('tractor_model'),
            stock_quantity=product_data.get('stock_quantity', 0)
        )
        
        success_text = (
            "✅ **Товар успешно добавлен!**\n\n"
            f"📦 **Информация о товаре:**\n\n"
            f"• Артикул: `{new_product.article}`\n"
            f"• Название: {new_product.name}\n"
            f"• Категория: {new_product.category}\n"
            f"• Модель: {new_product.tractor_model or 'Не указана'}\n"
            f"• Цена: {new_product.price}{config.CURRENCY_SYMBOL}\n"
            f"• На складе: {new_product.stock_quantity} шт.\n"
            f"• Описание: {description or 'Нет описания'}\n\n"
            f"**ID товара:** {new_product.id}\n\n"
            "Что добавить еще один товар, нажмите /add_product\n"
            "Для возврата в меню: /seller_panel"
        )
        
        await update.message.reply_text(success_text, parse_mode='Markdown')
        logger.info(f"Товар {new_product.article} добавлен продавцом")
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка при добавлении товара: {str(e)}\n\n"
            "Попробуйте еще раз или обратитесь к администратору."
        )
        logger.error(f"Ошибка при добавлении товара: {e}")
    
    # Очищаем данные
    context.user_data.pop('new_product', None)
    
    return ConversationHandler.END


async def cancel_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена добавления товара"""
    context.user_data.pop('new_product', None)
    
    await update.message.reply_text(
        "❌ Добавление товара отменено.\n\n"
        "Для возврата в панель продавца: /seller_panel"
    )
    
    return ConversationHandler.END


async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск описания"""
    return await get_description(update, context)


async def my_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать товары продавца"""
    user = update.effective_user
    db_user = await db_manager.get_user_by_telegram_id(user.id)
    
    if not db_user or db_user.role not in [UserRole.SELLER.value, UserRole.ADMIN.value]:
        await update.message.reply_text("❌ Нет доступа")
        return
    
    products = await db_manager.get_all_products()
    
    if not products:
        await update.message.reply_text("📦 Список товаров пуст")
        return
    
    text = f"📦 **Все товары** ({len(products)} шт.):\n\n"
    
    for product in products[:20]:  # Показываем первые 20
        stock_status = "✅" if product.stock_quantity > 0 else "❌"
        low_stock = "⚠️" if product.is_low_stock() else ""
        
        text += (
            f"{stock_status}{low_stock} **{product.name}**\n"
            f"  Артикул: `{product.article}`\n"
            f"  Цена: {product.price}{config.CURRENCY_SYMBOL}\n"
            f"  Склад: {product.stock_quantity} шт.\n\n"
        )
    
    if len(products) > 20:
        text += f"... и еще {len(products) - 20} товаров"
    
    await update.message.reply_text(text, parse_mode='Markdown')


# Создание ConversationHandler для добавления товара
def get_add_product_handler():
    """Создать обработчик диалога добавления товара"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_product, pattern="^seller_add_product$")],
        states={
            ADD_PRODUCT_ARTICLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_article)],
            ADD_PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ADD_PRODUCT_CATEGORY: [CallbackQueryHandler(get_category_callback, pattern="^cat_")],
            ADD_PRODUCT_TRACTOR_MODEL: [
                CallbackQueryHandler(get_tractor_model, pattern="^tractor_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_tractor_model)
            ],
            ADD_PRODUCT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
            ADD_PRODUCT_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_stock)],
            ADD_PRODUCT_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_description),
                CommandHandler('skip', skip_description)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_add_product)],
        allow_reentry=True
    )


def get_seller_handlers():
    """Получить все обработчики для продавцов"""
    return [
        CommandHandler("seller_panel", seller_panel),
        CommandHandler("add_product", seller_panel),  # Альтернативный вход
        CommandHandler("my_products", my_products),
        get_add_product_handler()
    ]
