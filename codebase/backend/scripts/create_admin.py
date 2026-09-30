"""
Provision an ADMIN account. Admin accounts must never be created through a
public registration endpoint, so this is a standalone CLI script instead of
an API route.

Usage:
    python scripts/create_admin.py --email admin@example.com --phone +10000000000 \
        --full-name "Platform Admin" --password "A-Strong-Password1"

Or set INITIAL_ADMIN_EMAIL / INITIAL_ADMIN_PASSWORD / INITIAL_ADMIN_FULL_NAME
in the environment and run with no arguments.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db, bcrypt
from app.models.user import User, UserRole, UserStatus


def main():
    parser = argparse.ArgumentParser(description="Create an ADMIN user.")
    parser.add_argument("--email", default=os.environ.get("INITIAL_ADMIN_EMAIL"))
    parser.add_argument("--phone", default=os.environ.get("INITIAL_ADMIN_PHONE", ""))
    parser.add_argument("--full-name", default=os.environ.get("INITIAL_ADMIN_FULL_NAME", "Platform Admin"))
    parser.add_argument("--password", default=os.environ.get("INITIAL_ADMIN_PASSWORD"))
    args = parser.parse_args()

    if not args.email or not args.password:
        print("ERROR: --email and --password (or INITIAL_ADMIN_EMAIL / INITIAL_ADMIN_PASSWORD) are required.")
        sys.exit(1)

    app = create_app(os.environ.get("APP_CONFIG", "development"))
    with app.app_context():
        email = args.email.strip().lower()
        if User.query.filter_by(email=email).first():
            print(f"ERROR: a user with email {email} already exists.")
            sys.exit(1)

        admin = User(
            full_name=args.full_name,
            email=email,
            phone=args.phone or None,
            password_hash=bcrypt.generate_hash(args.password),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
        )
        db.session.add(admin)
        db.session.commit()
        print(f"Admin created: {email} (public_id={admin.public_id})")


if __name__ == "__main__":
    main()
