"""Домашнее задание №2."""

from collections.abc import Iterator
from types import TracebackType
from typing import Any, Self


class StackIsEmptyError(Exception):
    """Exception raised when the stack is empty."""

    def __init__(self, message: str = "Стек пуст.") -> None:
        super().__init__(message)


class StackTypeMismatchError(Exception):
    """Exception raised when the stack is of a different type."""

    def __init__(self, message: str = "Стек имеет неверный тип.") -> None:
        super().__init__(message)


class Stack[T: Any]:
    """Stack data structure."""

    def __init__(self) -> None:
        self._data: list[T] = []

    def push(self, item: T) -> None:
        """Push item onto stack.

        Args:
            item: Item to push onto stack.

        """
        self._data.append(item)

    def pop(self) -> T:
        """Remove and return item from stack.

        Returns:
            item: Item removed from stack.

        Raises:
            StackIsEmptyError: If stack is empty.

        """
        try:
            return self._data.pop()
        except IndexError as exc:
            raise StackIsEmptyError from exc

    def __len__(self) -> int:
        """Return number of items in stack.

        Returns:
            int: Number of items in stack.

        """
        return len(self._data)

    def __str__(self) -> str:
        """Return string representation of stack.

        Returns:
            str: String representation of stack.

        """
        return f"Stack({', '.join(map(str, self._data))})"

    def __repr__(self) -> str:
        """Return string representation of stack.

        Returns:
            str: String representation of stack.

        """
        return f"Stack({self._data})"

    def __iter__(self) -> Iterator[T]:
        """Return iterator over the items in stack.

        Returns:
            Iterator[T]: Iterator over the items in stack.

        """
        return iter(self._data)

    def __contains__(self, item: T) -> bool:
        """Return True if item is in stack.

        Args:
            item: Item to check if it is in stack.

        Returns:
            True if item is in stack, False otherwise.

        """
        return item in self._data

    def __getitem__(self, index: int) -> T:
        """Return item at index in stack.

        Args:
            index: Index of item to return.

        Returns:
            item: Item at index in stack.

        """
        return self._data[index]

    def __eq__(self, other: Self) -> bool:
        """Return True if stacks are equal.

        Args:
            other: Other stack to compare with.

        Returns:
            True if stacks are equal, False otherwise.

        Raises:
            StackTypeMismatchError:
              If other is not a Stack or does not have a _data attribute.

        """
        if not isinstance(other, Stack) or getattr(other, "_data", None) is None:
            raise StackTypeMismatchError

        return self._data == other._data

    def __enter__(self) -> Self:
        """Return self as context manager.

        Returns:
            self: Stack[T]

        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit context manager.

        Args:
            exc_type: Type of exception that was raised.
            exc_value: Value of exception that was raised.
            traceback: Traceback of exception that was raised.

        Returns:
            None if no exception was raised, otherwise re-raise the exception.

        """
        return self._data.clear()
