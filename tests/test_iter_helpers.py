import pytest

from yahp.utils.iter_helpers import ListOfSingleItemDict


def test_getitem():
    x = [{'a': 'foo'}, {'b': 'bar'}]
    x = ListOfSingleItemDict(x)

    assert x['a'] == 'foo'
    assert x['b'] == 'bar'


def test_failed_getitem():
    x = [{'a': 'foo'}, {'b': 'bar'}]
    x = ListOfSingleItemDict(x)

    with pytest.raises(TypeError):
        _ = x['c']


def test_setitem_new_key():
    x = [{'a': 'foo'}, {'b': 'bar'}]
    x = ListOfSingleItemDict(x)
    x['c'] = 'baz'
    assert 'c' in x
    assert x['c'] == 'baz'


def test_setitem_overwrite():
    x = [{'a': 'foo'}, {'b': 'bar'}]
    x = ListOfSingleItemDict(x)
    x['b'] = 'baz'
    assert 'b' in x
    assert x['b'] == 'baz'


def test_contains():
    x = [{'a': 'foo'}, {'b': 'bar'}]
    x = ListOfSingleItemDict(x)

    assert 'a' in x
    assert 'b' in x


def test_not_contains():
    x = [{'a': 'foo'}, {'b': 'bar'}]
    x = ListOfSingleItemDict(x)

    assert 'c' not in x


def test_shared_memory_new_key():
    x = [{'a': 'foo'}, {'b': 'bar'}]
    y = ListOfSingleItemDict(x)
    y['c'] = 'baz'
    assert len(x) == 3
    assert x[2] == {'c': 'baz'}


def test_shared_memory_overwrite():
    x = [{'a': 'foo'}, {'b': 'bar'}]
    y = ListOfSingleItemDict(x)
    y['a'] = 'baz'
    assert x[0] == {'a': 'baz'}
