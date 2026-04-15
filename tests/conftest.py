import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def server_module():
    import app.server as server

    return server


@pytest.fixture
def client(server_module):
    return TestClient(server_module.app)


@pytest.fixture
def valid_api_key(server_module):
    return server_module.settings.api_key
