"""Create the first admin account:  python -m app.create_admin "Full Name" email password"""
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit('Usage: python -m app.create_admin "Full Name" email password')
    name, email, password = sys.argv[1], sys.argv[2].strip().lower(), sys.argv[3]
    if len(password) < 8:
        sys.exit("Password must be at least 8 characters")
    with SessionLocal() as db:
        if db.scalar(select(User.user_id).where(User.email == email)):
            sys.exit("A user with that email already exists")
        db.add(
            User(
                full_name=name,
                email=email,
                password_hash=hash_password(password),
                role="admin",
                is_active=True,
                is_approved=True,
            )
        )
        db.commit()
    print(f"Admin {email} created")


if __name__ == "__main__":
    main()
