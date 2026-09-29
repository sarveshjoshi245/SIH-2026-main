"""Test suite initialization and fixtures."""
import os
import sys

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.services.electricity_service import ElectricityService
from app.main import app

# Use isolated in-memory or temporary SQLite test DB
TEST_DATABASE_URL = "sqlite:///./test_electricity_department.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_test_database():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    ElectricityService.seed_initial_data(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def interop_headers():
    return {"X-API-Key": "elec_live_interop_key_991"}


@pytest.fixture
def clearance_headers():
    return {"X-API-Key": "elec_live_clearance_key_552"}


@pytest.fixture
def admin_headers():
    return {"X-API-Key": "elec_admin_secret_key_888"}
