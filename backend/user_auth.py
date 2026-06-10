"""用户认证模块 - 登录注册Token签发"""
import hashlib
import secrets
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict
from database.sqlite_client import sqlite_client


# Token有效期（天）
TOKEN_EXPIRE_DAYS = 30

# 用户数据文件路径（备份存储）
USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users_auth.json")


def _hash_password(password: str, salt: str) -> str:
    """密码hash"""
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()


def _generate_token() -> str:
    """生成token"""
    return secrets.token_urlsafe(32)


class UserAuthManager:
    """用户认证管理器"""

    def __init__(self):
        self._tokens: Dict[str, dict] = {}  # token -> {user_id, expires_at}
        self._load_tokens()

    def _load_tokens(self):
        """从文件加载token"""
        try:
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._tokens = data.get("tokens", {})
        except Exception:
            self._tokens = {}

    def _save_tokens(self):
        """保存token到文件"""
        try:
            data = {"tokens": self._tokens}
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def register(self, username: str, password: str, nickname: str = None) -> dict:
        """注册用户"""
        username = (username or "").strip()
        if not username or not password:
            return {"ok": False, "error": "用户名和密码不能为空"}
        if len(username) < 2 or len(username) > 32:
            return {"ok": False, "error": "用户名长度需2-32"}
        if len(password) < 6:
            return {"ok": False, "error": "密码至少6位"}

        # 检查是否已存在
        with sqlite_client.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cur.fetchone():
                return {"ok": False, "error": "用户名已被注册"}
            # 插入用户
            salt = secrets.token_hex(8)
            password_hash = _hash_password(password, salt)
            cur.execute(
                "INSERT INTO users (username, password_hash, salt, nickname) VALUES (?, ?, ?, ?)",
                (username, password_hash, salt, nickname or username),
            )
            user_id = cur.lastrowid

        # 自动登录
        return self.login(username, password, _user_id=user_id, _nickname=nickname or username)

    def login(self, username: str, password: str, _user_id: int = None, _nickname: str = None) -> dict:
        """登录"""
        username = (username or "").strip()
        if not username or not password:
            return {"ok": False, "error": "用户名和密码不能为空"}

        if _user_id is None:
            with sqlite_client.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, password_hash, salt, nickname FROM users WHERE username = ?",
                    (username,),
                )
                row = cur.fetchone()
            if not row:
                return {"ok": False, "error": "用户名或密码错误"}
            user_id, password_hash, salt, nickname = row
            if _hash_password(password, salt) != password_hash:
                return {"ok": False, "error": "用户名或密码错误"}
        else:
            user_id = _user_id
            nickname = _nickname

        # 签发token
        token = _generate_token()
        expires_at = (datetime.now() + timedelta(days=TOKEN_EXPIRE_DAYS)).isoformat()
        self._tokens[token] = {
            "user_id": user_id,
            "username": username,
            "nickname": nickname,
            "expires_at": expires_at,
        }
        self._save_tokens()

        return {
            "ok": True,
            "token": token,
            "user_id": user_id,
            "username": username,
            "nickname": nickname,
            "expires_at": expires_at,
        }

    def verify_token(self, token: str) -> Optional[dict]:
        """验证token，返回user信息或None"""
        if not token:
            return None
        info = self._tokens.get(token)
        if not info:
            return None
        # 检查过期
        try:
            expires = datetime.fromisoformat(info["expires_at"])
            if datetime.now() > expires:
                del self._tokens[token]
                self._save_tokens()
                return None
        except Exception:
            return None
        return info

    def logout(self, token: str) -> bool:
        """登出"""
        if token in self._tokens:
            del self._tokens[token]
            self._save_tokens()
            return True
        return False


# 全局实例
_auth_manager = None


def get_auth_manager() -> UserAuthManager:
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = UserAuthManager()
    return _auth_manager
