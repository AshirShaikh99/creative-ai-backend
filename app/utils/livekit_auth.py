import jwt
import time
from typing import Dict, Any, Optional
from app.config.config import get_settings

settings = get_settings()


def create_livekit_token(
    user_id: str,
    room_name: str,
    metadata: Optional[Dict[str, Any]] = None,
    can_publish: bool = True,
    can_subscribe: bool = True,
    ttl: int = 3600,  # 1 hour in seconds
) -> str:
    """
    Generate a JWT token for LiveKit authentication.
    
    Args:
        user_id: Unique identifier for the user
        room_name: Name of the LiveKit room
        metadata: Additional metadata to include in the token
        can_publish: Whether the user can publish media
        can_subscribe: Whether the user can subscribe to others' media
        ttl: Token time-to-live in seconds
        
    Returns:
        JWT token string
    """
    current_time = int(time.time())
    
    payload = {
        "iss": settings.LIVEKIT_API_KEY,  # Issuer
        "sub": user_id,  # Subject (participant identity)
        "jti": f"{room_name}:{user_id}",  # JWT ID
        "nbf": current_time,  # Not Before
        "exp": current_time + ttl,  # Expiration Time
        "video": {
            "room": room_name,
            "roomJoin": True,
            "canPublish": can_publish,
            "canSubscribe": can_subscribe,
        }
    }
    
    if metadata:
        payload["metadata"] = metadata
    
    token = jwt.encode(
        payload,
        settings.LIVEKIT_API_SECRET,
        algorithm="HS256"
    )
    
    return token
