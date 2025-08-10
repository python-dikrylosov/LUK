import os
import logging
import json
import pandas as pd
import qrcode
from io import BytesIO
from datetime import datetime
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException
import schedule  # Добавлено для планировщика
import threading  # Добавлено для работы с потоками
import time  # Добавлено для задержек

# === ИСПРАВЛЕНИЕ ПРОБЛЕМЫ С NUMPY ===
# Решение проблемы с AttributeError: module 'numpy' has no attribute 'float'
try:
    import numpy as np

    if not hasattr(np, 'float'):
        np.float = float
    if not hasattr(np, 'int'):
        np.int = int
except ImportError:
    pass

# Настройка логирования с правильной кодировкой
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

# === КОНФИГУРАЦИЯ БОТА ===
# ВНИМАНИЕ! Замените эти значения на ваши
TOKEN = '6370786666:AAFC05QMUzxs2cbChr4pQvE7u_vC3NjuJ2E'  # Замените на токен вашего бота
ADMIN_CHAT_ID = 810299040  # Ваш ID в Telegram
GROUP_CHAT_ID = -1001962220435  # ID вашей группы (например, @MTZ_UFA)
PAGE_SIZE = 10  # Количество товаров на странице
IMAGE_DIR = "product_images/"  # Папка с изображениями
USERS_FILE = "users.json"  # Файл для хранения профилей
CARTS_FILE = "carts.json"  # Файл для хранения корзин
EXCEL_FILE = "БГАУ1.xlsx"  # Файл с базой данных товаров

# Создание папки для изображений, если её нет
os.makedirs(IMAGE_DIR, exist_ok=True)

# Инициализация бота
bot = telebot.TeleBot(TOKEN)

# === ЗАГРУЗКА ДАННЫХ ИЗ EXCEL ===
try:
    # Проверяем существование файла
    if not os.path.exists(EXCEL_FILE):
        logger.error(f"❌ Файл базы данных {EXCEL_FILE} не найден!")
        # Создаем примерный файл для тестирования
        example_data = {
            'Наименование': ['Сальник коленвала', 'Подшипник ступицы', 'Фильтр масляный'],
            'Каталожный номер': ['12345', '67890', '11223'],
            'Стоимость': [500, 1200, 300],
            'Наличие': [10, 0, 5],
            'Фото': ['s1.jpg', 'p1.jpg', 'f1.jpg']
        }
        example_df = pd.DataFrame(example_data)
        example_df.to_excel(EXCEL_FILE, index=False)
        logger.info(f"✅ Создан примерный файл базы данных {EXCEL_FILE}")

        # Создаем примерные изображения
        for img in example_data['Фото']:
            img_path = os.path.join(IMAGE_DIR, img)
            if not os.path.exists(img_path):
                qr = qrcode.make(img)
                qr.save(img_path)
                logger.info(f"✅ Создано примерное изображение {img_path}")

    # Загружаем данные
    data = pd.read_excel(EXCEL_FILE)

    # Проверяем наличие необходимых столбцов
    required_columns = ['Наименование', 'Каталожный номер', 'Стоимость', 'Наличие']
    for col in required_columns:
        if col not in data.columns:
            logger.error(f"❌ В файле базы данных отсутствует обязательный столбец: {col}")
            raise ValueError(f"Отсутствует столбец: {col}")

    # Очищаем и преобразуем данные
    data.columns = [col.strip() for col in data.columns]
    data['Наименование'] = data['Наименование'].astype(str).str.strip()

    # Обработка стоимости с разными форматами
    data['Стоимость'] = data['Стоимость'].astype(str).str.replace(',', '.').str.replace('[^0-9.]', '', regex=True)
    data['Стоимость'] = pd.to_numeric(data['Стоимость'], errors='coerce').fillna(0).astype(float)

    # Обработка фото
    if 'Фото' in data.columns:
        data['Фото'] = data['Фото'].apply(lambda x: str(x).strip() if pd.notna(x) else '')
    else:
        data['Фото'] = ''
        logger.warning("⚠️ В файле базы данных отсутствует столбец 'Фото'")

    logger.info(f"✅ Данные успешно загружены: {len(data)} товаров")
except Exception as e:
    logger.error(f"❌ Критическая ошибка загрузки данных: {str(e)}")
    # Создаем минимальную тестовую базу для продолжения работы
    test_data = {
        'Наименование': ['Товар 1', 'Товар 2', 'Товар 3'],
        'Каталожный номер': ['TEST001', 'TEST002', 'TEST003'],
        'Стоимость': [100, 200, 300],
        'Наличие': [5, 0, 10],
        'Фото': ['test1.jpg', 'test2.jpg', 'test3.jpg']
    }
    data = pd.DataFrame(test_data)
    logger.info("✅ Создана тестовая база данных для продолжения работы")


# === РАБОТА С ФАЙЛАМИ ===
def load_data(file):
    """Загружает данные из JSON файла"""
    if os.path.exists(file):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки {file}: {str(e)}")
            # Создаем резервную копию поврежденного файла
            backup_name = f"{file}.backup.{int(datetime.now().timestamp())}"
            os.rename(file, backup_name)
            logger.info(f"✅ Создана резервная копия: {backup_name}")
    return {}


def save_data(file, data):
    """Безопасно сохраняет данные в JSON файл"""
    try:
        # Сохраняем во временный файл
        temp_file = file + ".tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Заменяем основной файл
        if os.path.exists(file):
            os.replace(file, file + ".old")
        os.replace(temp_file, file)

        # Удаляем старый файл, если он существует
        if os.path.exists(file + ".old"):
            os.remove(file + ".old")

        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения {file}: {str(e)}")
        return False


# Загружаем данные пользователей и корзин
user_profiles = load_data(USERS_FILE)
user_carts = load_data(CARTS_FILE)


# === ИНИЦИАЛИЗАЦИЯ ПОЛЬЗОВАТЕЛЯ ===
def init_user(user_id):
    """Инициализирует профиль пользователя при первом обращении"""
    user_id = str(user_id)
    if user_id not in user_profiles:
        user_profiles[user_id] = {
            "phone": None,
            "orders": [],
            "joined": datetime.now().strftime("%d.%m.%Y %H:%M")
        }
        save_data(USERS_FILE, user_profiles)

    # Убедимся, что корзина инициализирована как список
    if user_id not in user_carts or not isinstance(user_carts[user_id], list):
        user_carts[user_id] = []
        save_data(CARTS_FILE, user_carts)


# Проверка вступления в группу
def user_in_group(user_id):
    """Проверяет, состоит ли пользователь в группе магазина"""
    try:
        if GROUP_CHAT_ID == -1001234567890:  # Значение по умолчанию из примера
            logger.warning("⚠️ Не настроен GROUP_CHAT_ID. Проверка группы отключена.")
            return True

        member = bot.get_chat_member(GROUP_CHAT_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"❌ Ошибка проверки членства в группе: {str(e)}")
        return True  # Разрешаем доступ при ошибках проверки


# === ЕЖЕДНЕВНЫЙ ОТЧЕТ ===
def send_daily_report():
    """Формирует и отправляет ежедневный отчет в группу"""
    try:
        # Собираем статистику
        total_users = len(user_profiles)
        total_orders = 0
        today_orders = 0
        total_revenue = 0
        
        # Подсчитываем заказы и выручку
        today = datetime.now().strftime("%d.%m.%Y")
        for profile in user_profiles.values():
            for order in profile.get('orders', []):
                total_orders += 1
                if 'total' in order:
                    total_revenue += order['total']
                
                # Проверяем, является ли заказ сегодняшним
                if today in order['date']:
                    today_orders += 1
        
        # Формируем сообщение отчета
        report = (f"📊 ЕЖЕДНЕВНЫЙ ОТЧЕТ МАГАЗИНА\n"
                  f"📅 Дата: {datetime.now().strftime('%d.%m.%Y')}\n\n"
                  f"👥 Всего пользователей: {total_users}\n"
                  f"🛒 Всего заказов: {total_orders}\n"
                  f"🆕 Заказов сегодня: {today_orders}\n"
                  f"💰 Общая выручка: {total_revenue:.0f} ₽\n\n"
                  f"Работаем для вас 24/7! 🚜")
        
        # Отправляем отчет в группу
        bot.send_message(GROUP_CHAT_ID, report)
        logger.info("✅ Ежедневный отчет успешно отправлен в группу")
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке ежедневного отчета: {str(e)}")

# Функция для запуска планировщика в фоновом потоке
def run_scheduler():
    """Запускает планировщик задач в фоновом режиме"""
    # Настраиваем отправку отчета каждый день в 9:00
    schedule.every().day.at("09:00").do(send_daily_report)
    
    # Отправляем отчет сразу при запуске бота
    send_daily_report()
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Проверяем каждую минуту


# === ОСНОВНЫЕ КОМАНДЫ ===
@bot.message_handler(commands=['start'])
def start(message):
    """Обработчик команды /start"""
    user_id = str(message.from_user.id)
    init_user(user_id)

    # Проверяем членство в группе
    if not user_in_group(user_id):
        bot.send_message(user_id,
                         "🔒 Для использования бота нужно вступить в нашу группу:\n"
                         "👉 https://t.me/MTZ_UFA  \n"
                         "После вступления напишите /start")
        return

    # Если номер телефона не указан, запрашиваем его
    if not user_profiles[user_id]["phone"]:
        bot.send_message(user_id, "📞 Введите ваш номер телефона:")
        bot.register_next_step_handler(message, process_phone)
    else:
        show_main_menu(message)


def process_phone(message):
    """Обработчик ввода номера телефона"""
    user_id = str(message.from_user.id)
    phone = message.text.strip()

    # Простая валидация номера
    if not phone.startswith(('7', '8', '+7')) or len(phone) < 10:
        bot.send_message(message.chat.id, "❌ Некорректный формат номера. Пример: +79123456789")
        bot.register_next_step_handler(message, process_phone)
        return

    user_profiles[user_id]["phone"] = phone
    save_data(USERS_FILE, user_profiles)
    show_main_menu(message)


def show_main_menu(message):
    """Отображает главное меню бота"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🛍 Каталог", "🛒 Корзина", "👤 Профиль", "🔍 Поиск")
    bot.send_message(
        message.chat.id,
        "Добро пожаловать в магазин запчастей!\n"
        "У нас есть всё для МТЗ, ЯМЗ, КАМАЗ, Т-150 и др.\n\n"
        "Выберите действие:",
        reply_markup=markup
    )


# === РАБОТА С КАТАЛОГОМ ===
def show_page(chat_id, page=0):
    """Отображает страницу каталога товаров"""
    total_pages = (len(data) + PAGE_SIZE - 1) // PAGE_SIZE
    if page < 0:
        page = 0
    elif page >= total_pages:
        page = total_pages - 1 if total_pages > 0 else 0

    start_idx = page * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, len(data))

    if len(data) == 0:
        bot.send_message(chat_id, "❌ База данных пуста. Обратитесь к администратору.")
        return

    markup = types.InlineKeyboardMarkup()
    for i in range(start_idx, end_idx):
        item = data.iloc[i]
        btn_text = f"{item['Наименование']} - {item['Стоимость']:.0f} ₽"
        if len(btn_text) > 64:
            btn_text = btn_text[:61] + "..."
        markup.add(types.InlineKeyboardButton(
            btn_text,
            callback_data=f"item_{i}"
        ))

    # Навигация по страницам
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{page - 1}"))
    if end_idx < len(data):
        nav_buttons.append(types.InlineKeyboardButton("Вперед ➡️", callback_data=f"page_{page + 1}"))

    if nav_buttons:
        markup.row(*nav_buttons)

    status = f"Страница {page + 1}/{total_pages} | Товаров: {len(data)}"
    bot.send_message(chat_id, status, reply_markup=markup)


# Детали товара
@bot.callback_query_handler(func=lambda c: c.data.startswith("item_"))
def show_item(call):
    """Показывает детали выбранного товара"""
    try:
        item_idx = int(call.data.split("_")[1])
        if item_idx < 0 or item_idx >= len(data):
            bot.answer_callback_query(call.id, "❌ Товар не найден")
            return

        item = data.iloc[item_idx]

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Добавить в корзину", callback_data=f"add_{item_idx}"))

        text = (f"🛒 <b>{item['Наименование']}</b>\n\n"
                f"💰 Цена: {item['Стоимость']:.0f} ₽\n"
                f"📦 Наличие: {'✅' if item['Наличие'] > 0 else '⏳ Под заказ'}")

        # Добавляем каталожный номер, если он есть
        if 'Каталожный номер' in item and pd.notna(item['Каталожный номер']):
            text += f"\n📌 Номер: {item['Каталожный номер']}"

        # Пытаемся отправить фото
        if 'Фото' in item and pd.notna(item['Фото']):
            image_path = os.path.join(IMAGE_DIR, str(item['Фото']))
            if os.path.exists(image_path):
                try:
                    with open(image_path, 'rb') as photo:
                        bot.send_photo(call.message.chat.id, photo, caption=text, reply_markup=markup,
                                       parse_mode='HTML')
                    return
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки фото {image_path}: {str(e)}")

        # Если фото нет или ошибка, отправляем текст
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='HTML')
    except Exception as e:
        logger.error(f"❌ Ошибка при отображении товара: {str(e)}")
        bot.answer_callback_query(call.id, "❌ Ошибка при отображении товара")


# Обработчик навигации по страницам
@bot.callback_query_handler(func=lambda c: c.data.startswith("page_"))
def handle_page(call):
    """Обработчик навигации по страницам каталога"""
    try:
        page = int(call.data.split("_")[1])
        show_page(call.message.chat.id, page)
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"❌ Ошибка при переходе на страницу: {str(e)}")
        bot.answer_callback_query(call.id, "❌ Ошибка при переходе на страницу")


# === ПОИСК ТОВАРОВ ===
@bot.message_handler(func=lambda m: m.text == "🔍 Поиск")
def search_start(message):
    """Запускает процесс поиска товаров"""
    bot.send_message(message.chat.id, "Введите название или каталожный номер товара:")
    bot.register_next_step_handler(message, process_search)


def process_search(message):
    """Обрабатывает поисковый запрос"""
    query = message.text.strip().lower()
    if not query:
        bot.send_message(message.chat.id, "❌ Запрос не может быть пустым")
        return

    # Поиск по названию и каталожному номеру
    results = data[
        data['Наименование'].str.lower().str.contains(query, na=False) |
        data['Каталожный номер'].astype(str).str.lower().str.contains(query, na=False)
        ]

    if results.empty:
        # Попробуем убрать пробелы и дефисы
        cleaned_query = query.replace(' ', '').replace('-', '')
        results = data[
            data['Каталожный номер'].astype(str).str.lower().str.replace(' ', '').str.replace('-', '').str.contains(
                cleaned_query, na=False)
        ]

        if results.empty:
            bot.send_message(message.chat.id, "❌ Ничего не найдено. Попробуйте другой запрос.")
            return

    # Отправляем результаты поиска
    found = 0
    for _, item in results.head(10).iterrows():
        item_idx = item.name
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Добавить в корзину", callback_data=f"add_{item_idx}"))

        text = (f"🔍 <b>{item['Наименование']}</b>\n"
                f"📌 {item.get('Каталожный номер', 'Нет номера')}\n"
                f"💰 {item['Стоимость']:.0f} ₽\n"
                f"📦 {'✅ В наличии' if item['Наличие'] > 0 else '⏳ Под заказ'}")

        # Пытаемся отправить фото
        if 'Фото' in item and pd.notna(item['Фото']):
            image_path = os.path.join(IMAGE_DIR, str(item['Фото']))
            if os.path.exists(image_path):
                try:
                    with open(image_path, 'rb') as photo:
                        bot.send_photo(message.chat.id, photo, caption=text, reply_markup=markup, parse_mode='HTML')
                        found += 1
                        continue
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки фото: {str(e)}")

        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='HTML')
        found += 1

    if found == 0:
        bot.send_message(message.chat.id, "❌ Ничего не найдено. Попробуйте другой запрос.")


# === РАБОТА С КОРЗИНОЙ ===
@bot.callback_query_handler(func=lambda c: c.data.startswith("add_"))
def add_to_cart(call):
    """Добавляет товар в корзину"""
    try:
        user_id = str(call.from_user.id)
        init_user(user_id)

        item_idx = int(call.data.split("_")[1])
        if item_idx < 0 or item_idx >= len(data):
            bot.answer_callback_query(call.id, "❌ Товар не найден")
            return

        item = data.iloc[item_idx]

        if item['Наличие'] <= 0:
            bot.answer_callback_query(call.id, "🚫 Товар отсутствует!")
            return

        # Убедимся, что корзина инициализирована как список
        if user_id not in user_carts or not isinstance(user_carts[user_id], list):
            user_carts[user_id] = []

        user_carts[user_id].append({
            "name": item['Наименование'],
            "cost": float(item['Стоимость']),
            "number": item.get('Каталожный номер', ''),
            "image": item.get('Фото', '')
        })

        save_data(CARTS_FILE, user_carts)

        # Отправляем уведомление
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🛒 Перейти в корзину", callback_data="view_cart"))
        markup.add(types.InlineKeyboardButton("◀️ Назад в каталог", callback_data="back_to_catalog"))

        bot.answer_callback_query(call.id, "✅ Товар добавлен в корзину!")
        bot.send_message(
            call.message.chat.id,
            f"Товар '{item['Наименование']}' добавлен в корзину.\n"
            f"Продолжайте покупки или перейдите в корзину для оформления заказа.",
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"❌ Ошибка при добавлении в корзину: {str(e)}")
        bot.answer_callback_query(call.id, "❌ Ошибка при добавлении в корзину")


def show_cart(message):
    """Отображает содержимое корзины"""
    user_id = str(message.from_user.id)
    init_user(user_id)

    cart = user_carts.get(user_id, [])
    if not cart:
        bot.send_message(message.chat.id, "🛒 Ваша корзина пуста 😕", reply_markup=get_main_menu_markup())
        return

    total = sum(item['cost'] for item in cart)
    text = "🛒 <b>Ваша корзина:</b>\n\n"

    for i, item in enumerate(cart):
        text += f"{i + 1}. {item['name']} — {item['cost']:.0f} ₽\n"

    text += f"\n<b>Итого: {total:.0f} ₽</b>"

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout"))
    markup.add(types.InlineKeyboardButton("🗑 Очистить корзину", callback_data="clear_cart"))
    markup.add(types.InlineKeyboardButton("◀️ Назад в каталог", callback_data="back_to_catalog"))

    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='HTML')


@bot.message_handler(func=lambda m: m.text == "🛒 Корзина")
def show_cart_handler(message):
    """Обработчик команды открытия корзины"""
    show_cart(message)


@bot.callback_query_handler(func=lambda c: c.data == "view_cart")
def view_cart_handler(call):
    """Обработчик просмотра корзины через кнопку"""
    show_cart(call.message)


@bot.callback_query_handler(func=lambda c: c.data == "clear_cart")
def clear_cart(call):
    """Очищает корзину пользователя"""
    user_id = str(call.from_user.id)
    user_carts[user_id] = []
    save_data(CARTS_FILE, user_carts)
    bot.answer_callback_query(call.id, "✅ Корзина очищена")
    show_cart(call.message)


@bot.callback_query_handler(func=lambda c: c.data == "back_to_catalog")
def back_to_catalog(call):
    """Возвращает пользователя к каталогу товаров"""
    show_page(call.message.chat.id)


# === ОФОРМЛЕНИЕ ЗАКАЗА ===
@bot.callback_query_handler(func=lambda c: c.data == "checkout")
def checkout(call):
    """Оформляет заказ из корзины"""
    user_id = str(call.from_user.id)
    cart = user_carts.get(user_id, [])

    if not cart:
        bot.answer_callback_query(call.id, "🛒 Корзина пуста!")
        return

    total = sum(item['cost'] for item in cart)
    order_time = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Формирование уведомления для пользователя
    user_message = (f"✅ <b>Заказ оформлен!</b>\n\n"
                    f"📱 Телефон: {user_profiles[user_id].get('phone', 'Не указан')}\n"
                    f"📅 {order_time}\n\n"
                    f"<b>Состав заказа:</b>\n")

    for item in cart:
        user_message += f"• {item['name']} — {item['cost']:.0f} ₽\n"

    user_message += f"\n<b>Итого: {total:.0f} ₽</b>\n\n"
    user_message += ("Ожидайте звонка для уточнения деталей заказа.\n"
                     "Спасибо за покупку!")

    # Отправляем подтверждение пользователю
    bot.send_message(call.message.chat.id, user_message, parse_mode='HTML')

    # Формирование уведомления для админа
    admin_message = (f"🔔 <b>НОВЫЙ ЗАКАЗ</b>\n"
                     f"Пользователь: @{call.from_user.username or 'Аноним'}\n"
                     f"Телефон: {user_profiles[user_id].get('phone', 'Не указан')}\n"
                     f"Дата: {order_time}\n\n"
                     f"<b>Состав заказа:</b>\n")

    for item in cart:
        admin_message += f"• {item['name']} — {item['cost']:.0f} ₽\n"

    admin_message += f"\n<b>Итого: {total:.0f} ₽</b>"

    # Сохранение заказа
    if user_id not in user_profiles:
        user_profiles[user_id] = {"phone": None, "orders": []}

    user_profiles[user_id]["orders"].append({
        "date": order_time,
        "items": cart.copy(),
        "total": total
    })

    # Очищаем корзину
    user_carts[user_id] = []

    # Сохраняем данные
    save_data(USERS_FILE, user_profiles)
    save_data(CARTS_FILE, user_carts)

    # Отправляем уведомление админу
    try:
        if ADMIN_CHAT_ID != 123456789:  # Не значение по умолчанию
            bot.send_message(ADMIN_CHAT_ID, admin_message, parse_mode='HTML')
        else:
            logger.warning("⚠️ Не настроен ADMIN_CHAT_ID. Уведомление админу не отправлено.")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомления админу: {str(e)}")


# === ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ ===
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def show_profile(message):
    """Показывает профиль пользователя и историю заказов"""
    user_id = str(message.from_user.id)
    init_user(user_id)
    profile = user_profiles.get(user_id, {})

    text = (f"👤 <b>Ваш профиль</b>\n\n"
            f"📞 Телефон: {profile.get('phone', 'Не указан')}\n"
            f"🛒 Заказов: {len(profile.get('orders', []))}\n\n")

    orders = profile.get("orders", [])
    if not orders:
        text += "📦 У вас пока нет заказов"
    else:
        text += "📦 <b>История заказов:</b>\n"
        for order in orders[-5:]:  # Показываем последние 5 заказов
            text += f"\n<b>Дата:</b> {order['date']}\n"
            text += f"<b>Итого:</b> {order['total']:.0f} ₽\n"
            text += f"<b>Товаров:</b> {len(order['items'])}"

    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=get_main_menu_markup())


def get_main_menu_markup():
    """Возвращает клавиатуру главного меню"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🛍 Каталог", "🛒 Корзина", "👤 Профиль", "🔍 Поиск")
    return markup


# === ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ ===
@bot.message_handler(commands=['help'])
def help_command(message):
    """Показывает справочную информацию о боте"""
    help_text = (
        "ℹ️ <b>Справка по боту</b>\n\n"
        "🛒 <b>Корзина</b>\n"
        "• Добавление: нажмите 'Добавить в корзину' у товара\n"
        "• Просмотр: нажмите 'Корзина' в меню\n"
        "• Управление: очистка корзины и оформление заказа\n\n"
        "🔍 <b>Поиск</b>\n"
        "• Нажмите 'Поиск' и введите название или каталожный номер\n"
        "• Выберите нужный товар из результатов\n\n"
        "💡 <b>Советы</b>\n"
        "• Используйте каталожные номера для точного поиска\n"
        "• После оформления заказа ожидайте звонка для уточнения деталей"
    )
    bot.send_message(message.chat.id, help_text, parse_mode='HTML', reply_markup=get_main_menu_markup())


# === ОБРАБОТЧИКИ СОБЫТИЙ ===
@bot.message_handler(func=lambda m: m.text == "🛍 Каталог")
def catalog(message):
    """Обработчик команды открытия каталога"""
    show_page(message.chat.id)


@bot.message_handler(func=lambda m: m.text == "🛒 Корзина")
def show_cart_handler(message):
    """Обработчик команды открытия корзины"""
    show_cart(message)


@bot.message_handler(func=lambda m: m.text == "🔍 Поиск")
def search_handler(message):
    """Обработчик команды поиска"""
    search_start(message)


@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile_handler(message):
    """Обработчик команды профиля"""
    show_profile(message)


# Обработка неизвестных команд
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    """Обработка всех остальных сообщений"""
    if message.text.startswith('/'):
        bot.send_message(message.chat.id, "❌ Неизвестная команда. Используйте меню ниже.",
                         reply_markup=get_main_menu_markup())
    else:
        process_search(message)


# === ЗАПУСК БОТА ===
if __name__ == "__main__":
    logger.info("🤖 Бот запущен и готов к работе!")
    logger.info("========================================")
    logger.info(f"ADMIN_CHAT_ID: {ADMIN_CHAT_ID}")
    logger.info(f"GROUP_CHAT_ID: {GROUP_CHAT_ID}")
    logger.info(f"Товаров в базе: {len(data)}")
    logger.info("========================================")

    # Проверка настройки токена
    if TOKEN == 'ВАШ_ТОКЕН_ОТ_BOTFATHER':
        logger.warning("⚠️ ВНИМАНИЕ! Токен бота не настроен. Замените 'ВАШ_ТОКЕН_ОТ_BOTFATHER' на реальный токен.")

    # Запускаем планировщик ежедневных отчетов в фоновом потоке
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("✅ Запущен планировщик ежедневных отчетов")
    
    # Запуск бота с обработкой ошибок
    try:
        bot.polling(none_stop=True, interval=1, timeout=60)
    except Exception as e:
        logger.critical(f"❌ Критическая ошибка при запуске бота: {str(e)}")
        logger.info("Попытка перезапуска через 10 секунд...")
        import time

        time.sleep(10)
        try:
            bot.polling(none_stop=True, interval=1, timeout=60)
        except:
            logger.critical("❌ Не удалось перезапустить бота. Обратитесь к разработчику.")
