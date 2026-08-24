from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from controllers.prompt import read_prompt, get_messages
from controllers.auth import session
import redis.asyncio as redis

from dotenv import load_dotenv
import os

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_url = os.getenv("REDIS_URL")

    app.state.redis = redis.from_url(
        redis_url, decode_responses=True)

    yield
    # Safely close the connection pool
    await app.state.redis.aclose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://aesthetic-tiramisu-feb2c3.netlify.app",
                   "https://aesthetic-tiramisu-feb2c3.netlify.app/, https://quadriismail.com", "https://quadriismail.com/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.add_api_route("/session", methods=["POST"], endpoint=session)
app.add_api_route("/prompt", methods=["POST"], endpoint=read_prompt)
app.add_api_route("/chat/history/{session_id}",
                  methods=["GET"], endpoint=get_messages)
