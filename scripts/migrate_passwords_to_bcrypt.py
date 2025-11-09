#!/usr/bin/env python3
"""
Password Migration Script - Migrate Plain Text Passwords to Bcrypt Hashes
===========================================================================

This script helps migrate from plain text passwords to bcrypt-hashed passwords
for the FX Trading AI system.

USAGE:
    python scripts/migrate_passwords_to_bcrypt.py

SECURITY NOTE:
    This script will generate bcrypt hashes for your passwords and output them
    as environment variable assignments. These should be set in your .env file
    or system environment.

REQUIREMENTS:
    - bcrypt>=4.0.0 (install via: pip install bcrypt)
"""

import bcrypt
import secrets
import sys
import os


def hash_password(password: str) -> str:
    """
    Hash password using bcrypt with 12 rounds.

    Args:
        password: Plain text password

    Returns:
        Bcrypt hash string
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def generate_strong_password(length: int = 32) -> str:
    """
    Generate a cryptographically secure random password.

    Args:
        length: Length of password to generate

    Returns:
        Random password string
    """
    return secrets.token_urlsafe(length)


def generate_jwt_secret() -> str:
    """
    Generate a strong JWT secret (minimum 32 characters).

    Returns:
        Random JWT secret string
    """
    return secrets.token_urlsafe(32)


def main():
    """Main migration function"""

    print("=" * 80)
    print("FX Trading AI - Password Migration to Bcrypt")
    print("=" * 80)
    print()

    # Check if bcrypt is installed
    try:
        import bcrypt
    except ImportError:
        print("ERROR: bcrypt is not installed.")
        print("Please install it with: pip install bcrypt>=4.0.0")
        sys.exit(1)

    print("This script will help you migrate from plain text passwords to bcrypt hashes.")
    print()
    print("OPTIONS:")
    print("1. Migrate existing passwords to bcrypt hashes")
    print("2. Generate new strong passwords with bcrypt hashes")
    print("3. Generate JWT secret")
    print()

    choice = input("Select option (1/2/3): ").strip()

    if choice == "1":
        migrate_existing_passwords()
    elif choice == "2":
        generate_new_passwords()
    elif choice == "3":
        generate_jwt_secret_only()
    else:
        print("Invalid option. Exiting.")
        sys.exit(1)


def migrate_existing_passwords():
    """Migrate existing plain text passwords to bcrypt hashes"""

    print()
    print("MIGRATE EXISTING PASSWORDS")
    print("-" * 80)
    print("Enter your current plain text passwords. They will be hashed with bcrypt.")
    print()

    # Demo user
    demo_password = input("Enter DEMO user password (or press Enter to skip): ").strip()
    demo_hash = hash_password(demo_password) if demo_password else None

    # Trader user
    trader_password = input("Enter TRADER user password (or press Enter to skip): ").strip()
    trader_hash = hash_password(trader_password) if trader_password else None

    # Premium user
    premium_password = input("Enter PREMIUM user password (or press Enter to skip): ").strip()
    premium_hash = hash_password(premium_password) if premium_password else None

    # Admin user
    admin_password = input("Enter ADMIN user password (or press Enter to skip): ").strip()
    admin_hash = hash_password(admin_password) if admin_password else None

    # Generate JWT secret
    jwt_secret = generate_jwt_secret()

    # Display results
    print()
    print("=" * 80)
    print("MIGRATION COMPLETE - Add these to your .env file:")
    print("=" * 80)
    print()

    if demo_hash:
        print(f"DEMO_PASSWORD={demo_hash}")
    if trader_hash:
        print(f"TRADER_PASSWORD={trader_hash}")
    if premium_hash:
        print(f"PREMIUM_PASSWORD={premium_hash}")
    if admin_hash:
        print(f"ADMIN_PASSWORD={admin_hash}")

    print(f"JWT_SECRET={jwt_secret}")
    print()
    print("=" * 80)
    print()
    print("IMPORTANT:")
    print("1. Copy the above environment variables to your .env file")
    print("2. NEVER commit the .env file to version control")
    print("3. Keep these credentials secure and backed up")
    print("4. The bcrypt hashes can be safely used in production")
    print()


def generate_new_passwords():
    """Generate new strong passwords with bcrypt hashes"""

    print()
    print("GENERATE NEW STRONG PASSWORDS")
    print("-" * 80)
    print("This will generate cryptographically secure random passwords.")
    print()

    # Generate passwords
    demo_password = generate_strong_password(24)
    demo_hash = hash_password(demo_password)

    trader_password = generate_strong_password(24)
    trader_hash = hash_password(trader_password)

    premium_password = generate_strong_password(24)
    premium_hash = hash_password(premium_password)

    admin_password = generate_strong_password(32)
    admin_hash = hash_password(admin_password)

    jwt_secret = generate_jwt_secret()

    # Display results
    print()
    print("=" * 80)
    print("NEW PASSWORDS GENERATED - SAVE THESE CREDENTIALS SECURELY!")
    print("=" * 80)
    print()
    print("PLAIN TEXT PASSWORDS (save these in a secure password manager):")
    print("-" * 80)
    print(f"DEMO user:    {demo_password}")
    print(f"TRADER user:  {trader_password}")
    print(f"PREMIUM user: {premium_password}")
    print(f"ADMIN user:   {admin_password}")
    print()
    print("=" * 80)
    print("BCRYPT HASHES (add these to your .env file):")
    print("=" * 80)
    print()
    print(f"DEMO_PASSWORD={demo_hash}")
    print(f"TRADER_PASSWORD={trader_hash}")
    print(f"PREMIUM_PASSWORD={premium_hash}")
    print(f"ADMIN_PASSWORD={admin_hash}")
    print(f"JWT_SECRET={jwt_secret}")
    print()
    print("=" * 80)
    print()
    print("IMPORTANT:")
    print("1. SAVE the plain text passwords in a secure password manager")
    print("2. Copy the bcrypt hashes to your .env file")
    print("3. NEVER commit the .env file to version control")
    print("4. Keep these credentials secure and backed up")
    print()


def generate_jwt_secret_only():
    """Generate only a JWT secret"""

    print()
    print("GENERATE JWT SECRET")
    print("-" * 80)
    print()

    jwt_secret = generate_jwt_secret()

    print("JWT_SECRET generated:")
    print()
    print(f"JWT_SECRET={jwt_secret}")
    print()
    print("Add this to your .env file and restart the server.")
    print()


if __name__ == "__main__":
    main()
