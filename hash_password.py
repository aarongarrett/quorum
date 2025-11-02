#!/usr/bin/env python3
"""Quick script to hash a password using Argon2."""
import argon2
import sys

if len(sys.argv) != 2:
    print("Usage: python hash_password.py 'your-password-here'")
    print()
    print("Example:")
    print("  python hash_password.py 'MySecurePassword'")
    sys.exit(1)

password = sys.argv[1]

if len(password) < 6:
    print("❌ Error: Password must be at least 6 characters long")
    sys.exit(1)

# Generate Argon2 hash
ph = argon2.PasswordHasher()
password_hash = ph.hash(password)

print("✅ Password hash generated!")
print()
print("Add this to your .env file:")
print("-" * 80)
print(f"ADMIN_PASSWORD={password_hash}")
print("-" * 80)
