import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from antigravity_manager.registry import load_registry, save_registry, update_registry_from_status
from antigravity_manager.status import LiveStatus, ModelQuotaStatus
from datetime import datetime, timezone, timedelta

def test_load_registry_not_exists():
    path = Path("/mock/registry.json")
    with patch("pathlib.Path.exists", return_value=False):
        assert load_registry(path) == {}

def test_load_registry_success():
    path = Path("/mock/registry.json")
    data = {"test@test.com": {"email": "test@test.com"}}
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_text", return_value=json.dumps(data)):
        assert load_registry(path) == data

def test_load_registry_error():
    path = Path("/mock/registry.json")
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_text", side_effect=OSError("err")):
        assert load_registry(path) == {}

def test_load_registry_not_dict():
    path = Path("/mock/registry.json")
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_text", return_value="[]"):
        assert load_registry(path) == {}

def test_save_registry():
    path = MagicMock()
    data = {"test": {"val": 1}}
    save_registry(data, path)
    path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    path.write_text.assert_called_once()

def test_update_registry_from_status():
    dt = datetime(2023, 1, 1, tzinfo=timezone.utc)
    dt2 = dt + timedelta(hours=1)

    m1 = ModelQuotaStatus(model_name="m1", quota_percent_left=100, refresh_in_text=None, refresh_at=None, is_available=True)
    m2 = ModelQuotaStatus(model_name="m2", quota_percent_left=0, refresh_in_text="1h", refresh_at=dt2, is_available=False)

    status = LiveStatus(
        email="test@test.com",
        plan="premium",
        is_pro=True,
        captured_at=dt,
        models=tuple([m1, m2])
    )

    with patch("antigravity_manager.registry.load_registry", return_value={}), \
         patch("antigravity_manager.registry.save_registry") as mock_save:

        update_registry_from_status(status, dry_run=False)

        assert mock_save.call_count == 1
        saved_data = mock_save.call_args[0][0]
        assert "test@test.com" in saved_data

        record = saved_data["test@test.com"]
        assert record["email"] == "test@test.com"
        assert record["plan"] == "premium"
        assert record["is_pro"] is True
        assert record["next_available_at"] == dt2.isoformat()

def test_update_registry_from_status_dry_run():
    dt = datetime(2023, 1, 1, tzinfo=timezone.utc)
    status = LiveStatus(
        email="test@test.com",
        plan="premium",
        is_pro=True,
        captured_at=dt,
        models=tuple([])
    )
    with patch("antigravity_manager.registry.load_registry", return_value={}), \
         patch("antigravity_manager.registry.save_registry") as mock_save:

        update_registry_from_status(status, dry_run=True)
        mock_save.assert_not_called()
