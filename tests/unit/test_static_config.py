"""Tests for StaticConfig."""
import pytest

from tg_exporter.configs.static_config import StaticConfig
from tg_exporter.services.export.exporters.markdown_settings import MarkdownSettings, ConfigValidationError


class TestStaticConfig:

    def test_have_valid_defaults(self):
        cfg = StaticConfig()
        cfg.markdown.validate()

    def test_strip_non_digits_from_api_id(self):
        cfg = StaticConfig.from_raw({"api_id": " 12 34 "})
        assert cfg.api_id == " 12 34 "
        assert cfg.api_id_int == 1234

    def test_return_none_for_api_id_int_when_empty(self):
        cfg = StaticConfig()
        assert cfg.api_id_int is None

    def test_throw_on_invalid_words_per_file(self):
        cfg = StaticConfig(markdown=MarkdownSettings(words_per_file=100))
        with pytest.raises(ConfigValidationError):
            cfg.markdown.validate()

    def test_load_nested_fields_from_raw(self):
        cfg = StaticConfig.from_raw({
            "api_id": "123",
            "api_hash": "my_hash",
            "deepgram_api_key": "dg_key",
            "transcription": {
                "provider": "deepgram",
                "model": "large",
                "language": "ru",
            },
            "defaults": {
                "format": "json",
                "words_per_file": 10000,
                "download_media": True,
            },
            "logging": {
                "level": "DEBUG",
            },
            "retry": {
                "max_attempts": 5,
            },
        })
        assert cfg.api_id == "123"
        assert cfg.api_hash == "my_hash"
        assert cfg.deepgram_api_key == "dg_key"
        assert cfg.transcription_provider == "deepgram"
        assert cfg.transcription_model == "large"
        assert cfg.transcription_language == "ru"
        assert cfg.default_format == "json"
        assert cfg.default_words_per_file == 10000
        assert cfg.default_download_media is True
        assert cfg.log_level == "DEBUG"
        assert cfg.retry_max_attempts == 5

    def test_default_secrets_source_to_file(self):
        cfg = StaticConfig()
        assert cfg.secrets_source == "file"

    def test_roundtrip_markdown_settings(self):
        s = MarkdownSettings(words_per_file=30_000, date_format="YYYY-MM-DD", plain_text=False)
        s2 = MarkdownSettings.from_dict(s.to_dict())
        assert s2.words_per_file == 30_000
        assert s2.date_format == "YYYY-MM-DD"
        assert s2.plain_text is False
