"""
MTZ_UFA_SHOP - Основной файл бота
"""
import asyncio
import logging
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from config import config
from database.db_manager import db_manager
from keyboards.main_menu import get_main_menu_keyboard
from handlers.seller import get_seller_handlers


# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename=config.LOGS_DIR / 'bot.log'
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    
    # Проверяем есть ли пользователь в БД
    db_user = await db_manager.get_user_by_telegram_id(user.id)
    
    if not db_user:
        # Создаем нового пользователя
        db_user = await db_manager.create_user(
            telegram_id=user.id,
            full_name=user.full_name,
            username=user.username
        )
        welcome_text = (
            f"👋 Добро пожаловать, {user.first_name}!\n\n"
            f"Я бот магазина запчастей MTZ_UFA_SHOP.\n"
            f"Здесь вы найдете запчасти для:\n"
            f"🚜 МТЗ | ⚙️ ЯМЗ | 🚛 КАМАЗ | 🔧 Т-150\n\n"
            f"Выберите действие в меню ниже 👇"
        )
    else:
        welcome_text = (
            f"👋 С возвращением, {user.first_name}!\n\n"
            f"Рад вас видеть снова в MTZ_UFA_SHOP!"
        )
    
    # Получаем клавиатуру в зависимости от роли
    keyboard = get_main_menu_keyboard(db_user.role)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=keyboard
    )
    
    logger.info(f"Пользователь {user.username} ({user.id}) запустил бота")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "📚 **Справка по боту MTZ_UFA_SHOP**\n\n"
        "**Основные команды:**\n"
        "/start - Запустить бота\n"
        "/catalog - Каталог товаров\n"
        "/search - Поиск запчастей\n"
        "/cart - Корзина\n"
        "/profile - Личный кабинет\n"
        "/schematic - Схемы тракторов\n"
        "/help - Эта справка\n\n"
        "**Для продавцов:**\n"
        "/seller_panel - Панель продавца\n"
        "/add_product - Добавить товар\n"
        "/stock_manage - Управление складом\n\n"
        "**Для администраторов:**\n"
        "/admin_panel - Панель администратора\n"
        "/statistics - Статистика\n"
        "/export_data - Экспорт данных\n\n"
        "💡 Нажмите на кнопку в меню для быстрого доступа!"
    )
    
    await update.message.reply_text(help_text)


async def catalog_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /catalog"""
    from keyboards.main_menu import get_catalog_categories
    
    text = (
        "🛒 **Каталог товаров**\n\n"
        "Выберите категорию или модель техники:"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=get_catalog_categories(),
        parse_mode='Markdown'
    )


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /search"""
    text = (
        "🔍 **Поиск запчастей**\n\n"
        "Введите название товара или артикул для поиска:\n\n"
        "_Пример: фильтр масляный или MTZ-80-001_"
    )
    
    await update.message.reply_text(
        text,
        parse_mode='Markdown'
    )
    
    # Устанавливаем флаг поиска
    context.user_data['searching'] = True


async def cart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /cart"""
    from keyboards.main_menu import get_cart_keyboard
    
    # Получаем корзину из контекста
    cart = context.user_data.get('cart', {})
    
    if not cart:
        await update.message.reply_text(
            "🛒 Ваша корзина пуста.\n\n"
            "Перейдите в каталог, чтобы добавить товары."
        )
        return
    
    # Формируем сообщение с корзиной
    total = 0
    items_text = "🛒 **Ваша корзина:**\n\n"
    
    for product_id, item in cart.items():
        subtotal = item['price'] * item['quantity']
        total += subtotal
        items_text += (
            f"• {item['name']}\n"
            f"  {item['quantity']} шт. × {item['price']}{config.CURRENCY_SYMBOL} = "
            f"{subtotal}{config.CURRENCY_SYMBOL}\n\n"
        )
    
    items_text += f"\n**Итого: {total}{config.CURRENCY_SYMBOL}**"
    
    await update.message.reply_text(
        items_text,
        reply_markup=get_cart_keyboard(),
        parse_mode='Markdown'
    )


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /profile"""
    from keyboards.main_menu import get_profile_keyboard
    
    user = update.effective_user
    db_user = await db_manager.get_user_by_telegram_id(user.id)
    
    if not db_user:
        await update.message.reply_text("❌ Пользователь не найден. Нажмите /start")
        return
    
    # Получаем статистику пользователя
    orders = await db_manager.get_user_orders(db_user.id)
    total_spent = sum(order.total_amount for order in orders if order.status == 'delivered')
    
    profile_text = (
        f"👤 **Личный кабинет**\n\n"
        f"**Имя:** {db_user.full_name}\n"
        f"**Username:** @{db_user.username or 'не указан'}\n"
        f"**Телефон:** {db_user.phone or 'не указан'}\n"
        f"**Роль:** {db_user.role}\n\n"
        f"**Статистика:**\n"
        f"• Заказов: {len(orders)}\n"
        f"• Потрачено: {total_spent}{config.CURRENCY_SYMBOL}\n"
    )
    
    await update.message.reply_text(
        profile_text,
        reply_markup=get_profile_keyboard(),
        parse_mode='Markdown'
    )


async def schematic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /schematic"""
    from keyboards.main_menu import get_schematic_menu
    
    text = (
        "🚜 **Схемы тракторов**\n\n"
        "Выберите модель техники для просмотра схемы:\n\n"
        "_Нажмите на узел схемы, чтобы увидеть доступные запчасти_"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=get_schematic_menu(),
        parse_mode='Markdown'
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user_message = update.message.text
    
    # Обработка поиска
    if context.user_data.get('searching'):
        query = user_message
        products = await db_manager.search_products(query)
        
        if not products:
            await update.message.reply_text(
                f"❌ По запросу \"{query}\" ничего не найдено.\n\n"
                "Попробуйте другой запрос или выберите категорию в каталоге."
            )
        else:
            result_text = f"🔍 Найдено товаров: {len(products)}\n\n"
            for product in products[:10]:  # Показываем первые 10
                result_text += (
                    f"• **{product.name}**\n"
                    f"  Артикул: `{product.article}`\n"
                    f"  Цена: {product.price}{config.CURRENCY_SYMBOL}\n"
                    f"  В наличии: {product.stock_quantity} шт.\n\n"
                )
            
            await update.message.reply_text(
                result_text,
                parse_mode='Markdown'
            )
        
        context.user_data['searching'] = False
        return
    
    # Обработка команд меню
    if user_message == "🛒 Каталог":
        await catalog_command(update, context)
    elif user_message == "🔍 Поиск":
        await search_command(update, context)
    elif user_message == "📋 Корзина":
        await cart_command(update, context)
    elif user_message == "🚜 Схемы":
        await schematic_command(update, context)
    elif user_message == "👤 Профиль":
        await profile_command(update, context)
    elif user_message == "📞 Контакты":
        contact_text = (
            "📞 **Контакты**\n\n"
            "📍 Адрес: г. Уфа, ул. Примерная, 1\n"
            "📱 Телефон: +7 (999) 000-00-00\n"
            "📧 Email: info@mtz-ufa.ru\n"
            "🌐 Сайт: www.mtz-ufa.ru\n\n"
            "⏰ Режим работы:\n"
            "Пн-Пт: 9:00 - 18:00\n"
            "Сб: 10:00 - 15:00\n"
            "Вс: Выходной"
        )
        await update.message.reply_text(contact_text, parse_mode='Markdown')


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-запросов от inline-кнопок"""
    query = update.callback_query
    data = query.data
    
    await query.answer()
    
    if data == "main_menu":
        await query.edit_message_text(
            "Главное меню",
            reply_markup=get_main_menu_keyboard()
        )
    
    # Обработка категорий
    elif data.startswith("cat_"):
        category = data.replace("cat_", "")
        # Здесь будет логика показа товаров категории
        await query.edit_message_text(f"Категория: {category}")
    
    # Обработка добавления в корзину
    elif data.startswith("add_to_cart_"):
        product_id = int(data.replace("add_to_cart_", ""))
        # Логика добавления в корзину
        await query.edit_message_text(f"Товар {product_id} добавлен в корзину")


async def post_init(application: Application):
    """Инициализация после запуска"""
    # Установка команд бота
    commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("catalog", "Каталог товаров"),
        BotCommand("search", "Поиск запчастей"),
        BotCommand("cart", "Корзина"),
        BotCommand("profile", "Личный кабинет"),
        BotCommand("schematic", "Схемы тракторов"),
        BotCommand("help", "Справка")
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Команды бота установлены")


def main():
    """Основная функция запуска бота"""
    # Проверка токена
    if not config.BOT_TOKEN or config.BOT_TOKEN == "your_bot_token_here":
        print("❌ Ошибка: Не установлен BOT_TOKEN!")
        print("Скопируйте .env.example в .env и укажите ваш токен бота")
        return
    
    # Инициализация базы данных
    asyncio.run(db_manager.init_db())
    print("✅ База данных инициализирована")
    
    # Создание приложения
    application = Application.builder().token(config.BOT_TOKEN).post_init(post_init).build()
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("catalog", catalog_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("cart", cart_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("schematic", schematic_command))
    
    # Обработчики для продавцов
    for handler in get_seller_handlers():
        application.add_handler(handler)
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Запуск бота
    print(f"🤖 Запуск бота {config.BOT_NAME} v{config.BOT_VERSION}...")
    print("📊 Для остановки нажмите Ctrl+C")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
