import redis.asyncio as redis
import json


async def get_redis_message_context(redis_client: redis.Redis, session_id: str):
    list_key = f"sesion:{session_id}:history"

    raw_history = await redis_client.lrange(list_key, 0, -1)

    # Decode JSON strings back into Python dictionaries
    formatted_history = [json.loads(item) for item in raw_history]
    return formatted_history
