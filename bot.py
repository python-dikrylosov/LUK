#!/usr/bin/env python3
"""
Telegram-бот для магазина запчастей MTZ_UFA
Основной файл запуска бота
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import (
    BOT_TOKEN,
    ADMIN_GROUP_ID,
    PRODUCTS_FILE,
    USERS_FILE,
    CARTS_FILE,
    IMAGES_FOLDER,
    LOG_FILE,
    LOG_LEVEL,
    SEARCH_RESULTS_LIMIT,
    MAX_CART_ITEMS,
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL),
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MTZBot:
    """Класс основного бота"""
    
    def __init__(self):
        self.application = None
        self.products = []
        self.users = {}
        self.carts = {}
        
    def load_data(self):
        """Загрузка данных из файлов"""
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                self.users = json.load(f)
        else:
            self.users = {}
            
        if os.path.exists(CARTS_FILE):
            with open(CARTS_FILE, 'r', encoding='utf-8') as f:
                self.carts = json.load(f)
        else:
            self.carts = {}
            
        logger.info("Данные загружены успешно")
        
    def save_users(self):
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, ensure_ascii=False, indent=2)
            
    def save_carts(self):
        with open(CARTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.carts, f, ensure_ascii=False, indent=2)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = str(user.id)
        
        if user_id not in self.users:
            self.users[user_id] = {
                'id': user_id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'registered_at': datetime.now().isoformat(),
                'orders': []
            }
            self.save_users()
            logger.info(f"Новый пользователь: {user_id}")
        
        keyboard = [
            [InlineKeyboardButton("📦 Каталог", callback_data="catalog")],
            [InlineKeyboardButton("🔍 Поиск", callback_data="search")],
            [InlineKeyboardButton("🛒 Корзина", callback_data="cart")],
            [InlineKeyboardButton("📋 Мои заказы", callback_data="orders")],
            [InlineKeyboardButton("📞 Контакты", callback_data="contacts")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = (
            f"👋 Здравствуйте, {user.first_name}!\n\n"
            "Добро пожаловать в магазин запчастей МТЗ, ЯМЗ, КАМАЗ, Т-150!\n\n"
            "Выберите действие:"
        )
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "catalog":
            await self.show_catalog(update, context)
        elif data == "search":
            await query.edit_message_text("🔍 Введите название или артикул запчасти:")
            context.user_data['waiting_for_search'] = True
        elif data == "cart":
            await self.show_cart(update, context)
        elif data == "orders":
            await self.show_orders(update, context)
        elif data == "contacts":
            await self.show_contacts(update, context)
        elif data.startswith("category_"):
            category = data.replace("category_", "")
            await self.show_category_products(update, context, category)
        elif data.startswith("product_"):
            product_id = data.replace("product_", "")
            await self.show_product(update, context, product_id)
        elif data.startswith("add_to_cart_"):
            product_id = data.replace("add_to_cart_", "")
            await self.add_to_cart(update, context, product_id)
        elif data == "checkout":
            await self.checkout(update, context)
        elif data == "clear_cart":
            await self.clear_cart(update, context)
        elif data == "back_to_menu":
            await self.back_to_menu(update, context)
        elif data == "back_to_catalog":
            await self.show_catalog(update, context)
    
    async def show_catalog(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        categories = set(p.get('category', 'Разное') for p in self.products)
        
        keyboard = []
        for cat in sorted(categories):
            keyboard.append([InlineKeyboardButton(f"📁 {cat}", callback_data=f"category_{cat}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                "📦 Выберите категорию:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "📦 Выберите категорию:",
                reply_markup=reply_markup
            )
    
    async def search_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if context.user_data.get('waiting_for_search'):
            query_text = update.message.text.lower()
            results = [
                p for p in self.products
                if query_text in p.get('name', '').lower() or 
                   query_text in str(p.get('article', '')).lower()
            ][:SEARCH_RESULTS_LIMIT]
            
            if not results:
                await update.message.reply_text("❌ Ничего не найдено.")
            else:
                keyboard = []
                for p in results:
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{p.get('name', 'Б/Н')} - {p.get('price', 0)}₽",
                            callback_data=f"product_{p.get('id', '')}"
                        )
                    ])
                keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"✅ Найдено {len(results)} товаров:\n",
                    reply_markup=reply_markup
                )
            
            context.user_data['waiting_for_search'] = False
    
    async def show_cart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        cart = self.carts.get(user_id, [])
        
        if not cart:
            text = "🛒 Ваша корзина пуста."
            keyboard = [[InlineKeyboardButton("🔙 В каталог", callback_data="back_to_catalog")]]
        else:
            total = sum(item.get('price', 0) * item.get('quantity', 1) for item in cart)
            text = f"🛒 Ваша корзина ({len(cart)} поз.):\n\n"
            for item in cart:
                text += f"• {item.get('name', 'Б/Н')} x{item.get('quantity', 1)} — {item.get('price', 0) * item.get('quantity', 1)}₽\n"
            text += f"\n💰 Итого: {total}₽"
            
            keyboard = [
                [InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout")],
                [InlineKeyboardButton("🗑 Очистить корзину", callback_data="clear_cart")],
                [InlineKeyboardButton("🔙 В каталог", callback_data="back_to_catalog")],
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def add_to_cart(self, update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: str):
        user_id = str(update.effective_user.id)
        product = next((p for p in self.products if str(p.get('id')) == product_id), None)
        
        if not product:
            await update.callback_query.answer("❌ Товар не найден", show_alert=True)
            return
        
        if user_id not in self.carts:
            self.carts[user_id] = []
        
        existing = next((i for i in self.carts[user_id] if str(i.get('id')) == product_id), None)
        if existing:
            existing['quantity'] = existing.get('quantity', 1) + 1
        else:
            self.carts[user_id].append({
                'id': product.get('id'),
                'name': product.get('name'),
                'price': product.get('price'),
                'article': product.get('article'),
                'quantity': 1
            })
        
        if len(self.carts[user_id]) > MAX_CART_ITEMS:
            self.carts[user_id] = self.carts[user_id][:MAX_CART_ITEMS]
        
        self.save_carts()
        
        await update.callback_query.answer(f"✅ Добавлено в корзину", show_alert=False)
        await self.show_cart(update, context)
    
    async def clear_cart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        self.carts[user_id] = []
        self.save_carts()
        
        await update.callback_query.edit_message_text("🗑 Корзина очищена.")
        await self.show_catalog(update, context)
    
    async def checkout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        cart = self.carts.get(user_id, [])
        
        if not cart:
            await update.callback_query.answer("Корзина пуста!", show_alert=True)
            return
        
        total = sum(item.get('price', 0) * item.get('quantity', 1) for item in cart)
        
        order = {
            'order_id': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'user_id': user_id,
            'items': cart,
            'total': total,
            'status': 'new',
            'created_at': datetime.now().isoformat()
        }
        
        if user_id in self.users:
            self.users[user_id].setdefault('orders', []).append(order)
            self.save_users()
        
        if ADMIN_GROUP_ID:
            order_text = f"🆕 Новый заказ #{order['order_id']}\n"
            order_text += f"👤 Пользователь: @{update.effective_user.username}\n"
            order_text += f"💰 Сумма: {total}₽\n\n"
            for item in cart:
                order_text += f"• {item.get('name')} x{item.get('quantity', 1)}\n"
            
            try:
                await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=order_text)
            except Exception as e:
                logger.error(f"Ошибка отправки заказа в админ-группу: {e}")
        
        self.carts[user_id] = []
        self.save_carts()
        
        await update.callback_query.edit_message_text(
            f"✅ Заказ #{order['order_id']} оформлен!\n"
            f"💰 Сумма: {total}₽\n\n"
            f"Менеджер свяжется с вами в ближайшее время."
        )
        
        logger.info(f"Заказ {order['order_id']} оформлен пользователем {user_id}")
    
    async def show_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        orders = self.users.get(user_id, {}).get('orders', [])
        
        if not orders:
            text = "📋 У вас пока нет заказов."
        else:
            text = "📋 Ваши заказы:\n\n"
            for order in orders[-5:]:
                text += f"#{order['order_id']} — {order['total']}₽ ({order['status']})\n"
        
        keyboard = [[InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def show_contacts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "📞 Контакты:\n\n"
            "📍 Адрес: г. Уфа\n"
            "📱 Телефон: +7 (XXX) XXX-XX-XX\n"
            "📧 Email: info@mtz-ufa.ru\n"
            "⏰ Режим работы: Пн-Пт 9:00-18:00"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def back_to_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.start(update, context)
    
    def run(self):
        self.load_data()
        
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.search_handler))
        
        logger.info("Бот запущен...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    bot = MTZBot()
    bot.run()
