import os

os.environ.setdefault("APP_CONFIG", "testing")

import pytest

from app import create_app
from app.extensions import db as _db, bcrypt
from app.models.user import User, UserRole, UserStatus


@pytest.fixture()
def app():
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        # Phase 7: app/rbac/service.py seeds admin permissions/roles lazily
        # on first use (the same get-or-create convention as Phase 6's
        # NotificationTemplate), but tests build scoped-admin fixtures by
        # querying AdminRole directly (see _make_scoped_admin below)
        # before any of those lazy call sites necessarily runs - seed
        # explicitly here so those fixtures always find their role.
        from app.rbac.service import ensure_seeded

        ensure_seeded()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def db(app):
    return _db


@pytest.fixture()
def client(app):
    return app.test_client()


def _make_user(db, email, phone, password, role, status=UserStatus.ACTIVE, full_name="Test User"):
    user = User(
        full_name=full_name,
        email=email,
        phone=phone,
        password_hash=bcrypt.generate_hash(password),
        role=role,
        status=status,
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def make_user(db):
    return lambda **kwargs: _make_user(db, **kwargs)


@pytest.fixture()
def customer(db):
    return _make_user(db, "customer@example.com", "+10000000001", "Password123", UserRole.CUSTOMER, full_name="Cara Customer")


@pytest.fixture()
def vendor(db):
    return _make_user(db, "vendor@example.com", "+10000000002", "Password123", UserRole.VENDOR, full_name="Vic Vendor")


@pytest.fixture()
def vendor2(db):
    return _make_user(db, "vendor2@example.com", "+10000000012", "Password123", UserRole.VENDOR, full_name="Vera Vendor2")


@pytest.fixture()
def customer2(db):
    return _make_user(db, "customer2@example.com", "+10000000011", "Password123", UserRole.CUSTOMER, full_name="Chris Customer2")


@pytest.fixture()
def rider(db):
    return _make_user(db, "rider@example.com", "+10000000003", "Password123", UserRole.RIDER, full_name="Remy Rider")


@pytest.fixture()
def rider2(db):
    return _make_user(db, "rider2@example.com", "+10000000013", "Password123", UserRole.RIDER, full_name="Rae Rider2")


@pytest.fixture()
def rider3(db):
    return _make_user(db, "rider3@example.com", "+10000000014", "Password123", UserRole.RIDER, full_name="Ray Rider3")


@pytest.fixture()
def admin(db):
    return _make_user(db, "admin@example.com", "+10000000004", "Password123", UserRole.ADMIN, full_name="Adele Admin")


def _make_scoped_admin(db, email, phone, full_name, role_name):
    from app.models.admin_role import AdminRole

    user = _make_user(db, email, phone, "Password123", UserRole.ADMIN, full_name=full_name)
    role = AdminRole.query.filter_by(name=role_name).first()
    user.admin_role_id = role.id
    db.session.commit()
    return user


@pytest.fixture()
def support_agent(db):
    return _make_scoped_admin(db, "agent@example.com", "+10000000020", "Sam Agent", "SUPPORT_AGENT")


@pytest.fixture()
def operations_admin(db):
    return _make_scoped_admin(db, "ops@example.com", "+10000000021", "Olive Ops", "OPERATIONS_ADMIN")


@pytest.fixture()
def finance_admin(db):
    return _make_scoped_admin(db, "financeadmin@example.com", "+10000000022", "Fay Finance", "FINANCE_ADMIN")


@pytest.fixture()
def moderator(db):
    return _make_scoped_admin(db, "moderator@example.com", "+10000000023", "Mo Derator", "MODERATOR")


@pytest.fixture()
def analyst(db):
    return _make_scoped_admin(db, "analyst@example.com", "+10000000024", "Ana Lyst", "ANALYST")


@pytest.fixture()
def super_admin(db):
    return _make_scoped_admin(db, "superadmin@example.com", "+10000000025", "Sue PerAdmin", "SUPER_ADMIN")


def auth_headers(client, identifier, password="Password123"):
    resp = client.post("/api/v1/auth/login", json={"identifier": identifier, "password": password})
    token = resp.get_json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def login_as():
    def _login(client, identifier, password="Password123"):
        return auth_headers(client, identifier, password)

    return _login
