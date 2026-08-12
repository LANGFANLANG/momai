import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base


os.environ.setdefault("DATABASE_URL", "sqlite://")


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
