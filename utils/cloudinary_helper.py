"""
utils/cloudinary_helper.py — Cloudinary image upload utility for ICSS

Handles snapshot uploads to Cloudinary with error handling and fallbacks.
"""

import os
import logging
import cv2
import numpy as np
from typing import Optional, Tuple
from datetime import datetime

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Global Cloudinary client
_cloudinary_client = None
_is_available = None


def _init_cloudinary():
    """Initialize Cloudinary client from environment variables"""
    global _cloudinary_client, _is_available
    
    if _is_available is not None:
        return _is_available
    
    try:
        import cloudinary
        import cloudinary.uploader
        
        cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "").strip()
        api_key = os.environ.get("CLOUDINARY_API_KEY", "").strip()
        api_secret = os.environ.get("CLOUDINARY_API_SECRET", "").strip()
        
        if not all([cloud_name, api_key, api_secret]):
            logger.warning("Cloudinary credentials not found in environment")
            _is_available = False
            return False
        
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret
        )
        
        _cloudinary_client = cloudinary
        _is_available = True
        logger.info("Cloudinary client initialized successfully")
        return True
        
    except ImportError:
        logger.warning("Cloudinary package not installed. Install with: pip install cloudinary")
        _is_available = False
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Cloudinary: {e}")
        _is_available = False
        return False


def is_cloudinary_available() -> bool:
    """Check if Cloudinary is properly configured and available"""
    return _init_cloudinary()


def upload_snapshot(
    frame: np.ndarray,
    folder: str = "icss-alerts",
    timestamp: Optional[datetime] = None
) -> Tuple[bool, str]:
    """
    Upload a video frame snapshot to Cloudinary
    
    Args:
        frame: OpenCV frame (numpy array)
        folder: Cloudinary folder name
        timestamp: Optional timestamp for filename
        
    Returns:
        Tuple of (success: bool, url: str)
    """
    if not is_cloudinary_available():
        logger.warning("Cloudinary not available, skipping upload")
        return False, ""
    
    try:
        import cloudinary.uploader
        
        # Generate filename with timestamp
        if timestamp is None:
            timestamp = datetime.now()
        
        filename = f"alert_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
        
        # Convert OpenCV BGR to RGB
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            frame_rgb = frame
        
        # Convert to bytes
        success, encoded_img = cv2.imencode('.jpg', frame_rgb, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            logger.error("Failed to encode frame to JPEG")
            return False, ""
        
        img_bytes = encoded_img.tobytes()
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            img_bytes,
            folder=folder,
            public_id=filename,
            resource_type="image",
            format="jpg",
            quality="auto:good",
            fetch_format="auto"
        )
        
        if result and 'secure_url' in result:
            url = result['secure_url']
            logger.info(f"Snapshot uploaded successfully: {url}")
            return True, url
        else:
            logger.error("Upload response missing secure_url")
            return False, ""
            
    except Exception as e:
        logger.error(f"Failed to upload snapshot to Cloudinary: {e}")
        return False, ""


def get_upload_info() -> dict:
    """Get Cloudinary configuration status"""
    return {
        'available': is_cloudinary_available(),
        'cloud_name': os.environ.get("CLOUDINARY_CLOUD_NAME", "")[:10] + "..." if os.environ.get("CLOUDINARY_CLOUD_NAME") else "",
        'configured': bool(
            os.environ.get("CLOUDINARY_CLOUD_NAME") and 
            os.environ.get("CLOUDINARY_API_KEY") and 
            os.environ.get("CLOUDINARY_API_SECRET")
        )
    }
