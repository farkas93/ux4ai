import os

import pytest
from sqlalchemy import create_engine, text

from aipm_toolkit.db import Base

pytestmark = pytest.mark.postgres


def test_postgres_can_create_foundation_schema():
    url = os.getenv("AIPM_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set AIPM_TEST_DATABASE_URL to run PostgreSQL integration tests")
    engine = create_engine(url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    with engine.connect() as connection:
        assert connection.execute(text("select 1")).scalar_one() == 1
