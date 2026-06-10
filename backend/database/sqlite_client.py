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
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_rag_fragments_product_id ON rag_fragments(product_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_history_session_id ON chat_history(session_id)')
    
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

sqlite_client = SQLiteClient()
