# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Important:** Also read `AGENTS.md` — this project has detailed rules for AI agents (Russian responses, plan-before-implement workflow, anti-semantic-collapse rules, test conventions).

## Commands

```bash
# Install in dev mode
pip install -e ".[dev]"

# Lint
ruff check .

# Run all tests
pytest

# Run a single test file
pytest tests/unit/test_converter.py

# Run a single test function
pytest tests/unit/test_converter.py::test_convert_text_message -v

# Run all tests in a category
pytest tests/unit/
pytest tests/func/
pytest tests/integration/
```

## Architecture

Two packages with strict layering:

- **`tg_exporter/`** — core library. Services, models, Telegram client abstraction. Does NOT depend on CLI.
- **`tg_exporter_cli/`** — CLI interface. Click commands + DI host. Depends on core.

Data flow: `CLI commands` → `CliHost (DI)` → `Services` → `Models (frozen dataclasses)`

### Dependency Injection

`CliHost.build()` in `tg_exporter_cli/hosting/cli_host.py` reads config, creates `StaticConfig` and `StateModel`, registers all services as singletons in the `Container`. CLI commands access services via `get_host().get(ServiceType)` where `get_host()` calls `click.get_current_context().obj`.

To override services in tests, use `host.rebind_services(callback)`.

### Telegram client abstraction

- `ITelegramClientManager` (ABC) — lifecycle management
- `TelegramClientInterface` (ABC) — the actual API contract
- `TelethonClientAdapter` — real Telethon implementation
- `FakeTelegramClient` / `FakeTelegramClientManager` — test doubles

`converter.py` is the **single** place where Telethon types are converted to domain models (`ExportMessage`). Everything downstream works with pure Python types.

### Secrets

`ISecretStore` abstracts secret storage. Priority: env vars (`TG_EXPORTER_*`) > `.env` > `secrets.json` > system keyring. `EnvFallbackSecretStore` wraps `JsonSecretStore` for CI/CD support.

### One file = one class

File name is `snake_case` of the class name. For example, `ExportOrchestrator` lives in `export_orchestrator.py`.

### Key exports flow

```
TelegramClientInterface → converter → ExportMessage
                                          │
                                   ExportOrchestrator
                                     ├── JsonExporter → result.json
                                     ├── MarkdownExporter → _part_N.md
                                     ├── MediaDownloader → media/
                                     ├── Transcriber → text
                                     └── AnalyticsCollector → analytics/
```

### Cancellation

Long-running operations accept `CancellationToken`. Checked in each iteration of the export loop. Ctrl+C triggers cancellation.

## Tests

```
tests/
├── unit/         # Pure components, 0-2 deps, no DI needed
├── func/         # Business logic, 3+ deps, uses DI + fakes
├── integration/  # Multi-subsystem interactions
└── common/fakes/ # Fake implementations for tests
```

- `pytest` only, never `unittest.TestCase`
- Test naming: `test_{expected_behavior}[_when_{condition}]`
- `asyncio_mode = "strict"` in pytest config — all async tests get automatic event loop
- Docstrings on func and integration tests in Russian
- Тестами покрываются основные сценарии команд: happy path, ключевые флаги, типичные ошибки
