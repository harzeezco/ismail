from ollama import AsyncClient # <-- IMPORTANT: Import the Async client
from fastapi.concurrency import run_in_threadpool
from fastapi import Depends, Response
import os
from pydantic import BaseModel
from fastapi import Response, HTTPException, Depends
from fastapi.responses import StreamingResponse
import ollama
from ai_model.system_prompt import system_prompt
from utils.verify_refresh_session import verify_and_refresh_session
from lib.redis_client import get_redis
import redis.asyncio as redis
from utils.get_session_token import get_session_token
from services.supabase_client import supabase
from starlette.concurrency import run_in_threadpool
from postgrest.exceptions import APIError
from utils.get_redis_message_context import get_redis_message_context
from utils.save_redis_message_context import save_redis_message_context 
import json


class Prompt(BaseModel):
    prompt: str


# Initialize the cloud client outside the function so it can be reused
ollama_cloud_client = AsyncClient(
    host="https://ollama.com",
    headers={'Authorization': f"Bearer {os.environ.get('OLLAMA_API_KEY')}"}
)


async def read_prompt(
    payload: Prompt,
    redis_client: redis.Redis = Depends(get_redis),
    session_id: str = Depends(get_session_token),
):
    await verify_and_refresh_session(session_id, redis_client)
    raw_input = payload.prompt.strip()

    if not raw_input:
        return Response(
            content='{"error": "Prompt cannot be empty"}',
            media_type="application/json",
            status_code=400,
        )

    if len(raw_input) > 500:
        return Response(
            content='{"error": "Prompt is too long"}',
            media_type="application/json",
            status_code=400,
        )

    user_prompt = f"""
        Answer the following question from a portfolio visitor. 
        Remember to strictly use the provided JSON data, keep the answer concise, 
        and format your final response entirely in Markdown.\n\n
        Visitor Question: "{raw_input}"
    """

    chat_history = await get_redis_message_context(redis_client, session_id)

    async def event_generator():
        full_reply = ""
        try:
            # 1. Trigger Ollama stream using the AsyncCloudClient
            response = await ollama_cloud_client.chat(
                model="gpt-oss:20b-cloud",
                messages=[
                    {"role": "system", "content": system_prompt},
                    *chat_history,
                    {"role": "user", "content": user_prompt},
                ],
                options={"temperature": 0.7, "keep_alive": "60m"},
                stream=True
            )

            # 2. Iterate through stream chunks asynchronously
            async for chunk in response:
                token = chunk.get("message", {}).get("content", "")
                if token:
                    full_reply += token
                    yield f"data: {json.dumps({'token': token})}\n\n"

            # 3. Save context to Redis after stream completes
            await save_redis_message_context(redis_client, session_id, raw_input, full_reply)

            # 4. Save to Supabase via thread pool
            def _insert():
                return supabase.table("chat_messages").insert([
                    {
                        "session_id": session_id,
                        "role": "user",
                        "content": raw_input
                    },
                    {
                        "session_id": session_id,
                        "role": "assistant",
                        "content": full_reply
                    }
                ]).execute()

            await run_in_threadpool(_insert)
            yield "data: [DONE]\n\n"

        except Exception as e:
            # If Ollama fails, or DB fails, it gets caught and streamed here
            print(f"CRITICAL ERROR: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    # Return a Server-Sent Events (SSE) streaming response
    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def get_messages(session_id: str = Depends(get_session_token)):
    try:
        response = supabase.table("chat_messages").select("role, content, created_at").eq(
            "session_id", session_id).order("created_at", desc=False).execute()

        if not response.data:
            return {"history": [], "message": "No prior chat history found for this session."}

        return {
            "history": response.data
        }

    except APIError as db_error:
        print(f"Supabase API Error for session {session_id}: {db_error.message}")
        raise HTTPException(
            status_code=400,
            detail=f"Database query failed: {db_error.message}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Failed to load chat history.")