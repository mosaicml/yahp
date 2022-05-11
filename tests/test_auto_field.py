from typing import Callable
from unittest.mock import Mock

import pytest

import yahp as hp
import yahp.field


class FooClassDocstring:
    """Foo class

    Args:
        required (str): Required parameter.
        optional (int, optional): Optional parameter. (default: ``5``)
    """

    def __init__(self, required: str, optional: int = 5):
        self.required = required
        self.optional = optional


class FooClassAndInitDocstring:
    """Foo class.
    """

    def __init__(self, required: str, optional: int = 5):
        """Foo init.

        Args:
            required (str): Required parameter.
            optional (int, optional): Optional parameter. (default: ``5``)
        """
        self.required = required
        self.optional = optional


def foo_func(required: str, optional: int = 5):
    """Foo func.

    Args:
        required (str): Required parameter.
        optional (int, optional): Optional parameter. (default: ``5``)
    """
    del required, optional  # unused


@pytest.mark.parametrize('constructor', [FooClassDocstring, FooClassAndInitDocstring, foo_func])
class TestHpAuto:

    def test_required(self, constructor: Callable, monkeypatch: pytest.MonkeyPatch):
        mock = Mock()
        mock.return_value = 'MOCK_RETURN'
        monkeypatch.setattr(yahp.field, 'required', mock)
        field = hp.auto(constructor, 'required')
        mock.assert_called_once_with('Required parameter.')
        assert field == mock.return_value

    def test_optional(self, constructor: Callable, monkeypatch: pytest.MonkeyPatch):
        mock = Mock()
        mock.return_value = 'MOCK_RETURN'
        monkeypatch.setattr(yahp.field, 'optional', mock)
        field = hp.auto(constructor, 'optional')
        mock.assert_called_once_with('Optional parameter. (default: ``5``)', default=5)
        assert field == mock.return_value
