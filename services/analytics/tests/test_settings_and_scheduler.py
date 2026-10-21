"""Settings and scheduler process."""

import asyncio
import logging
import signal
from datetime import timedelta

import pytest
from pydantic import ValidationError

from analytics.common.config import Settings, get_settings
from analytics.ingestion import scheduler
from analytics.ingestion.scheduler import (
    HEARTBEAT_INTERVAL_SECONDS,
    build_scheduler,
    heartbeat,
    install_signal_handler,
    serve,
)


def test_the_service_token_must_have_32_characters() -> None:
    with pytest.raises(ValidationError):
        Settings(service_token="too-short")


def test_the_service_token_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SERVICE_TOKEN", raising=False)
    get_settings.cache_clear()

    with pytest.raises(ValidationError):
        Settings()


def test_the_log_level_must_be_known() -> None:
    with pytest.raises(ValidationError):
        Settings(service_token="a" * 32, log_level="chatty")


def test_the_environment_is_read_from_the_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANALYTICS_DB_URL", "postgresql+asyncpg://user:pw@db:5432/name")
    monkeypatch.setenv("REDIS_URL", "redis://:pw@cache:6379/0")
    monkeypatch.setenv("SERVICE_TOKEN", "b" * 32)
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("ENV", "test")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.analytics_db_url == "postgresql+asyncpg://user:pw@db:5432/name"
    assert settings.redis_url == "redis://:pw@cache:6379/0"
    assert settings.service_token.get_secret_value() == "b" * 32
    assert settings.log_level == "DEBUG"
    assert settings.env == "test"


def test_the_scheduler_registers_a_heartbeat_job() -> None:
    scheduler = build_scheduler()

    job = scheduler.get_job("heartbeat")

    assert job is not None
    assert job.trigger.interval == timedelta(seconds=HEARTBEAT_INTERVAL_SECONDS)


async def test_the_heartbeat_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    await heartbeat()

    assert "scheduler heartbeat" in caplog.messages


async def test_the_scheduler_stops_cleanly(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    scheduler = build_scheduler()
    stop = asyncio.Event()

    task = asyncio.create_task(serve(scheduler, stop))
    await asyncio.sleep(0.2)
    stop.set()
    await asyncio.wait_for(task, timeout=5)

    assert "scheduler started" in caplog.messages
    assert "scheduler stopped" in caplog.messages


def test_the_signal_handler_is_installed() -> None:
    stop = asyncio.Event()
    loop = asyncio.new_event_loop()
    try:
        install_signal_handler(loop, stop, signal.SIGTERM)
    finally:
        loop.close()


def test_the_entry_point_runs_the_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []

    async def fake_run() -> None:
        calls.append(True)

    monkeypatch.setattr(scheduler, "run", fake_run)

    scheduler.main()

    assert calls == [True]
