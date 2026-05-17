"""Тесты Container — DI-контейнер."""

from __future__ import annotations

import pytest

from tg_exporter_cli.hosting.container import Container

# ---------------------------------------------------------------------------
# Вспомогательные типы для тестов
# ---------------------------------------------------------------------------


class IFoo:
    pass


class Foo:
    pass


class IBar:
    pass


class Bar:
    pass

# ---------------------------------------------------------------------------
# Тесты
# ---------------------------------------------------------------------------


class TestContainer:

    def test_create_instance_via_factory(self):
        """Регистрация фабрики и получение инстанса через get."""
        c = Container()
        c.register(Foo, lambda _: Foo())
        instance = c.get(Foo)
        assert isinstance(instance, Foo)

    def test_return_same_instance_on_repeated_get(self):
        """Повторный get возвращает тот же инстанс (singleton)."""
        c = Container()
        c.register(Foo, lambda _: Foo())
        first = c.get(Foo)
        second = c.get(Foo)
        assert first is second

    def test_create_instance_lazily(self):
        """Фабрика не вызывается до первого get."""
        c = Container()
        called = []

        def factory(_container):
            called.append(True)
            return Foo()

        c.register(Foo, factory)
        assert called == []
        c.get(Foo)
        assert called == [True]

    def test_register_instance(self):
        """register_instance регистрирует готовый инстанс."""
        c = Container()
        foo = Foo()
        c.register_instance(Foo, foo)
        assert c.get(Foo) is foo

    def test_register_instance_overrides_factory(self):
        """Готовый инстанс отдаётся вместо фабрики."""
        c = Container()
        foo_direct = Foo()
        c.register(Foo, lambda _: Foo())
        c.register_instance(Foo, foo_direct)
        assert c.get(Foo) is foo_direct

    def test_register_interface_resolves_to_implementation(self):
        """get по интерфейсу возвращает инстанс реализации."""
        c = Container()
        c.register_interface(IFoo, Foo)
        c.register(Foo, lambda _: Foo())
        instance = c.get(IFoo)
        assert isinstance(instance, Foo)

    def test_register_interface_also_works_for_implementation_type(self):
        """get по типу реализации тоже работает."""
        c = Container()
        c.register_interface(IFoo, Foo)
        c.register(Foo, lambda _: Foo())
        instance = c.get(Foo)
        assert isinstance(instance, Foo)

    def test_throw_on_unregistered_type(self):
        """get для незарегистрированного типа вызывает KeyError."""
        c = Container()
        with pytest.raises(KeyError):
            c.get(Foo)

    def test_autocreate_instance_for_interface_without_factory(self):
        """get по интерфейсу автосоздаёт реализацию, даже без явной фабрики."""
        c = Container()
        c.register_interface(IFoo, Foo)
        instance = c.get(IFoo)
        assert isinstance(instance, Foo)

    def test_autocreate_instance_is_singleton(self):
        """Автосозданный инстанс тоже singleton."""
        c = Container()
        c.register_interface(IFoo, Foo)
        first = c.get(IFoo)
        second = c.get(IFoo)
        assert first is second

    def test_register_updates_factory_for_uncreated_instance(self):
        """Повторный register меняет фабрику, если инстанс ещё не создан."""
        c = Container()
        c.register(Foo, lambda _: Foo())
        # Переопределяем фабрику на другой тип
        c.register(Foo, lambda _: Bar())
        instance = c.get(Foo)
        assert isinstance(instance, Bar)

    def test_register_does_not_replace_existing_instance(self):
        """register после get не заменяет уже созданный инстанс."""
        c = Container()
        c.register(Foo, lambda _: Foo())
        first = c.get(Foo)

        # Регистрируем новую фабрику
        c.register(Foo, lambda _: Bar())
        second = c.get(Foo)
        assert first is second
        assert isinstance(first, Foo)

    def test_register_instance_replaces_existing_instance(self):
        """register_instance перезаписывает ранее созданный инстанс."""
        c = Container()
        c.register(Foo, lambda _: Foo())
        first = c.get(Foo)

        new_foo = Bar()
        c.register_instance(Foo, new_foo)
        second = c.get(Foo)
        assert second is new_foo
        assert second is not first

    def test_multiple_interfaces_to_same_implementation(self):
        """Несколько интерфейсов могут указывать на один тип реализации."""
        c = Container()
        c.register_interface(IFoo, Foo)
        c.register_interface(IBar, Foo)
        c.register(Foo, lambda _: Foo())
        instance_ifoo = c.get(IFoo)
        instance_ibar = c.get(IBar)
        assert isinstance(instance_ifoo, Foo)
        assert isinstance(instance_ibar, Foo)
        assert instance_ifoo is instance_ibar

    def test_container_is_empty_initially(self):
        """Новый контейнер не содержит зарегистрированных типов."""
        c = Container()
        with pytest.raises(KeyError):
            c.get(Foo)
