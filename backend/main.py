"""
FastAPI server — thin routing layer.
"""

import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, List, Optional

from agent import CourseAgent

app = FastAPI(title="NUS Course Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = CourseAgent()


class ChatRequest(BaseModel):
    message: str
    profile: Dict = {}
    history: List[Dict] = []


@app.get("/")
def root():
    return {"status": "ok", "service": "NUS Course Agent"}


@app.get("/health")
def health():
    return agent.test_connection()


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    def event_generator():
        for event in agent.stream_chat(req.message, req.profile, req.history):
            event_type = event.get("event", "unknown")
            data = event.get("data", {})
            yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
