"""Tests for StaticConfig."""
import unittest

from tg_exporter.configs.static_config import StaticConfig
from tg_exporter.services.export.exporters.markdown_settings import MarkdownSettings, ConfigValidationError


class TestStaticConfig(unittest.TestCase):

    def should_have_valid_defaults(self):
        cfg = StaticConfig()
        cfg.markdown.validate()  # no raise

    def should_strip_non_digits_from_api_id(self):
        cfg = StaticConfig.from_raw({"api_id": " 12 34 "})
        self.assertEqual(cfg.api_id, " 12 34 ")
        self.assertEqual(cfg.api_id_int, 1234)

    def should_return_none_for_api_id_int_when_empty(self):
        cfg = StaticConfig()
        self.assertIsNone(cfg.api_id_int)

    def should_throw_on_invalid_words_per_file(self):
        cfg = StaticConfig(markdown=MarkdownSettings(words_per_file=100))
        with self.assertRaises(ConfigValidationError):
            cfg.markdown.validate()

    def should_load_nested_fields_from_raw(self):
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
        self.assertEqual(cfg.api_id, "123")
        self.assertEqual(cfg.api_hash, "my_hash")
        self.assertEqual(cfg.deepgram_api_key, "dg_key")
        self.assertEqual(cfg.transcription_provider, "deepgram")
        self.assertEqual(cfg.transcription_model, "large")
        self.assertEqual(cfg.transcription_language, "ru")
        self.assertEqual(cfg.default_format, "json")
        self.assertEqual(cfg.default_words_per_file, 10000)
        self.assertTrue(cfg.default_download_media)
        self.assertEqual(cfg.log_level, "DEBUG")
        self.assertEqual(cfg.retry_max_attempts, 5)

    def should_default_secrets_source_to_file(self):
        cfg = StaticConfig()
        self.assertEqual(cfg.secrets_source, "file")

    def should_roundtrip_markdown_settings(self):
        s = MarkdownSettings(words_per_file=30_000, date_format="YYYY-MM-DD", plain_text=False)
        s2 = MarkdownSettings.from_dict(s.to_dict())
        self.assertEqual(s2.words_per_file, 30_000)
        self.assertEqual(s2.date_format, "YYYY-MM-DD")
        self.assertFalse(s2.plain_text)
