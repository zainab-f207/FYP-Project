#!/usr/bin/env python3
"""Test script to check if all imports work correctly"""

import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

try:
    print("Testing imports...")

    # Test basic imports
    from fastapi import FastAPI
    print("✓ FastAPI import successful")

    from pydantic import BaseModel
    print("✓ Pydantic import successful")

    import mysql.connector
    print("✓ MySQL connector import successful")

    # Test auth imports
    from auth_updated import verify_password, get_password_hash, create_access_token, verify_token
    print("✓ Auth imports successful")

    # Test helpers import (this might be the problematic one)
    from crime_risk_model.utils.helpers import engineer_features, interpret_clusters, assign_individual_risk_levels, load_model, load_risk_mapping
    print("✓ Helpers import successful")

    print("\n✅ All imports successful!")

except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
