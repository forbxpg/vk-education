"""Домашнее задание 3. Магия валидации.

Это домашнее задание предназначено для глубокого погружения во внутренние механизмы Python,
которые служат фундаментом для таких популярных технологий, как Django ORM, SQLAlchemy,
Pydantic и веб-фреймворки уровня FastAPI. Понимание принципов работы дескрипторов и метаклассов
позволяет разработчику перестать воспринимать декларативный синтаксис этих библиотек как “магию”
и начать осознанно проектировать сложные архитектуры, системы валидации и автоматической регистрации
компонентов.

В рамках этого домашнего задания будет 4 задачи:
1. Реализовать базовый дескриптор типа
2. Создать дескриптор с валидацией значений
3. Создать метакласс-реестр
4. Собрать все созданные компоненты воедино
"""

"""
Шаг 1. Базовый дескриптор типа
В статически типизированных языках компилятор следит за типами.
В Python эту роль часто берут на себя дескрипторы (аналог Field в Pydantic).

Реализуйте класс-дескриптор TypedProperty, который при присваивании значения атрибуту
проверяет его тип. Если тип не совпадает с ожидаемым - выбрасывать TypeError.
Дескриптор должен принимать ожидаемый тип в __init__.
Должны быть реализованы методы __get__, __set__, __set_name__.
Хранение значения должно происходить в экземпляре владельца (через instance.__dict__),
а не внутри дескриптора
"""


class TypedProperty:
    """Base descriptor for type checking.

    Attributes:
        _expected_type (type): The expected type of the attribute.
        name (str | None): The name of the attribute.

    Methods:
        __get__(instance: object, owner: type) -> object:
            Get the value of the attribute.
        __set__(instance: object, value: object) -> None:
            Set the value of the attribute.
        __set_name__(owner: type, name: str) -> None:
            Set the name of the attribute on the owner class.

    """

    def __init__(self, expected_type: type) -> None:
        self._expected_type = expected_type
        self.name: str | None = None

    def __set_name__(self, owner: type, name: str) -> None:
        """Set the name of the attribute on the owner class.

        Args:
            owner (type): The owner class.
            name (str): The name of the attribute.

        """
        self.name = name

    def __get__(self, instance: object, owner: type) -> object:
        """Get the value of the attribute.

        Args:
            instance (object): The instance of the owner class.
            owner (type): The owner class.

        Returns:
            object: The value of the attribute.

        Note:
            When class creates name is already being assigned by `__set_name__`.
            So we ignore the type checking here.

        """
        if instance is None:
            return self

        return instance.__dict__.get(self.name)

    def __set__(self, instance: object, value: object) -> None:
        """Set the value of the attribute.

        Args:
            instance (object): The instance of the owner class.
            value (object): The value to set.

        Raises:
            TypeError: If the value is not of the expected type.

        """
        if not isinstance(value, self._expected_type):
            msg = (
                f"Атрибут `{self.name}` должен быть типа: "
                f"`{self._expected_type.__name__}` "
                f"(получен тип: `{type(value).__name__}`)"
            )
            raise TypeError(msg)

        instance.__dict__[self.name] = value


"""
ШАГ 2. ДЕСКРИПТОР С ВАЛИДАЦИЕЙ ЗНАЧЕНИЙ

Библиотеки вроде Pydantic не только проверяют тип, но и валидируют диапазон значений,
длину строки и т.д.

ЗАДАЧА

Создайте класс ValidatedProperty, унаследованный от TypedProperty.
Добавьте возможность передачи ограничений
(например, min, max для чисел или min_length для строк).

1) Требуется наличие поддержки как минимум одного типа валидации
(числовой диапазон ИЛИ длина строки (оба, само собой, допустимо)).
2) При нарушении ограничения выбрасывать ValueError.
"""


class ValidatedProperty(TypedProperty):
    """Descriptor that validates the value of an attribute.

    Attributes:
        min_value (int | float | None): The minimum value allowed.
        max_value (int | float | None): The maximum value allowed.
        min_length (int | None): The minimum length allowed for strings.
        max_length (int | None): The maximum length allowed for strings.

    Methods:
        _validate_number(value: float) -> None:
            Raises:
                ValueError: If the value is not valid.

        _validate_string(value: str) -> None:
            Raises:
                ValueError: If the value is not valid.

        _validate_all(value: object) -> None:
            calls _validate_number or _validate_string based on the type of value

        __set__(self, instance: object, value: object) -> None:
            inherited from TypedProperty with validation

    """

    def __init__(
        self,
        min_value: float | None = None,
        max_value: float | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
    ) -> None:
        self._min_value = min_value
        self._max_value = max_value
        self._min_length = min_length
        self._max_length = max_length

    def _validate_number(self, value: float) -> None:
        """Validate the number value.

        Raises:
            ValueError: If the value is not valid.

        """
        if self._min_value is not None and value < self._min_value:
            msg = (
                f"Атрибут {self.name} должен быть ({self.name} >= {self._min_value})"
                f" (получено: {value})"
            )
            raise ValueError(msg)

        if self._max_value is not None and value > self._max_value:
            msg = (
                f"Атрибут {self.name} должен быть ({self.name} <= {self._max_value})"
                f" (получено: {value})"
            )
            raise ValueError(msg)

    def _validate_string(self, value: str) -> None:
        """Validate the string value.

        Raises:
            ValueError: If the value is not valid.

        """
        str_len = len(value)
        if self._min_length is not None and str_len < self._min_length:
            msg = (
                f"Атрибут {self.name} должен быть не менее {self._min_length} символов"
                f" (получено: {str_len})"
            )
            raise ValueError(msg)

        if self._max_length is not None and str_len > self._max_length:
            msg = (
                f"Атрибут {self.name} должен быть не более {self._max_length} символов"
                f" (получено: {str_len})"
            )
            raise ValueError(msg)

    def _validate_all(self, value: object) -> None:
        """Validate the value."""
        if isinstance(value, (int, float)):
            self._validate_number(value)
        elif isinstance(value, str):
            self._validate_string(value)

    def __set__(self, instance: object, value: object) -> None:
        """Validate the value and set it on the instance."""
        super().__set__(instance, value)
        self._validate_all(value)


"""ШАГ 3. МЕТАКЛАСС-РЕЕСТР

SQLAlchemy использует метаклассы для маппинга (ORM), автоматически преобразуя классы
в таблицы базы данных в момент их создания.

ЗАДАЧА

Создайте метакласс RegistryMeta, который автоматически добавляет каждый созданный
с его помощью класс в глобальный словарь (реестр) по имени класса.

1) Метакласс должен наследоваться от type.
2) Реестр должен быть доступен через атрибут метакласса (например, RegistryMeta.registry).
3) Исключить дублирование имен в реестре (или обрабатывать это явно)."""


class RegistryMeta(type):
    """Metaclass that automatically registers every class created with it.

    Attributes:
        registry (dict[str, type]): Global registry of all registered classes.

    """

    registry: dict[str, type] = {}

    def __new__(
        metacls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, object],
    ) -> type:
        """Create a new class and register it in the global registry.

        Raises:
            ValueError: If the class name already exists in the registry.

        Note:
            If the class is a subclass of a class that uses this metaclass,
            it will be automatically registered.

            If the class name already exists in the registry, a `ValueError`
            will be raised.

            If theres no parent class that uses this metaclass, the class
            will not be registered because its base class.

        """
        cls = super().__new__(metacls, name, bases, namespace)

        if name in metacls.registry:
            msg = (
                f"Класс с именем `{name}` уже зарегистрирован. "
                f"Дублирование имён запрещено."
            )
            raise ValueError(msg)
        metacls.registry[name] = cls
        return cls


"""ШАГ 4. ИНТЕГРАЦИЯ

Соберем все созданные компоненты воедино. Так работает объявление моделей в Pydantic или SQLAlchemy:
    вы описываете поля классом, а метакласс собирает их в конфигурацию.

ЗАДАЧА

Создайте расширенный метакласс ModelMeta, наследующий RegistryMeta.
Метакласс должен собрать информацию о всех полях модели в атрибут _fields.
Наконец, создайте базовый класс Model, использующий RegistryMeta


1) При наследовании класса от Model метакласс должен сканировать атрибуты класса.
2) Все найденные дескрипторы сохраняются в словарь _fields
(имя атрибута -> объект дескриптора)."""


class ModelMeta(RegistryMeta):
    """Extended metaclass that scans class attributes for descriptors."""

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict,
    ) -> "ModelMeta":
        cls = super().__new__(mcs, name, bases, namespace)
        cls._fields = {
            key: val
            for key, val in namespace.items()
            if isinstance(val, TypedProperty)  # catching all TypedProperty instances
        }
        return cls


class Model(metaclass=ModelMeta):
    """Base class for models that uses ModelMeta as metaclass."""
