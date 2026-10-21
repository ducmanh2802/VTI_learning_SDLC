"""Scheduler process of the Analytics service.

`python -m analytics.ingestion.scheduler` runs an APScheduler instance with
no business job yet: the collection jobs arrive in WP-10. The heartbeat job
proves that the process is alive and lets the orchestrator see the logs.
"""

import asyncio
import logging
import signal
from asyncio.events import AbstractEventLoop

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from analytics.common.config import get_settings
from analytics.common.logging import configure_logging
from analytics.common.time import TRADING_TZ, utcnow

logger = logging.getLogger("analytics.ingestion.scheduler")

HEARTBEAT_INTERVAL_SECONDS = 60


async def heartbeat() -> None:
    """Log that the scheduler is alive."""
    logger.info("scheduler heartbeat")


def build_scheduler() -> AsyncIOScheduler:
    """Build the scheduler with its heartbeat job and no business job."""
    scheduler = AsyncIOScheduler(timezone=TRADING_TZ)
    scheduler.add_job(
        heartbeat,
        trigger="interval",
        seconds=HEARTBEAT_INTERVAL_SECONDS,
        id="heartbeat",
        next_run_time=utcnow(),
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    return scheduler


async def serve(scheduler: AsyncIOScheduler, stop: asyncio.Event) -> None:
    """Run the scheduler until the stop event is set."""
    scheduler.start()
    logger.info("scheduler started")
    try:
        await stop.wait()
    finally:
        scheduler.shutdown(wait=True)
        logger.info("scheduler stopped")


def install_signal_handler(
    loop: AbstractEventLoop, stop: asyncio.Event, signal_number: signal.Signals
) -> None:
    """Ask the scheduler to stop on SIGTERM and SIGINT."""
    try:
        loop.add_signal_handler(signal_number, stop.set)
    except NotImplementedError:  # pragma: no cover - Windows has no loop signal handlers
        signal.signal(signal_number, lambda *_: stop.set())


async def run() -> None:
    """Run the scheduler until a termination signal is received."""
    scheduler = build_scheduler()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signal_number in (signal.SIGTERM, signal.SIGINT):
        install_signal_handler(loop, stop, signal_number)
    await serve(scheduler, stop)


def main() -> None:
    """Entry point of the scheduler process."""
    configure_logging(get_settings().log_level)
    asyncio.run(run())


if __name__ == "__main__":
    main()
