"""
Resilient retry utility with exponential backoff and jitter for external network calls.
Adheres to Architecture Rules Section 44: Retries.
"""

import asyncio
import functools
import inspect
import random
import time
from typing import Any, Callable, TypeVar

from backend.app.observability.logger import get_logger

logger = get_logger("factlens.retry")

T = TypeVar("T")


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retry_on: tuple[type[Exception], ...] = (Exception,),
    exclude: tuple[type[Exception], ...] = (ValueError, TypeError, KeyError),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying transient operations with exponential backoff and optional jitter.
    Supports both synchronous and asynchronous functions.

    :param max_attempts: Maximum number of execution attempts before re-raising.
    :param initial_delay: Delay in seconds before the first retry attempt.
    :param backoff_factor: Multiplier for subsequent retry delays.
    :param jitter: Whether to add random variance to avoid thundering herd.
    :param retry_on: Tuple of exception types to trigger a retry.
    :param exclude: Tuple of exception types that should fail fast without retrying.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        func_name = getattr(func, "__name__", str(func))

        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                delay = initial_delay
                last_exc: Exception | None = None

                for attempt in range(1, max_attempts + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exclude as exc:
                        logger.warning(f"[{func_name}] Non-retriable error {type(exc).__name__}: {exc}. Failing fast.")
                        raise
                    except retry_on as exc:
                        last_exc = exc
                        if attempt == max_attempts:
                            logger.error(f"[{func_name}] Failed after {max_attempts} attempts. Error: {exc}")
                            raise

                        sleep_time = delay
                        if jitter:
                            sleep_time += random.uniform(0, 0.5 * delay)

                        logger.warning(
                            f"[{func_name}] Transient error on attempt {attempt}/{max_attempts}: {exc}. "
                            f"Retrying in {sleep_time:.2f}s..."
                        )
                        await asyncio.sleep(sleep_time)
                        delay *= backoff_factor

                if last_exc:
                    raise last_exc

            return async_wrapper

        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                delay = initial_delay
                last_exc: Exception | None = None

                for attempt in range(1, max_attempts + 1):
                    try:
                        return func(*args, **kwargs)
                    except exclude as exc:
                        logger.warning(f"[{func_name}] Non-retriable error {type(exc).__name__}: {exc}. Failing fast.")
                        raise
                    except retry_on as exc:
                        last_exc = exc
                        if attempt == max_attempts:
                            logger.error(f"[{func_name}] Failed after {max_attempts} attempts. Error: {exc}")
                            raise

                        sleep_time = delay
                        if jitter:
                            sleep_time += random.uniform(0, 0.5 * delay)

                        logger.warning(
                            f"[{func_name}] Transient error on attempt {attempt}/{max_attempts}: {exc}. "
                            f"Retrying in {sleep_time:.2f}s..."
                        )
                        time.sleep(sleep_time)
                        delay *= backoff_factor

                if last_exc:
                    raise last_exc

            return sync_wrapper

    return decorator
