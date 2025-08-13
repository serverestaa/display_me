# routers/linkedin_apply.py
from uuid import uuid4
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Depends
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
import os
from typing import AsyncGenerator
from pydantic import BaseModel
from tasks.apply import enqueue_apply_task  # Celery producer
from utils import get_current_user  

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis = Redis.from_url(REDIS_URL, decode_responses=True)

router = APIRouter(prefix="/linkedin", tags=["linkedin"])

class ApplyResponse(BaseModel):
    task_id: str
    status: str = "queued"

@router.post("/apply", response_model=ApplyResponse)
async def start_apply(
    title: str = Form(...),
    resume: UploadFile = File(...),
    user=Depends(get_current_user),
):
    task_id = str(uuid4())
    pdf_path = Path("static/resumes")
    pdf_path.mkdir(parents=True, exist_ok=True)
    file_on_disk = pdf_path / f"{task_id}.pdf"
    file_on_disk.write_bytes(await resume.read())

    enqueue_apply_task.delay(task_id, str(file_on_disk), title, user.id)
    return {"task_id": task_id}

@router.get("/apply/{task_id}/events")
async def sse_progress(task_id: str) -> StreamingResponse:
    async def event_stream() -> AsyncGenerator[str, None]:
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"progress:{task_id}")
        try:
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    yield f"data: {msg['data']}\n\n"
        finally:
            await pubsub.unsubscribe(f"progress:{task_id}")
    return StreamingResponse(event_stream(), media_type="text/event-stream")
