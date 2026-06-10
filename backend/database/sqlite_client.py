import sqlite3
import json
import os
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from config import settings

class SQLiteClient:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.SQLITE_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_tables()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_tables(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    product_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    brand TEXT,
                    category TEXT,
                    sub_category TEXT,
                    base_price REAL,
                    image_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS skus (
                    sku_id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL,
                    properties TEXT,
                    price REAL,
                    FOREIGN KEY (product_id) REFERENCES products(product_id_id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rag_fragments (
                    fragment_id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL,
                    content_type TEXT,
                    title TEXT,
                    content TEXT NOT NULL,
                    metadata_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    msg_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 用户表：登录注册
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    nickname TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 购物车表：每个用户每个SKU一条记录，相同user+product+sku累加数量
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cart_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    sku_id TEXT,
                    title TEXT NOT NULL,
                    brand TEXT,
                    image_path TEXT,
                    unit_price REAL NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('CREATE INDEX IF NOT EXISTS idx_rag_fragments_product_id ON rag_fragments(product_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_history_session_id ON chat_history(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cart_items_user_id ON cart_items(user_id)')
    
    def insert_product(self, product_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO products 
                (product_id, title, brand, category, sub_category, base_price, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                product_data.get('product_id'),
                product_data.get('title'),
                product_data.get('brand'),
                product_data.get('category'),
                product_data.get('sub_category'),
                product_data.get('base_price'),
                product_data.get('image_path')
            ))
    
    def insert_sku(self, sku_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO skus (sku_id, product_id, properties, price)
                VALUES (?, ?, ?, ?)
            ''', (
                sku_data.get('sku_id'),
                sku_data.get('product_id'),
                json.dumps(sku_data.get('properties', {})),
                sku_data.get('price')
            ))
    
    def insert_fragment(self, fragment_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO rag_fragments 
                (fragment_id, product_id, content_type, title, content, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                fragment_data.get('fragment_id'),
                fragment_data.get('product_id'),
                fragment_data.get('content_type'),
                fragment_data.get('title'),
                fragment_data.get('content'),
                json.dumps(fragment_data.get('metadata_json', {}))
            ))
    
    def get_fragments_by_product_id(self, product_id: str) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM rag_fragments WHERE product_id = ? LIMIT 1',
                (product_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_fragments(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM rag_fragments')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_all_products(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM products')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM products WHERE product_id = ?', (product_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_skus_by_product_id(self, product_id: str) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM skus WHERE product_id = ?', (product_id,))
            rows = cursor.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d['properties'] = json.loads(d['properties'])
                result.append(d)
            return result
    
    def insert_chat_msg(self, msg_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO chat_history (msg_id, session_id, role, content)
                VALUES (?, ?, ?, ?)
            ''', (
                msg_data.get('msg_id'),
                msg_data.get('session_id'),
                msg_data.get('role'),
                msg_data.get('content')
            ))
    
    def get_chat_history(self, session_id: str, limit: int = 100) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM chat_history WHERE session_id = ? ORDER BY created_at DESC LIMIT ?',
                (session_id, limit)
            )
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]
            return list(reversed(result))

    # ========== 购物车CRUD方法 ==========
    def add_cart_item(self, item_data: Dict[str, Any]) -> int:
        """
        加购：同user+product+sku已存在则数量+1，否则新增
        返回新插入或更新的cart_item_id
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 检查是否已存在
            cursor.execute(
                "SELECT id, quantity FROM cart_items WHERE user_id=? AND product_id=? AND IFNULL(sku_id,'')=IFNULL(?, '')",
                (item_data.get('user_id'), item_data.get('product_id'), item_data.get('sku_id'))
            )
            existing = cursor.fetchone()
            if existing:
                new_qty = min(existing['quantity'] + item_data.get('quantity', 1), 99)
                cursor.execute("UPDATE cart_items SET quantity=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                               (new_qty, existing['id']))
                return existing['id']
            else:
                cursor.execute('''
                    INSERT INTO cart_items
                    (user_id, product_id, sku_id, title, brand, image_path, unit_price, quantity)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    item_data.get('user_id'),
                    item_data.get('product_id'),
                    item_data.get('sku_id'),
                    item_data.get('title'),
                    item_data.get('brand'),
                    item_data.get('image_path'),
                    item_data.get('unit_price'),
                    item_data.get('quantity', 1)
                ))
                return cursor.lastrowid

    def get_cart_items(self, user_id: str) -> List[Dict]:
        """查询某用户购物车所有项"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM cart_items WHERE user_id = ? ORDER BY created_at DESC',
                (user_id,)
            )
            rows = cursor.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d['subtotal'] = round(d.get('unit_price', 0) * d.get('quantity', 0), 2)
                result.append(d)
            return result

    def update_cart_quantity(self, item_id: int, quantity: int) -> bool:
        """修改购物车某项数量"""
        if quantity < 1 or quantity > 99:
            return False
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE cart_items SET quantity=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
                (quantity, item_id)
            )
            return cursor.rowcount > 0

    def remove_cart_item(self, item_id: int) -> bool:
        """从购物车删除某项"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM cart_items WHERE id=?', (item_id,))
            return cursor.rowcount > 0

    def clear_cart(self, user_id: str) -> int:
        """清空某用户购物车，返回删除的行数"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM cart_items WHERE user_id=?', (user_id,))
            return cursor.rowcount

sqlite_client = SQLiteClient()
