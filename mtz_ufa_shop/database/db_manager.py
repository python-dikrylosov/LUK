"""
MTZ_UFA_SHOP - Менеджер базы данных
"""
import asyncio
from typing import Optional, List
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, func
from datetime import datetime

from .models import Base, User, Product, Order, OrderItem, StockMovement, UserRole, OrderStatus


class DatabaseManager:
    """Менеджер работы с базой данных"""
    
    def __init__(self, database_url: str = "sqlite+aiosqlite:///data/shop.db"):
        self.database_url = database_url
        self.engine = None
        self.session_maker = None
    
    async def init_db(self):
        """Инициализация базы данных"""
        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            future=True
        )
        self.session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Создание таблиц
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def get_session(self) -> AsyncSession:
        """Получение сессии"""
        if not self.session_maker:
            await self.init_db()
        return self.session_maker()
    
    # ========== Пользователи ==========
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получить пользователя по Telegram ID"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
    
    async def create_user(
        self,
        telegram_id: int,
        full_name: str,
        username: Optional[str] = None,
        phone: Optional[str] = None,
        role: UserRole = UserRole.BUYER
    ) -> User:
        """Создать нового пользователя"""
        async with await self.get_session() as session:
            user = User(
                telegram_id=telegram_id,
                full_name=full_name,
                username=username,
                phone=phone,
                role=role.value
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
    
    async def update_user_role(self, telegram_id: int, role: UserRole) -> Optional[User]:
        """Обновить роль пользователя"""
        async with await self.get_session() as session:
            user = await self.get_user_by_telegram_id(telegram_id)
            if user:
                user.role = role.value
                await session.commit()
                await session.refresh(user)
            return user
    
    async def update_user_phone(self, telegram_id: int, phone: str) -> Optional[User]:
        """Обновить телефон пользователя"""
        async with await self.get_session() as session:
            user = await self.get_user_by_telegram_id(telegram_id)
            if user:
                user.phone = phone
                await session.commit()
                await session.refresh(user)
            return user
    
    # ========== Товары ==========
    
    async def get_product_by_article(self, article: str) -> Optional[Product]:
        """Получить товар по артикулу"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(Product).where(Product.article == article)
            )
            return result.scalar_one_or_none()
    
    async def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """Получить товар по ID"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(Product).where(Product.id == product_id)
            )
            return result.scalar_one_or_none()
    
    async def get_all_products(self) -> List[Product]:
        """Получить все товары"""
        async with await self.get_session() as session:
            result = await session.execute(select(Product))
            return list(result.scalars().all())
    
    async def get_products_by_category(self, category: str) -> List[Product]:
        """Получить товары по категории"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(Product).where(Product.category == category)
            )
            return list(result.scalars().all())
    
    async def get_products_by_tractor_model(self, tractor_model: str) -> List[Product]:
        """Получить товары по модели трактора"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(Product).where(Product.tractor_model == tractor_model)
            )
            return list(result.scalars().all())
    
    async def search_products(self, query: str) -> List[Product]:
        """Поиск товаров по названию или артикулу"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(Product).where(
                    (Product.name.ilike(f"%{query}%")) |
                    (Product.article.ilike(f"%{query}%"))
                )
            )
            return list(result.scalars().all())
    
    async def create_product(
        self,
        article: str,
        name: str,
        category: str,
        price: float,
        description: Optional[str] = None,
        tractor_model: Optional[str] = None,
        stock_quantity: int = 0,
        min_stock_level: int = 5,
        image_path: Optional[str] = None
    ) -> Product:
        """Создать новый товар"""
        async with await self.get_session() as session:
            product = Product(
                article=article,
                name=name,
                category=category,
                price=price,
                description=description,
                tractor_model=tractor_model,
                stock_quantity=stock_quantity,
                min_stock_level=min_stock_level,
                image_path=image_path
            )
            session.add(product)
            await session.commit()
            await session.refresh(product)
            return product
    
    async def update_product_stock(self, product_id: int, quantity: int) -> Optional[Product]:
        """Обновить остаток товара"""
        async with await self.get_session() as session:
            product = await self.get_product_by_id(product_id)
            if product:
                product.stock_quantity = quantity
                product.updated_at = datetime.utcnow()
                await session.commit()
                await session.refresh(product)
            return product
    
    async def add_stock(self, product_id: int, quantity: int, user_id: int, comment: str = "") -> bool:
        """Добавить товар на склад"""
        async with await self.get_session() as session:
            product = await self.get_product_by_id(product_id)
            if not product:
                return False
            
            product.stock_quantity += quantity
            movement = StockMovement(
                product_id=product_id,
                quantity=quantity,
                movement_type="purchase",
                user_id=user_id,
                comment=comment
            )
            session.add(movement)
            await session.commit()
            return True
    
    async def remove_stock(self, product_id: int, quantity: int, user_id: int, comment: str = "") -> bool:
        """Списать товар со склада"""
        async with await self.get_session() as session:
            product = await self.get_product_by_id(product_id)
            if not product or product.stock_quantity < quantity:
                return False
            
            product.stock_quantity -= quantity
            movement = StockMovement(
                product_id=product_id,
                quantity=-quantity,
                movement_type="sale",
                user_id=user_id,
                comment=comment
            )
            session.add(movement)
            await session.commit()
            return True
    
    async def get_low_stock_products(self) -> List[Product]:
        """Получить товары с низким остатком"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(Product).where(Product.stock_quantity <= Product.min_stock_level)
            )
            return list(result.scalars().all())
    
    # ========== Заказы ==========
    
    async def create_order(
        self,
        user_id: int,
        delivery_address: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Order:
        """Создать новый заказ"""
        async with await self.get_session() as session:
            order = Order(
                user_id=user_id,
                delivery_address=delivery_address,
                comment=comment
            )
            session.add(order)
            await session.commit()
            await session.refresh(order)
            return order
    
    async def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """Получить заказ по ID"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(Order).where(Order.id == order_id)
            )
            return result.scalar_one_or_none()
    
    async def get_user_orders(self, user_id: int) -> List[Order]:
        """Получить все заказы пользователя"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(Order)
                .where(Order.user_id == user_id)
                .order_by(Order.created_at.desc())
            )
            return list(result.scalars().all())
    
    async def add_order_item(
        self,
        order_id: int,
        product_id: int,
        quantity: int,
        price: float
    ) -> OrderItem:
        """Добавить позицию в заказ"""
        async with await self.get_session() as session:
            item = OrderItem(
                order_id=order_id,
                product_id=product_id,
                quantity=quantity,
                price_at_purchase=price
            )
            session.add(item)
            await session.commit()
            await session.refresh(item)
            return item
    
    async def update_order_status(self, order_id: int, status: OrderStatus) -> Optional[Order]:
        """Обновить статус заказа"""
        async with await self.get_session() as session:
            order = await self.get_order_by_id(order_id)
            if order:
                order.status = status.value
                order.updated_at = datetime.utcnow()
                await session.commit()
                await session.refresh(order)
            return order
    
    async def get_orders_by_status(self, status: OrderStatus) -> List[Order]:
        """Получить заказы по статусу"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(Order).where(Order.status == status.value)
            )
            return list(result.scalars().all())
    
    # ========== Статистика ==========
    
    async def get_total_orders_count(self) -> int:
        """Получить общее количество заказов"""
        async with await self.get_session() as session:
            result = await session.execute(select(func.count(Order.id)))
            return result.scalar()
    
    async def get_total_revenue(self) -> float:
        """Получить общую выручку"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(func.sum(Order.total_amount)).where(
                    Order.status.in_([OrderStatus.DELIVERED.value, OrderStatus.PAID.value])
                )
            )
            return result.scalar() or 0.0
    
    async def get_users_count(self) -> int:
        """Получить количество пользователей"""
        async with await self.get_session() as session:
            result = await session.execute(select(func.count(User.id)))
            return result.scalar()
    
    async def get_products_count(self) -> int:
        """Получить количество товаров"""
        async with await self.get_session() as session:
            result = await session.execute(select(func.count(Product.id)))
            return result.scalar()


# Глобальный экземпляр
db_manager = DatabaseManager()
