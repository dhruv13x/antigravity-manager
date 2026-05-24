import pytest
import os
from unittest.mock import patch
from antigravity_manager.config import _home_from_env

def test_home_from_env():
    with patch.dict(os.environ, {"TEST_ENV": "/tmp/test_dir"}):
        res = _home_from_env("TEST_ENV", "/fallback")
        assert str(res) == "/tmp/test_dir"

def test_home_from_env_fallback():
    with patch.dict(os.environ, clear=True):
        res = _home_from_env("TEST_ENV", "/fallback")
        assert str(res) == "/fallback"

def test_home_from_env_expanduser():
    with patch.dict(os.environ, {"TEST_ENV": "~/test_dir"}), \
         patch("os.path.expanduser", return_value="/home/user/test_dir"):
        res = _home_from_env("TEST_ENV", "/fallback")
        assert str(res) == "/home/user/test_dir"
