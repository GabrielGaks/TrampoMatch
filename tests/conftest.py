import pytest
from trampomatch import create_app
from trampomatch.extensions import db as _db


@pytest.fixture(scope="session")
def app():
    app = create_app("testing")
    with app.app_context():
        yield app


@pytest.fixture(autouse=True)
def reset_database(app):
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        yield
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    with app.app_context():
        yield _db
        _db.session.rollback()
