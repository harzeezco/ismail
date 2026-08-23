from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis.asyncio as redis

# This automatically looks for the "Authorization: Bearer <token>" header
security = HTTPBearer()


async def get_session_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    # credentials.credentials automatically extracts just the raw token string!
    token = credentials.credentials
    print(f"Extracted Clean Token: {token}")
    return token
