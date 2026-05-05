"""
Исключения для медиа-загрузчика.
"""


class MediaTooLongError(Exception):
    """Аудио длиннее допустимого лимита."""


class MediaProcessingError(Exception):
    """Не удалось обработать медиафайл."""


class _CancelledDuringDownload(Exception):
    """Внутреннее исключение — отмена во время progress_callback."""
