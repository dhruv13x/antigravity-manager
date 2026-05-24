from datetime import datetime

from antigravity_manager.registry import load_registry, save_registry, update_registry_from_status
from antigravity_manager.status import LiveStatus


def test_registry(tmp_path, monkeypatch):
    rpath = tmp_path / "r.json"
    rpath.write_text("{}")
    monkeypatch.setattr("antigravity_manager.registry.COOLDOWN_REGISTRY_PATH", rpath)

    save_registry({"a": {}})
    assert "a" in load_registry()

    st = LiveStatus(email="b", plan="free", is_pro=False, captured_at=datetime.now(), models=())
    update_registry_from_status(st)
    assert "b" in load_registry()
