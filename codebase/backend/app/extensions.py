"""
Extension instances, created here (unbound) and initialized against the app
in the application factory. Keeping them in one module avoids circular
imports between models/, auth/, users/, etc.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import bcrypt as bcrypt_lib

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()
limiter = Limiter(key_func=get_remote_address)


class Bcrypt:
    """Thin wrapper so the rest of the app depends on `extensions.bcrypt`
    rather than importing the bcrypt package directly everywhere."""

    def __init__(self, rounds: int = 12):
        self.rounds = rounds

    def init_app(self, app):
        self.rounds = app.config.get("BCRYPT_LOG_ROUNDS", 12)

    def generate_hash(self, plain_text: str) -> str:
        salt = bcrypt_lib.gensalt(rounds=self.rounds)
        return bcrypt_lib.hashpw(plain_text.encode("utf-8"), salt).decode("utf-8")

    def verify(self, plain_text: str, hashed: str) -> bool:
        try:
            return bcrypt_lib.checkpw(plain_text.encode("utf-8"), hashed.encode("utf-8"))
        except (ValueError, TypeError):
            return False


bcrypt = Bcrypt()
