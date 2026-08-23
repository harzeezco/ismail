from pydantic import BaseModel
from fastapi.responses import JSONResponse
import os
import httpx
from dotenv import load_dotenv
from datetime import datetime, timezone
from dateutil import parser
import secrets
import redis.asyncio as redis
from fastapi import Depends
from lib.redis_client import get_redis

session_token = secrets.token_hex(32)

load_dotenv()


class Trunstile(BaseModel):
    trunstile_token: str


async def session(data: Trunstile, redis_client: redis.Redis = Depends(get_redis)):
    if not data.trunstile_token:
        return {
            "success": False,
            "message": "A token must be send"
        }

    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

    payload = {
        "secret": os.getenv("TURNSTILE_SECRET_KEY"),
        "response": data.trunstile_token
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=payload, timeout=4.0)

    cf_data = response.json()
    challenge = cf_data.get("challenge_ts")

    if challenge:
        current_time = datetime.now(timezone.utc)
        challenge_time = parser.parse(challenge)

        newTime = (current_time - challenge_time).total_seconds()

        if newTime > 300:
            return JSONResponse(
                status_code=403,
                content={
                    "status": False,
                    "message": "Token expired, Try again!"
                })

    if cf_data.get("success") is False:
        return JSONResponse(
            status_code=403,
            content={
                "status": False,
                "message": "Verification Failed"
            }
        )

    await redis_client.setex(
        name=f"session:{session_token}",
        time=3500,
        value="active"
    )

    return {
        "token": session_token
    }
