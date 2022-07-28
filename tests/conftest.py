# Copyright 2021 MosaicML. All Rights Reserved.

import sys

import pytest

# Add the path of any pytest fixture files you want to make global
pytest_plugins = [
    'tests.yahp_fixtures',
]


@pytest.fixture(autouse=True)
def patch_sys_argv(monkeypatch: pytest.MonkeyPatch):
    """Patch the sys.argv by default to exclude all pytest CLI flags."""
    monkeypatch.setattr(sys, 'argv', [sys.argv[0]])
