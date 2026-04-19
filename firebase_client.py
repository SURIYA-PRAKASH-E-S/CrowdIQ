"""
firebase_client.py — Firebase Realtime Database client for ICSS.

Single source of truth for Firebase Admin SDK initialization.
Provides a get_db() helper that returns the root database reference.
"""

import os
import logging
import firebase_admin
from firebase_admin import credentials, db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Client initialisation (module-level singleton)
# ---------------------------------------------------------------------------

_db_ref = None


def _create_firebase_client():
    """
    Build the Firebase Admin SDK client from environment secrets.
    Returns None (with a warning) when secrets are missing so the rest
    of the app degrades gracefully instead of crashing.
    """
    # Try to load from .env file first
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    # Guard against double-initialization
    if firebase_admin._apps:
        logger.info("Firebase app already initialized")
        return firebase_admin.db.reference("/")

    database_url = os.environ.get("FIREBASE_DATABASE_URL", "").strip()
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()

    if not database_url or not credentials_path:
        logger.warning(
            "FIREBASE_DATABASE_URL or GOOGLE_APPLICATION_CREDENTIALS is not set. "
            "Create a .env file with your credentials or set them as environment variables. "
            "The database tab will be unavailable."
        )
        print("\n=== FIREBASE SETUP REQUIRED ===")
        print("To enable database features:")
        print("1. Copy env_example.txt to .env")
        print("2. Replace placeholder values with your actual Firebase credentials")
        print("3. Download your service account JSON and place it in the project root")
        print("4. Restart the application")
        print("================================\n")
        return None

    # Check if credentials file exists
    if not os.path.exists(credentials_path):
        logger.warning(
            f"Service account file not found at: {credentials_path}"
        )
        print(f"\n=== SERVICE ACCOUNT FILE NOT FOUND ===")
        print(f"Expected file: {credentials_path}")
        print("Download your service account JSON from Firebase Console:")
        print("1. Go to Firebase Console → Project Settings → Service Accounts")
        print("2. Click 'Generate New Private Key'")
        print("3. Save the JSON file as firebase-service-account.json in the project root")
        print("================================\n")
        return None

    try:
        cred = credentials.Certificate(credentials_path)
        firebase_admin.initialize_app(cred, {
            'databaseURL': database_url
        })
        logger.info("Firebase Admin SDK initialized successfully")
        return firebase_admin.db.reference("/")
    except Exception as exc:
        logger.error("Failed to initialize Firebase Admin SDK: %s", exc)
        return None


def get_db():
    """
    Get the Firebase Realtime Database root reference.
    Returns None if Firebase is not configured.
    """
    global _db_ref
    
    if _db_ref is None:
        _db_ref = _create_firebase_client()
    
    return _db_ref


def is_connected() -> bool:
    """Return True if the Firebase client was initialised successfully."""
    return get_db() is not None
