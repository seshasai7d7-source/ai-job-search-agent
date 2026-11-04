import ipaddress
import socket

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import Base


@pytest.fixture(autouse=True)
def block_outgoing_sockets(monkeypatch):
    original_socket = socket.socket

    class NetworkDisabledSocket(original_socket):
        @staticmethod
        def _is_loopback(address):
            if not isinstance(address, tuple) or not address:
                return False
            host = address[0]
            try:
                return ipaddress.ip_address(host).is_loopback
            except ValueError:
                return host.lower() == "localhost"

        def connect(self, address):
            if self._is_loopback(address):
                return super().connect(address)
            raise RuntimeError("Network access is disabled during tests.")

        def connect_ex(self, address):
            if self._is_loopback(address):
                return super().connect_ex(address)
            raise RuntimeError("Network access is disabled during tests.")

    monkeypatch.setattr(socket, "socket", NetworkDisabledSocket)


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    test_session = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )
    app.state.test_engine = test_engine

    def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    del app.state.test_engine
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()
