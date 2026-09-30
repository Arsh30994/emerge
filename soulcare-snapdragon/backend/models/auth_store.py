"""
Local auth for SoulCare Desktop.

Privacy-first: accounts live on-device in a JSON store. No cloud IdP.
Demo users ship for judges; anyone can register locally.
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("soulcare.auth")

DEFAULT_USERS = [
    {"username": "demo", "password": "demo123", "display_name": "Demo User"},
    {"username": "judge", "password": "snapdragon", "display_name": "Hackathon Judge"},
]


class AuthStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(__file__).resolve().parents[2] / "models" / "users.json"
        self.sessions: dict[str, dict[str, Any]] = {}
        self._ensure_store()

    def _hash(self, password: str, salt: str) -> str:
        return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()

    def _ensure_store(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            return
        users = {}
        for u in DEFAULT_USERS:
            salt = secrets.token_hex(8)
            users[u["username"]] = {
                "username": u["username"],
                "display_name": u["display_name"],
                "salt": salt,
                "password_hash": self._hash(u["password"], salt),
                "created_at": time.time(),
            }
        self.path.write_text(json.dumps({"users": users}, indent=2))
        logger.info("Created local auth store at %s", self.path)

    def _load(self) -> dict[str, Any]:
        return json.loads(self.path.read_text())

    def _save(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2))

    def register(self, username: str, password: str, display_name: str | None = None) -> dict[str, Any]:
        username = (username or "").strip().lower()
        if len(username) < 3 or len(password) < 6:
            raise ValueError("Username ≥3 chars and password ≥6 chars required")
        data = self._load()
        if username in data["users"]:
            raise ValueError("Username already exists")
        salt = secrets.token_hex(8)
        data["users"][username] = {
            "username": username,
            "display_name": display_name or username,
            "salt": salt,
            "password_hash": self._hash(password, salt),
            "created_at": time.time(),
        }
        self._save(data)
        return self.login(username, password)

    def login(self, username: str, password: str) -> dict[str, Any]:
        username = (username or "").strip().lower()
        data = self._load()
        user = data["users"].get(username)
        if not user or user["password_hash"] != self._hash(password, user["salt"]):
            raise ValueError("Invalid username or password")
        token = secrets.token_urlsafe(24)
        self.sessions[token] = {
            "username": user["username"],
            "display_name": user["display_name"],
            "issued_at": time.time(),
        }
        return {
            "token": token,
            "user": {
                "username": user["username"],
                "display_name": user["display_name"],
            },
        }

    def logout(self, token: str | None) -> None:
        if token:
            self.sessions.pop(token, None)

    def user_for(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        return self.sessions.get(token)

    def guest(self) -> dict[str, Any]:
        token = secrets.token_urlsafe(24)
        self.sessions[token] = {
            "username": "guest",
            "display_name": "Guest",
            "issued_at": time.time(),
            "guest": True,
        }
        return {
            "token": token,
            "user": {"username": "guest", "display_name": "Guest", "guest": True},
        }
