import os

from app.core.models import ArchiveFormat, ExportFormat


def test_export_format_text_formats():
    assert ExportFormat.TXT in ExportFormat.text_formats()
    assert ExportFormat.CSV not in ExportFormat.text_formats()


def test_export_format_table_formats():
    assert ExportFormat.CSV in ExportFormat.table_formats()
    assert ExportFormat.XLSX in ExportFormat.table_formats()


def test_export_format_document_formats():
    assert ExportFormat.DOCX in ExportFormat.document_formats()
    assert ExportFormat.PDF in ExportFormat.document_formats()


def test_archive_format_values():
    assert ArchiveFormat.ZIP == "zip"
    assert ArchiveFormat.TAR_GZ == "tar.gz"


def test_is_safe_path_blocks_traversal(isolated_settings, tmp_export_dir):
    from storage.paths import is_safe_path
    # inside export dir is safe
    assert is_safe_path(os.path.join(tmp_export_dir, "file.txt")) is True
    # outside is not
    assert is_safe_path("/tmp/evil.txt") is False
    assert is_safe_path(os.path.join(tmp_export_dir, "..", "evil.txt")) is False


def test_resolve_output_path_adds_ext(isolated_settings, tmp_export_dir):
    from storage.paths import resolve_output_path
    folder = tmp_export_dir
    path, name = resolve_output_path(folder, "report", "docx")
    assert name == "report.docx"
    assert path.endswith("report.docx")


def test_public_url(isolated_settings):
    from storage.paths import public_url
    url = public_url("/tmp/file-converter-test/export_abc", "report.docx")
    assert url == "http://localhost:9003/files/export_abc/report.docx"


def test_new_export_folder_creates_dir(isolated_settings):
    from storage.paths import new_export_folder
    folder = new_export_folder()
    assert os.path.isdir(folder)
