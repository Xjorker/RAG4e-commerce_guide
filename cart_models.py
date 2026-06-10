"""
Task 1: 购物车数据模型与数据库Schema
TDD: 先定义模型，让测试和实现都基于此契约
"""
import sqlite3
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ============ Pydantic 数据模型（API层） ============

class CartItemAdd(BaseModel):
    """加购请求"""
    user_id: str = "default_user"
    product_id: str
    sku_id: Optional[str] = None
    title: str
    brand: Optional[str] = None
    image_path: Optional[str] = None
    unit_price: float = Field(gt=0)
    quantity: int = Field(ge=1, le=99, default=1)


class CartItemUpdate(BaseModel):
    """修改数量请求"""
    quantity: int = Field(ge=1, le=99)


class CartItem(BaseModel):
    """购物车商品项（响应）"""
    id: int
    user_id: str
    product_id: str
    sku_id: Optional[str] = None
    title: str
    brand: Optional[str] = None
    image_path: Optional[str] = None
    unit_price: float
    quantity: int
    subtotal: float  # unit_price * quantity
    added_at: str


class CartSummary(BaseModel):
    """购物车汇总"""
    items: List[CartItem]
    total_count: int  # 总件数
    total_amount: float  # 总价


# ============ 数据库初始化 ============

CART_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS cart_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'default_user',
    product_id TEXT NOT NULL,
    sku_id TEXT,
    title TEXT NOT NULL,
    brand TEXT,
    image_path TEXT,
    unit_price REAL NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cart_user ON cart_items(user_id);
CREATE INDEX IF NOT EXISTS idx_cart_user_product ON cart_items(user_id, product_id, sku_id);
"""


def init_cart_table(db_path: str = "d:/RAG导购/ecommerce.db"):
    """初始化购物车表（幂等操作）"""
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(CART_TABLE_DDL)
        conn.commit()
    finally:
        conn.close()
    print(f"[OK] cart_items initialized: {db_path}")


if __name__ == "__main__":
    init_cart_table()
