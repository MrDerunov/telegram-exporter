"""
ProfileManager — управление несколькими Telegram-аккаунтами.

Метаданные профилей (несекретные) и список чатов хранятся в state.json
через ISettingsStore. Сессии (секретные) — через ISecretStore.

Формат state.json (фрагмент с профилями):
{
  "active_phone": "+7999...",
  "profiles": [
    {"phone": "+7999...", "display_name": "Max", "api_id": "123"},
    ...
  ],
  "chats": [...]
}
"""

from __future__ import annotations

import threading
from typing import Optional

from tg_exporter.secrets.secret_store import ISecretStore
from tg_exporter.hosting.settings_store import ISettingsStore
from tg_exporter.hosting.state_model import StateModel, ProfileEntry
from ...utils.logger import logger
from .profile import Profile, _session_key, _normalize_phone


class ProfileManager:
    """
    CRUD над списком профилей + активным профилем.

    Thread-safe: внутренний lock защищает загрузку/сохранение состояния.
    Секреты (session string) всегда идут через ISecretStore.
    Состояние (профили, чаты) — через ISettingsStore → state.json.
    """

    def __init__(self, secrets: ISecretStore, settings: ISettingsStore) -> None:
        self._secrets = secrets
        self._settings = settings
        self._lock = threading.Lock()
        self._profiles: list[Profile] = []
        self._active_phone: Optional[str] = None
        self._load()

    # ---------------------------------------------------------- persistence

    def _load(self) -> None:
        state = self._settings.load()
        self._active_phone = state.active_phone or None
        self._profiles = [
            Profile(phone=p.phone, display_name=p.display_name, api_id=p.api_id)
            for p in state.profiles
        ]

    def _save(self) -> None:
        # Читаем текущее состояние чтобы сохранить chats нетронутыми
        current = self._settings.load()
        state = StateModel(
            active_phone=self._active_phone or "",
            profiles=tuple(
                ProfileEntry(phone=p.phone, display_name=p.display_name, api_id=p.api_id)
                for p in self._profiles
            ),
            chats=current.chats,  # чаты не трогаем
        )
        self._settings.save(state)

    # ---------------------------------------------------------- queries

    def list(self) -> list[Profile]:
        with self._lock:
            return list(self._profiles)

    def active(self) -> Optional[Profile]:
        with self._lock:
            if not self._active_phone:
                return None
            return next((p for p in self._profiles if p.phone == self._active_phone), None)

    def active_phone(self) -> Optional[str]:
        with self._lock:
            return self._active_phone

    def get(self, phone: str) -> Optional[Profile]:
        phone = _normalize_phone(phone)
        with self._lock:
            return next((p for p in self._profiles if p.phone == phone), None)

    def is_empty(self) -> bool:
        with self._lock:
            return not self._profiles

    # ---------------------------------------------------------- mutations

    def add_or_update(
        self,
        phone: str,
        api_id: str,
        session_string: str,
        display_name: str = "",
        set_active: bool = True,
    ) -> Profile:
        """Добавляет новый профиль (или обновляет существующий по phone)."""
        phone = _normalize_phone(phone)
        if not phone:
            raise ValueError("phone required")
        if not api_id:
            raise ValueError("api_id required")
        if session_string:
            self._secrets.set(_session_key(api_id, phone), session_string)
        with self._lock:
            existing = next((p for p in self._profiles if p.phone == phone), None)
            if existing is not None:
                existing.api_id = api_id
                if display_name:
                    existing.display_name = display_name
                profile = existing
            else:
                profile = Profile(phone=phone, display_name=display_name or phone, api_id=api_id)
                self._profiles.append(profile)
            if set_active or self._active_phone is None:
                self._active_phone = phone
            self._save()
            return profile

    def set_active(self, phone: str) -> Optional[Profile]:
        phone = _normalize_phone(phone)
        with self._lock:
            profile = next((p for p in self._profiles if p.phone == phone), None)
            if profile is None:
                return None
            self._active_phone = profile.phone
            self._save()
            return profile

    def remove(self, phone: str) -> bool:
        """Удаляет профиль и его сессию через ISecretStore."""
        phone = _normalize_phone(phone)
        with self._lock:
            profile = next((p for p in self._profiles if p.phone == phone), None)
            if profile is None:
                return False
            self._profiles = [p for p in self._profiles if p.phone != phone]
            if self._active_phone == phone:
                self._active_phone = self._profiles[0].phone if self._profiles else None
            self._save()
            api_id = profile.api_id
        self._delete_session(api_id, phone)
        return True

    def rename(self, phone: str, display_name: str) -> bool:
        phone = _normalize_phone(phone)
        with self._lock:
            profile = next((p for p in self._profiles if p.phone == phone), None)
            if profile is None:
                return False
            profile.display_name = display_name or phone
            self._save()
            return True

    # ---------------------------------------------------------- session I/O

    def load_session(self, profile: Profile) -> Optional[str]:
        if not profile.api_id or not profile.phone:
            return None
        return self._secrets.get(_session_key(profile.api_id, profile.phone))

    def save_session(self, profile: Profile, session_string: str) -> None:
        if not session_string or not profile.api_id or not profile.phone:
            return
        self._secrets.set(_session_key(profile.api_id, profile.phone), session_string)

    def _delete_session(self, api_id: str, phone: str) -> None:
        if not api_id or not phone:
            return
        key = _session_key(api_id, phone)
        self._secrets.delete(key)
