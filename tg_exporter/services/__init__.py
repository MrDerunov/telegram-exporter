# Lazy imports to avoid circular imports (services.export <-> hosting.app_config)
# Import directly from submodules:
#   from tg_exporter.services.analytics import AnalyticsCollector
#   from tg_exporter.services.export_history import ExportHistory
#   from tg_exporter.services.media_downloader import MediaDownloader

__all__: list[str] = []


def __getattr__(name: str):
    if name == "AnalyticsCollector":
        from .analytics import AnalyticsCollector
        return AnalyticsCollector
    if name == "render_top_authors":
        from .analytics import render_top_authors
        return render_top_authors
    if name == "render_activity":
        from .analytics import render_activity
        return render_activity
    if name == "MediaDownloader":
        from .media_downloader import MediaDownloader
        return MediaDownloader
    if name == "ExportHistory":
        from .export_history import ExportHistory
        return ExportHistory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
