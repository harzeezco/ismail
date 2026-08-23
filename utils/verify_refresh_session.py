import redis.asyncio as redis
from fastapi import HTTPException, status


async def verify_and_refresh_session(session_id: str | None, redis_client: redis.Redis):

    session_key = f"session:{session_id}"

    exists = await redis_client.exists(session_key)

    if not exists:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please re-initialize."
        )

    await redis_client.expire(session_key, 3600)

    return True
