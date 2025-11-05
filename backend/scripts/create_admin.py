"""Create admin user."""
import sys
import os
from getpass import getpass

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import User, UserRole
from auth import get_password_hash


def create_admin_user():
    """Create an admin user interactively."""
    print("🔐 Create Admin User")
    print("-" * 40)

    email = input("Admin Email: ").strip()
    if not email:
        print("❌ Email is required")
        return False

    full_name = input("Full Name: ").strip()

    password = getpass("Password: ")
    password_confirm = getpass("Confirm Password: ")

    if password != password_confirm:
        print("❌ Passwords do not match")
        return False

    if len(password) < 8:
        print("❌ Password must be at least 8 characters")
        return False

    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"❌ User with email {email} already exists")
            return False

        # Create admin user
        admin_user = User(
            email=email,
            full_name=full_name,
            role=UserRole.ADMIN,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_verified=True
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        print("\n✅ Admin user created successfully!")
        print(f"   ID: {admin_user.id}")
        print(f"   Email: {admin_user.email}")
        print(f"   Role: {admin_user.role}")

        return True

    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = create_admin_user()
    sys.exit(0 if success else 1)
