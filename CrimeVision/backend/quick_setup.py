#!/usr/bin/env python3
"""
Quick setup script for JWT secret key
Run this to generate a secure secret key and create/update your .env file
"""
import os
import secrets
import string
from pathlib import Path

def generate_secret_key():
    """Generate a secure 64-character secret key"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(64))

def main():
    print("🔐 JWT Secret Key Setup")
    print("=" * 30)

    # Generate secret key
    secret_key = generate_secret_key()

    print(f"Generated Secret Key: {secret_key[:20]}...{secret_key[-10:]}")
    print(f"Key Length: {len(secret_key)} characters")

    # Create or update .env file
    env_file = Path('.env')
    env_content = f"SECRET_KEY={secret_key}\n"

    if env_file.exists():
        print("📝 Updating existing .env file...")
        with open(env_file, 'r') as f:
            lines = f.readlines()

        # Update or add SECRET_KEY line
        key_found = False
        for i, line in enumerate(lines):
            if line.startswith('SECRET_KEY='):
                lines[i] = env_content
                key_found = True
                break

        if not key_found:
            lines.append(env_content)

        with open(env_file, 'w') as f:
            f.writelines(lines)
    else:
        print("📝 Creating new .env file...")
        with open(env_file, 'w') as f:
            f.write(env_content)

    print("✅ .env file updated successfully!")
    print("🔄 Restart your FastAPI server to use the new secret key")
    print("⚠️  Keep this key secure and never commit it to version control!")

if __name__ == "__main__":
    main()
