import pytest
from learnloop import flags


@pytest.fixture(autouse=True)
def isolate_flagsmith_client(monkeypatch):
    """Ensure no test leaks or mutates the singleton client or hits real credentials."""
    flags._client = None
    yield
    flags._client = None
