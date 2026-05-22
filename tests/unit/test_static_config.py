"""Tests for StaticConfig."""

from tg_exporter.settings.configs import StaticConfig
from tg_exporter.settings.configs.markdown_config import MarkdownConfig


class TestStaticConfig:

    def test_have_valid_defaults(self):
        cfg = StaticConfig()
        cfg.markdown.validate()

    def test_strip_non_digits_from_api_id(self):
        cfg = StaticConfig.from_raw({"api_id": " 12 34 "})
        assert cfg.api_id == " 12 34 "

    def test_default_secrets_source_to_file(self):
        cfg = StaticConfig()
        assert cfg.secrets_source == "file"

    def test_roundtrip_markdown_settings(self):
        s = MarkdownConfig(words_per_file=30_000, date_format="YYYY-MM-DD", plain_text=False)
        s2 = MarkdownConfig.from_dict(s.to_dict())
        assert s2.words_per_file == 30_000
        assert s2.date_format == "YYYY-MM-DD"
        assert s2.plain_text is False
