import os

from storage.cleanup import cleanup_old_folders


def test_write_text_and_list_and_delete(isolated_settings, tmp_export_dir):
    from storage.files import write_text, list_folder, delete_file

    ref = write_text("hello", "greeting.txt", "txt")
    assert os.path.exists(ref.path)
    assert ref.name == "greeting.txt"

    folder = os.path.dirname(ref.path)
    items = list_folder(folder)
    assert any(i["name"] == "greeting.txt" for i in items)

    delete_file(ref.path)
    assert not os.path.exists(ref.path)


def test_cleanup_old_folders(isolated_settings, tmp_export_dir):
    import time
    from storage.paths import new_export_folder

    folder = new_export_folder()
    # make it look old
    old_time = time.time() - 7200
    os.utime(folder, (old_time, old_time))

    stats = cleanup_old_folders(max_age_seconds=3600)
    assert stats["deleted"] >= 1
    assert not os.path.exists(folder)


def test_is_safe_path_edge_cases(isolated_settings, tmp_export_dir):
    from storage.paths import is_safe_path

    assert is_safe_path(tmp_export_dir) is True
    assert is_safe_path(os.path.join(tmp_export_dir, "a", "b.txt")) is True
    assert is_safe_path("/etc/passwd") is False
