r"""Домашнее задание.

Вы разрабатываете сервис-агрегатор, который периодически парсит статьи с Хабра.
Внешние сервисы нестабильны: они могут отвечать долго, возвращать ошибки сети или временно быть недоступными.
Если сервис "упал", нет смысла продолжать слать запросы (это может усугубить ситуацию или быть расценено как DDoS).
Необходимо реализовать механизм защиты, который отслеживает здоровье внешнего сервиса и принимает решение:
выполнить запрос, подождать или сразу вернуть ошибку.

В рамках этого домашнего задания у вас будет 4 задачи:

Реализовать базовую структуру декоратора-фабрики
Научить декоратор помнить историю вызовов и различать успех\ошибку
Реализовать блокировку вызовов при частых ошибках
Добавить задержку при нестабильности и проверить входные данные
"""

from asyncio import Lock, sleep
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from functools import wraps
from typing import ParamSpec, TypeVar

T = TypeVar("T")
P = ParamSpec("P")

MIN_STATE_COUNT = 10
MAX_ERRORS_COUNT = 10
DEFAULT_SLEEP_TIME_SEC = 5
DEFAULT_NETWORK_ERRORS: list[type[BaseException]] = [ConnectionError, TimeoutError]


class CircuitBreakerOpenError(Exception):
    """Exception raised when the circuit breaker is open."""


class CircuitBreakerState(StrEnum):
    """States of the Circuit Breaker finite state machine."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CallResult(StrEnum):
    """Result of a single call for recording in the history."""

    SUCCESS = "success"
    FAILURE = "failure"


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker decorator config class."""

    state_count: int = 20
    error_count: int = 8
    sleep_time_sec: int = DEFAULT_SLEEP_TIME_SEC
    network_errors: list[type[BaseException]] = field(
        default_factory=lambda: list(DEFAULT_NETWORK_ERRORS),
    )

    def __post_init__(self) -> None:
        """Validate decorator input params.

        Raises:
            ValueError:
            - If state_count <= MIN_STATE_COUNT (must be > 10).
            - If error_count >= MAX_ERRORS_COUNT (must be < 10).
            - If sleep_time_sec is negative.
            - If error_count > state_count.
            - If network_errors is empty.

        """
        if self.sleep_time_sec < 0:
            msg = "sleep_time_sec не может быть отрицательным."
            raise ValueError(msg)

        if self.state_count <= MIN_STATE_COUNT:
            msg = f"state_count должен быть строго больше {MIN_STATE_COUNT}."
            raise ValueError(msg)

        if self.error_count >= MAX_ERRORS_COUNT:
            msg = f"error_count должен быть строго меньше {MAX_ERRORS_COUNT}."
            raise ValueError(msg)

        if self.error_count > self.state_count:
            msg = (
                f"error_count ({self.error_count}) не может превышать "
                f"state_count ({self.state_count}): порог ошибок "
                f"никогда не будет достигнут."
            )
            raise ValueError(msg)

        if not self.network_errors:
            msg = "network_errors не может быть пустым списком."
            raise ValueError(msg)


class CircuitBreaker:
    """Async decorator factory implementing the Circuit Breaker pattern.

    Tracks the health of an external service by recording call results
    in a sliding window and transitions between three states:

    CLOSED - normal operation, requests pass through.
    OPEN - too many failures, requests are blocked immediately.
    HALF_OPEN - cooldown elapsed, exactly one probe request is allowed.

    """

    def __init__(self, config: CircuitBreakerConfig) -> None:
        self._config = config
        self._lock = Lock()
        self._history: deque[CallResult] = deque(maxlen=config.state_count)
        self._state = CircuitBreakerState.CLOSED

        # Flag that says if a probe request is already in flight,
        # other coroutines should get a rejection.
        self._probe_in_flight = False

    async def _process_func_call(
        self,
        func: Callable[P, Awaitable[T]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        """Execute the wrapped function and update circuit state.

        Args:
            func: Callable[P, Awaitable[T]]
            *args: P.args
            **kwargs: P.kwargs

        Returns:
            T: The result of the function call.

        """
        network_errors = tuple(self._config.network_errors)

        try:
            result = await func(*args, **kwargs)
        except network_errors:
            async with self._lock:
                self._history.append(CallResult.FAILURE)

                if self._state == CircuitBreakerState.HALF_OPEN:
                    self._state = CircuitBreakerState.OPEN
                    self._probe_in_flight = False
                elif self._failure_count >= self._config.error_count:
                    self._state = CircuitBreakerState.OPEN
            raise

        async with self._lock:
            self._history.append(CallResult.SUCCESS)

            if self._state == CircuitBreakerState.HALF_OPEN:
                self._state = CircuitBreakerState.CLOSED
                self._probe_in_flight = False
        return result

    async def _preprocess_state(self) -> bool:
        """Check circuit state before the function call.

        Returns:
            True if the call is allowed to proceed, False otherwise.

        """
        need_backoff = False
        need_sleep = False

        async with self._lock:
            if self._state == CircuitBreakerState.CLOSED:
                if self._failure_count >= self._config.error_count:
                    self._state = CircuitBreakerState.OPEN
                    return False

                if self._history and self._history[-1] == CallResult.FAILURE:
                    need_backoff = True

            elif self._state == CircuitBreakerState.OPEN:
                if self._probe_in_flight:
                    return False
                self._state = CircuitBreakerState.HALF_OPEN
                self._probe_in_flight = True
                need_sleep = True

            elif self._state == CircuitBreakerState.HALF_OPEN:
                if self._probe_in_flight:
                    return False

        if need_sleep or need_backoff:
            await sleep(self._config.sleep_time_sec)

        return True

    @property
    def _failure_count(self) -> int:
        """Count failures in the current history window.

        Must be called under self._lock.
        """
        return self._history.count(CallResult.FAILURE)

    def __call__(
        self,
        func: Callable[P, Awaitable[T]],
    ) -> Callable[P, Awaitable[T]]:
        """Decorate an async function with Circuit Breaker logic.

        Args:
            func: Callable[P, Awaitable[T]]

        Returns:
            Callable[P, Awaitable[T]]

        """

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if not await self._preprocess_state():
                msg = (
                    f"Circuit OPEN for {func.__qualname__}: "
                    f"{self._failure_count}/{self._config.error_count} "
                    f"failures in last {self._config.state_count} calls."
                )
                raise CircuitBreakerOpenError(msg)
            return await self._process_func_call(func, *args, **kwargs)

        return wrapper
