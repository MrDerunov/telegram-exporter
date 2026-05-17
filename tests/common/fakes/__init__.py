"""Test doubles for tg-exporter."""
from .fake_telegram_client import FakeTelegramClient
from .fake_telegram_client_manager import FakeTelegramClientManager

__all__ = ["FakeTelegramClient", "FakeTelegramClientManager"]
