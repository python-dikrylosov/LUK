"""
MTZ_UFA_SHOP - Клавиатуры для бота
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def get_main_menu_keyboard(role: str = "buyer") -> ReplyKeyboardMarkup:
    """Главное меню в зависимости от роли"""
    
    if role == "admin":
        keyboard = [
            [KeyboardButton("🛒 Каталог"), KeyboardButton("🔍 Поиск")],
            [KeyboardButton("📊 Панель администратора")],
            [KeyboardButton("👤 Профиль"), KeyboardButton("📞 Контакты")]
        ]
    elif role == "seller":
        keyboard = [
            [KeyboardButton("🛒 Каталог"), KeyboardButton("🔍 Поиск")],
            [KeyboardButton("🏪 Панель продавца")],
            [KeyboardButton("👤 Профиль"), KeyboardButton("📞 Контакты")]
        ]
    else:  # buyer
        keyboard = [
            [KeyboardButton("🛒 Каталог"), KeyboardButton("🔍 Поиск")],
            [KeyboardButton("📋 Корзина"), KeyboardButton("🚜 Схемы")],
            [KeyboardButton("👤 Профиль"), KeyboardButton("📞 Контакты")]
        ]
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_catalog_categories() -> InlineKeyboardMarkup:
    """Категории товаров"""
    keyboard = [
        [InlineKeyboardButton("🚜 МТЗ", callback_data="cat_mtz")],
        [InlineKeyboardButton("⚙️ ЯМЗ", callback_data="cat_ymz")],
        [InlineKeyboardButton("🚛 КАМАЗ", callback_data="cat_kamaz")],
        [InlineKeyboardButton("🔧 Т-150", callback_data="cat_t150")],
        [InlineKeyboardButton("📦 Все товары", callback_data="cat_all")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_product_card(product_id: int, in_cart: bool = False) -> InlineKeyboardMarkup:
    """Карточка товара"""
    buttons = []
    
    if in_cart:
        buttons.append(InlineKeyboardButton("✅ В корзине", callback_data="in_cart"))
    else:
        buttons.append(InlineKeyboardButton("🛒 В корзину", callback_data=f"add_to_cart_{product_id}"))
    
    buttons.append(InlineKeyboardButton("🔙 Назад", callback_data="catalog_back"))
    
    keyboard = [buttons]
    return InlineKeyboardMarkup(keyboard)


def get_cart_keyboard() -> InlineKeyboardMarkup:
    """Корзина"""
    keyboard = [
        [InlineKeyboardButton("📝 Оформить заказ", callback_data="checkout")],
        [InlineKeyboardButton("🗑️ Очистить корзину", callback_data="clear_cart")],
        [InlineKeyboardButton("🔙 Продолжить покупки", callback_data="catalog")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_schematic_menu() -> InlineKeyboardMarkup:
    """Меню схем тракторов"""
    keyboard = [
        [InlineKeyboardButton("🚜 МТЗ-80/82", callback_data="scheme_mtz80")],
        [InlineKeyboardButton("🚜 МТЗ-1221", callback_data="scheme_mtz1221")],
        [InlineKeyboardButton("⚙️ ЯМЗ-236/238", callback_data="scheme_ymz")],
        [InlineKeyboardButton("🚛 КАМАЗ", callback_data="scheme_kamaz")],
        [InlineKeyboardButton("🔧 Т-150", callback_data="scheme_t150")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_order_status_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Статус заказа для продавца"""
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data=f"order_confirm_{order_id}")],
        [InlineKeyboardButton("💳 Оплата получена", callback_data=f"order_paid_{order_id}")],
        [InlineKeyboardButton("📦 Отправлен", callback_data=f"order_shipped_{order_id}")],
        [InlineKeyboardButton("❌ Отменить", callback_data=f"order_cancel_{order_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_seller_menu() -> ReplyKeyboardMarkup:
    """Меню продавца"""
    keyboard = [
        [KeyboardButton("➕ Добавить товар"), KeyboardButton("📦 Управление складом")],
        [KeyboardButton("📋 Заказы"), KeyboardButton("📊 Статистика")],
        [KeyboardButton("📥 Выгрузить отчет"), KeyboardButton("🔙 Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_admin_menu() -> ReplyKeyboardMarkup:
    """Меню администратора"""
    keyboard = [
        [KeyboardButton("👥 Пользователи"), KeyboardButton("📊 Статистика")],
        [KeyboardButton("🏷️ Категории"), KeyboardButton("⚙️ Настройки")],
        [KeyboardButton("📥 Экспорт данных"), KeyboardButton("🔙 Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_yes_no_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура Да/Нет"""
    keyboard = [
        [InlineKeyboardButton("✅ Да", callback_data="yes"),
         InlineKeyboardButton("❌ Нет", callback_data="no")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_quantity_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Выбор количества"""
    keyboard = [
        [InlineKeyboardButton("➖", callback_data=f"qty_dec_{product_id}"),
         InlineKeyboardButton("1", callback_data="qty_display"),
         InlineKeyboardButton("➕", callback_data=f"qty_inc_{product_id}")],
        [InlineKeyboardButton("✅ Добавить", callback_data=f"qty_add_{product_id}"),
         InlineKeyboardButton("❌ Отмена", callback_data="qty_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_profile_keyboard() -> InlineKeyboardMarkup:
    """Профиль пользователя"""
    keyboard = [
        [InlineKeyboardButton("📞 Изменить телефон", callback_data="change_phone")],
        [InlineKeyboardButton("📋 Мои заказы", callback_data="my_orders")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)
