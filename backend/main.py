from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from tools import search_modules, check_prerequisites, NUSModsClient, check_timetable_conflicts
from agent import CourseAgent
import json

app = FastAPI(title="NUS Course Selection Agent API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    taken_modules: List[str] = []
    priorities: str = "balanced"

class ValidateRequest(BaseModel):
    module_code: str
    taken_modules: List[str]

@app.get("/")
def read_root():
    return {"message": "Welcome to the NUS Course Selection Agent API"}

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    agent = CourseAgent(taken_modules=req.taken_modules, priorities=req.priorities)
    chunks = []
    for chunk in agent.chat_stream(req.message):
        chunks.append(chunk)
    return {"response": "".join(chunks)}

@app.post("/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    agent = CourseAgent(taken_modules=req.taken_modules, priorities=req.priorities)
    
    def event_generator():
        for chunk in agent.chat_stream(req.message):
            # SSE format
            yield f"data: {json.dumps({'text': chunk})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/tools/test_llm")
async def test_llm_endpoint(req: ChatRequest):
    """Diagnose the LLM connection."""
    agent = CourseAgent(taken_modules=req.taken_modules, priorities=req.priorities)
    return agent.test_connection()

@app.get("/tools/search")
async def search_endpoint(q: str, limit: int = 10):
    return search_modules(q, limit)

@app.post("/tools/validate")
async def validate_endpoint(req: ValidateRequest):
    details = NUSModsClient.get_module_details(req.module_code)
    if not details:
        raise HTTPException(status_code=404, detail="Module not found")
    
    can_take = check_prerequisites(details.get('prereqTree'), set(req.taken_modules))
    return {
        "module_code": req.module_code,
        "can_take": can_take,
        "prereq_tree": details.get('prereqTree'),
        "prereq_text": details.get('prerequisite')
    }

@app.post("/tools/conflicts")
async def conflicts_endpoint(modules: List[str], semester: int = 1):
    return check_timetable_conflicts(modules, semester)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
