import os
import shutil
import tempfile

import pytest

from app.core.config import Settings, override_settings, reset_settings
from app.core.templates import TemplateRegistry


@pytest.fixture()
def tmp_export_dir():
    d = tempfile.mkdtemp(prefix="fc_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture()
def isolated_settings(tmp_export_dir):
    s = Settings(
        MCP_AUTH_TOKEN="ci-test",
        DOCS_TEMPLATE_PATH=tmp_export_dir,
        OWN_TEMPLATES_PATH=tmp_export_dir,
        FILE_EXPORT_DIR=tmp_export_dir,
        FILE_EXPORT_BASE_URL="http://localhost:9003/files",
        LOG_LEVEL="INFO",
        FILES_DELAY=3600,
        PERSISTENT_FILES=False,
        HTTP_TIMEOUT=5.0,
        OWUI_URL="",
        JWT_SECRET="test-jwt",
    )
    override_settings(s)
    TemplateRegistry.reset()
    yield s
    reset_settings()
    TemplateRegistry.reset()
