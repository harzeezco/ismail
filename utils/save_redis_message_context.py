import redis.asyncio as redis
import json


async def save_redis_message_context(redis_client: redis.Redis, session_id: str, user_msg: str, assistant_msg: str):
    list_key = f"sesion:{session_id}:history"

    user_entry = json.dumps({"role": "user", "content": user_msg})
    assistant_entry = json.dumps(
        {"role": "assistant", "content": assistant_msg})
    
    await redis_client.rpush(list_key, user_entry, assistant_entry)
    
    await redis_client.ltrim(list_key, -6, -1)
    
    await redis_client.expire(list_key, 3600)
