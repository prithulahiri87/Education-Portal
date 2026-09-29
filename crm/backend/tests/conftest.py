import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["CRM_API_TOKEN"] = ""
os.environ["SEED_ON_START"] = "0"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, get_engine
from app.main import app


@pytest.fixture()
def client():
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as test_client:
        yield test_client
