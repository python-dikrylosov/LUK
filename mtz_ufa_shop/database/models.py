"""
MTZ_UFA_SHOP - Модели данных для базы данных
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class UserRole(enum.Enum):
    BUYER = "buyer"
    SELLER = "seller"
    ADMIN = "admin"


class OrderStatus(enum.Enum):
    NEW = "new"
    CONFIRMED = "confirmed"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255))
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20))
    role = Column(String(20), default=UserRole.BUYER.value, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    balance = Column(Float, default=0.0)
    
    # Связи
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.full_name} ({self.username})>"


class Product(Base):
    """Модель товара"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    article = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(500), nullable=False)
    description = Column(Text)
    category = Column(String(100), nullable=False)
    tractor_model = Column(String(50))  # MTZ, YMZ, KAMAZ, T150
    price = Column(Float, nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=False)
    min_stock_level = Column(Integer, default=5)
    image_path = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    order_items = relationship("OrderItem", back_populates="product")
    
    def __repr__(self):
        return f"<Product {self.name} ({self.article})>"
    
    def is_low_stock(self):
        """Проверка низкого остатка"""
        return self.stock_quantity <= self.min_stock_level


class Order(Base):
    """Модель заказа"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default=OrderStatus.NEW.value, nullable=False)
    total_amount = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    delivery_address = Column(Text)
    comment = Column(Text)
    
    # Связи
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Order #{self.id} - {self.status}>"
    
    def calculate_total(self):
        """Пересчитать общую сумму заказа"""
        self.total_amount = sum(item.subtotal for item in self.items)
        return self.total_amount


class OrderItem(Base):
    """Модель позиции заказа"""
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    price_at_purchase = Column(Float, nullable=False)
    
    # Связи
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    
    def __repr__(self):
        return f"<OrderItem {self.quantity} x {self.product_id}>"
    
    @property
    def subtotal(self):
        """Сумма по позиции"""
        return self.quantity * self.price_at_purchase


class StockMovement(Base):
    """Модель движения склада"""
    __tablename__ = "stock_movements"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)  # Положительное - приход, отрицательное - расход
    movement_type = Column(String(20), nullable=False)  # purchase, sale, adjustment
    user_id = Column(Integer, ForeignKey("users.id"))
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<StockMovement {self.movement_type}: {self.quantity}>"
