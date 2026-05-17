"""Пакет тестов. Патчит unittest для поддержки should_* методов."""

from __future__ import annotations

import unittest


def _patch_unittest_loader():
    """Патч unittest.TestLoader для сбора should_* методов наряду с test_*."""

    original_func = unittest.TestLoader.getTestCaseNames

    def patched_get_test_case_names(self, testCaseClass):
        names = list(original_func(self, testCaseClass))
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

    if unittest.TestLoader.getTestCaseNames is not patched_get_test_case_names:
        unittest.TestLoader.getTestCaseNames = patched_get_test_case_names


_patch_unittest_loader()
