r"""Домашнее задание.

Вы разрабатываете сервис-агрегатор, который периодически парсит статьи с Хабра. Внешние сервисы нестабильны: они могут отвечать долго, возвращать ошибки сети или временно быть недоступными. Если сервис "упал", нет смысла продолжать слать запросы (это может усугубить ситуацию или быть расценено как DDoS). Необходимо реализовать механизм защиты, который отслеживает здоровье внешнего сервиса и принимает решение: выполнить запрос, подождать или сразу вернуть ошибку.

В рамках этого домашнего задания у вас будет 4 задачи:

Реализовать базовую структуру декоратора-фабрики
Научить декоратор помнить историю вызовов и различать успех\ошибку
Реализовать блокировку вызовов при частых ошибках
Добавить задержку при нестабильности и проверить входные данные
"""

from asyncio import Lock, sleep
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from functools import wraps
from time import time
from typing import ParamSpec, TypeVar

T = TypeVar("T")
P = ParamSpec("P")

MIN_STATE_COUNT = 10
MAX_ERRORS_COUNT = 10
DEFAULT_SLEEP_TIME_SEC = 5
DEFAULT_NETWORK_ERRORS = [ConnectionError, TimeoutError]


class CircuitBreakerState(StrEnum):
    """Class to represent the states of circuit breaker."""

    # Allowed to make requests
    ALLOWED = "allowed"

    # Denied to make requests
    DENIED = "denied"

    # Try to make one request
    FIFTY_FIFTY = "fifty_fifty"


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker decorator config class."""

    network_errors: list[type[BaseException]]
    state_count: int = MIN_STATE_COUNT
    error_count: int = MAX_ERRORS_COUNT
    sleep_time_sec: int = DEFAULT_SLEEP_TIME_SEC

    def __post_init__(self) -> None:
        """Validate decorator input params.

        Args:
            state_count: int
            error_count: int

        Raises:
            ValueError:
            - If state_count is less than MIN_STATE_COUNT or negative.
            - If error_count is greater than MAX_ERRORS_COUNT or negative.


        """
        if self.state_count < 0 or self.error_count < 0 or self.sleep_time_sec < 0:
            msg = "В конфиге заданы отрицательные числа!"
            raise ValueError(msg)

        if self.state_count < MIN_STATE_COUNT:
            msg = f"Размер истории сообщений должен быть больше {MIN_STATE_COUNT}"
            raise ValueError(msg)

        if self.error_count > MAX_ERRORS_COUNT:
            msg = (
                f"Максимальное количество порога ошибок "
                f"не должно превышать {MAX_ERRORS_COUNT}"
            )
            raise ValueError(msg)

        if not self.network_errors:
            self.network_errors = DEFAULT_NETWORK_ERRORS


class CircuitBreaker:
    """Class-based sync decorator factory to improve periodical API calls.

    Implements:
        - Healthchecks of the API-server by handling exc.
        - Between-Requests time tracking to fit the rate limits.

    """

    def __init__(self, config: CircuitBreakerConfig) -> None:
        self._config = config

        self._lock = Lock()

        self.start_time = time()

        self._history: deque[CircuitBreakerState] = deque(maxlen=config.state_count)
        self._current_state = CircuitBreakerState.ALLOWED

    async def _process_func_call(
        self,
        func: Callable[P, Awaitable[T]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        """Process the function call."""

    async def _preprocess_state(self) -> bool:
        """Preprocess the state."""
        buffer_errors_count = self._history.count(CircuitBreakerState.DENIED)
        if buffer_errors_count >= self._config.error_count:
            await sleep(self._config.sleep_time_sec)

            async with self._lock:
                self._history.append()

    async def __call__[**P, T](
        self,
        func: Callable[P, Awaitable[T]],
    ) -> Callable[Callable[P, Awaitable[T]], Callable[P, Awaitable[T]]]:
        """Call the class and run decorator."""

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            async with self._lock:
                if self._current_state == CircuitBreakerState.DENIED:
                    await sleep(self._config.sleep_time_sec)
                    self._current_state = CircuitBreakerState.FIFTY_FIFTY

                elif self._current_state == CircuitBreakerState.FIFTY_FIFTY:
                    await self._process_func_call(func, *args, **kwargs)

                else:
                    await self._process_func_call(func, *args, **kwargs)
