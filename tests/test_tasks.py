"""The authored slice tasks load and point at real, hashable datasets."""

from __future__ import annotations

from statskills.tasks.authored.slice_tasks import AUTHORED_DATA_DIR, load_slice_tasks


def test_data_dir_resolves():
    assert AUTHORED_DATA_DIR.is_dir()


_KINDS = {"numeric", "exact", "categorical", "set", "regex"}


def test_slice_tasks_load_with_existing_datasets():
    tasks = load_slice_tasks()
    assert len(tasks) == 5
    for task in tasks:
        assert task.expected is not None and task.expected.kind in _KINDS
        assert task.verifier == "closed_form"
        for dataset in task.datasets:
            assert dataset.path.exists(), dataset.path
            assert len(dataset.sha256()) == 64  # content hash for provenance
