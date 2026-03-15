"""Домашнее задание №2."""

from typing import Any


class StackIsEmptyError(Exception):
    """Exception raised when the stack is empty."""

    def __init__(self, message: str = "Стек пуст.") -> None:
        super().__init__(message)


class Stack[T: Any]:
    """Stack data structure."""

    def __init__(self) -> None:
        self._data: list[T] = []

    def push(self, item: T) -> None:
        """Push item onto stack."""
        self._data.append(item)

    def pop(self) -> T:
        """Remove and return item from stack."""
        try:
            return self._data.pop()
        except IndexError as exc:
            raise StackIsEmptyError from exc

    def __str__(self) -> str:
        """Return string representation of stack."""
        return f"Stack<{self._data}, len={len(self._data)}>"

    def __repr__(self) -> str:
        """Return string representation of stack."""
        return self.__str__()
