"""
Task 2-4: 购物车CRUD服务层
- add_to_cart: 加购（已存在则数量+1）
- get_cart: 查询购物车
- update_quantity: 修改数量
- remove_from_cart: 删除某项
- clear_cart: 清空购物车
"""
import sqlite3
from typing import List
from cart_models import CartItem, CartItemAdd, CartItemUpdate


class CartService:
    def __init__(self, db_path: str = "d:/RAG导购/ecommerce.db"):
        self.db_path = db_path

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def add_to_cart(self, item: CartItemAdd) -> CartItem:
        """加购：若同user+product+sku已存在则quantity累加"""
        conn = self._connect()
        try:
            cur = conn.cursor()
            # 检查是否已存在
            cur.execute(
                "SELECT id, quantity FROM cart_items WHERE user_id=? AND product_id=? AND IFNULL(sku_id,'')=IFNULL(?, '')",
                (item.user_id, item.product_id, item.sku_id)
            )
            existing = cur.fetchone()
            if existing:
                new_qty = min(existing[1] + item.quantity, 99)
                cur.execute("UPDATE cart_items SET quantity=? WHERE id=?", (new_qty, existing[0]))
                item_id = existing[0]
            else:
                cur.execute(
                    """INSERT INTO cart_items
                    (user_id, product_id, sku_id, title, brand, image_path, unit_price, quantity)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (item.user_id, item.product_id, item.sku_id, item.title,
                     item.brand, item.image_path, item.unit_price, item.quantity)
                )
                item_id = cur.lastrowid
            conn.commit()
            return self.get_cart_item(item_id)
        finally:
            conn.close()

    def get_cart_item(self, item_id: int) -> CartItem:
        """获取单个购物车项"""
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM cart_items WHERE id=?", (item_id,))
            row = cur.fetchone()
            return self._row_to_item(row) if row else None
        finally:
            conn.close()

    def get_cart(self, user_id: str) -> List[CartItem]:
        """查询用户购物车"""
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM cart_items WHERE user_id=? ORDER BY added_at DESC",
                (user_id,)
            )
            return [self._row_to_item(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def update_quantity(self, item_id: int, update: CartItemUpdate) -> CartItem:
        """修改数量"""
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE cart_items SET quantity=? WHERE id=?", (update.quantity, item_id))
            conn.commit()
            return self.get_cart_item(item_id)
        finally:
            conn.close()

    def remove_from_cart(self, item_id: int) -> bool:
        """删除某项"""
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM cart_items WHERE id=?", (item_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def clear_cart(self, user_id: str) -> int:
        """清空用户购物车，返回删除条数"""
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM cart_items WHERE user_id=?", (user_id,))
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()

    def _row_to_item(self, row) -> CartItem:
        if not row:
            return None
        return CartItem(
            id=row[0],
            user_id=row[1],
            product_id=row[2],
            sku_id=row[3],
            title=row[4],
            brand=row[5],
            image_path=row[6],
            unit_price=row[7],
            quantity=row[8],
            subtotal=round(row[7] * row[8], 2),
            added_at=row[9]
        )
