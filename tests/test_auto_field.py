from typing import Callable
from unittest.mock import Mock

import docstring_parser
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


def missing_foo_docstring(foo: str):
    """Foo func."""
    del foo  # unused


def missing_docstring(foo: str):
    del foo  # unused


def malformed_docstring(foo: str):
    """Docstring

    Args:
        foo (Leaving parenthesis open...
    """


@pytest.fixture
def mock_required_field(monkeypatch: pytest.MonkeyPatch):
    mock = Mock()
    mock.return_value = 'MOCK_RETURN'
    monkeypatch.setattr(yahp.field, 'required', mock)
    return mock


@pytest.fixture
def mock_optional_field(monkeypatch: pytest.MonkeyPatch):
    mock = Mock()
    mock.return_value = 'MOCK_RETURN'
    monkeypatch.setattr(yahp.field, 'optional', mock)
    return mock


@pytest.mark.parametrize('constructor', [FooClassDocstring, FooClassAndInitDocstring, foo_func])
class TestHpAuto:

    def test_required(self, constructor: Callable, mock_required_field: Mock):
        field = hp.auto(constructor, 'required')
        mock_required_field.assert_called_once_with('Required parameter.')
        assert field == mock_required_field.return_value

    def test_optional(self, constructor: Callable, mock_optional_field: Mock):
        field = hp.auto(constructor, 'optional')
        mock_optional_field.assert_called_once_with('Optional parameter. (default: ``5``)', default=5)
        assert field == mock_optional_field.return_value

    def test_docstring_override(self, constructor: Callable, mock_optional_field: Mock):
        field = hp.auto(constructor, 'optional', doc='Custom docstring')
        mock_optional_field.assert_called_once_with('Custom docstring', default=5)
        assert field == mock_optional_field.return_value


@pytest.mark.parametrize('constructor', [missing_foo_docstring, missing_docstring, malformed_docstring])
def test_bad_docstring_ignore_errors(constructor: Callable, mock_required_field: Mock):
    with pytest.warns(match='Argument foo will be undocumented'):
        field = hp.auto(constructor, 'foo', ignore_docstring_errors=True)
    mock_required_field.assert_called_once_with('foo')
    assert field == mock_required_field.return_value


@pytest.mark.parametrize('constructor', [missing_foo_docstring, missing_docstring, malformed_docstring])
def test_bad_docstring_raise_exceptions(constructor: Callable):
    with pytest.raises((docstring_parser.ParseError, ValueError)):
        hp.auto(constructor, 'foo')
