from .telegram_client_manager_interface import ITelegramClientManager
from .telegram_client_manager import TelethonClientManager, ClientNotConfiguredError
from .telegram_client_interface import TelegramClientInterface
from .telethon_client_adapter import TelethonClientAdapter
from .converter import message_to_export, _normalize, _build_forwarded_from, _build_reactions, _build_poll, _extract_links, _detect_media_type
import importlib


def __getattr__(name: str):
    _auth_map = {
        "AuthService": "tg_exporter.services.auth.auth_service",
        "AuthResult": "tg_exporter.services.auth.models.auth_result",
        "AuthStep": "tg_exporter.services.auth.models.auth_step",
        "SendCodeResult": "tg_exporter.services.auth.models.auth_result",
        "SendCodeParams": "tg_exporter.services.auth.models.auth_models",
        "VerifyCodeParams": "tg_exporter.services.auth.models.auth_models",
        "ExportSessionParams": "tg_exporter.services.auth.models.auth_models",
    }
    if name in _auth_map:
        mod = importlib.import_module(_auth_map[name])
        attr = getattr(mod, name)
        globals()[name] = attr
        return attr
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ITelegramClientManager",
    "TelethonClientManager",
    "ClientNotConfiguredError",
    "TelegramClientInterface",
    "TelethonClientAdapter",
    "AuthService",
    "AuthResult",
    "SendCodeResult",
    "AuthStep",
    "SendCodeParams",
    "VerifyCodeParams",
    "ExportSessionParams",
    "message_to_export",
    "_normalize",
    "_build_forwarded_from",
    "_build_reactions",
    "_build_poll",
    "_extract_links",
    "_detect_media_type",
]
