"""Конфигурация pytest: поддержка should_* методов в unittest.TestCase."""

from __future__ import annotations

import unittest


def pytest_configure(config):
    """Патч unittest.TestLoader для сбора should_* методов наряду с test_*."""

    # getTestCaseNames — обычный instance-метод, получаем функцию напрямую
    original_func = unittest.TestLoader.getTestCaseNames

    def patched_get_test_case_names(self, testCaseClass):
        """Собирает методы с префиксами test_ и should_."""
        # Стандартные test_ методы
        names = list(original_func(self, testCaseClass))
        # Добавляем should_ методы, которых ещё нет в списке
        prefix = "should_"
        for attr_name in dir(testCaseClass):
            if not attr_name.startswith(prefix):
                continue
            if attr_name in names:
                continue
            attr = getattr(testCaseClass, attr_name)
            if callable(attr):
                names.append(attr_name)
        return names

    unittest.TestLoader.getTestCaseNames = patched_get_test_case_names
