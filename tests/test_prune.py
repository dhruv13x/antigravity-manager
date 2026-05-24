import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from antigravity_manager.prune import build_prune_plan, perform_prune, prune_result_to_text, PrunePlan

def test_build_prune_plan():
    with patch("pathlib.Path.glob") as mock_glob, \
         patch("pathlib.Path.exists") as mock_exists:

        mock_glob.return_value = [Path("/mock/logs.json")]
        mock_exists.return_value = True

        plan = build_prune_plan(Path("/mock"))

        assert len(plan.files) == 3 # 3 patterns
        assert len(plan.directories) == 6 # 6 directory names

def test_perform_prune_not_found():
    args = MagicMock(source_dir="/mock")
    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(FileNotFoundError):
            perform_prune(args)

def test_perform_prune_dry_run():
    args = MagicMock(source_dir="/mock", dry_run=True)
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.is_dir", return_value=True), \
         patch("antigravity_manager.prune.build_prune_plan") as mock_build:

        mock_plan = PrunePlan(files=[], directories=[])
        mock_build.return_value = mock_plan

        result = perform_prune(args)
        assert result == mock_plan

def test_perform_prune_execute():
    args = MagicMock(source_dir="/mock", dry_run=False)

    file_path = MagicMock()
    file_path.exists.return_value = True

    dir_path = MagicMock()
    dir_path.exists.return_value = True
    dir_path.name = "cache"

    mock_plan = PrunePlan(files=[file_path], directories=[dir_path])

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.is_dir", return_value=True), \
         patch("antigravity_manager.prune.build_prune_plan", return_value=mock_plan), \
         patch("shutil.rmtree") as mock_rmtree:

        result = perform_prune(args)
        assert result == mock_plan
        file_path.unlink.assert_called_once()
        mock_rmtree.assert_called_once()

def test_perform_prune_execute_tmp_with_bin():
    args = MagicMock(source_dir="/mock", dry_run=False)

    dir_path = MagicMock()
    dir_path.exists.return_value = True
    dir_path.name = "tmp"

    bin_path = MagicMock()
    bin_path.exists.return_value = True
    dir_path.__truediv__.return_value = bin_path

    item1 = MagicMock(name="bin")
    item1.name = "bin"

    item2 = MagicMock(name="other_dir")
    item2.name = "other_dir"
    item2.is_dir.return_value = True

    item3 = MagicMock(name="other_file")
    item3.name = "other_file"
    item3.is_dir.return_value = False

    dir_path.iterdir.return_value = [item1, item2, item3]

    mock_plan = PrunePlan(files=[], directories=[dir_path])

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.is_dir", return_value=True), \
         patch("antigravity_manager.prune.build_prune_plan", return_value=mock_plan), \
         patch("shutil.rmtree") as mock_rmtree:

        result = perform_prune(args)
        assert result == mock_plan
        mock_rmtree.assert_called_once_with(item2)
        item3.unlink.assert_called_once()

def test_prune_result_to_text():
    plan = PrunePlan(files=[Path("/mock/f1")], directories=[Path("/mock/d1")])
    text = prune_result_to_text(plan, dry_run=True, source_dir=Path("/mock"))
    assert "mode: dry-run" in text
    assert "source_dir: /mock" in text
    assert "files_removed: 1" in text
    assert "directories_removed: 1" in text
