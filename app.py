from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uuid
from agent import run_graph  # Import from the LangGraph file

app = FastAPI()

app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")


# In-memory session storage
session_store = {}

class ChatRequest(BaseModel):
    thread_id: str
    message: str

@app.post("/chat")
def chat_endpoint(chat_data: ChatRequest):
    thread_id = chat_data.thread_id
    print("hi")
    # If thread_id is not provided, generate one
    if not thread_id or thread_id not in session_store:
        thread_id = str(uuid.uuid4())
        session_store[thread_id] = thread_id  # Store session
    
    response = run_graph(chat_data.message, thread_id)
    return {"thread_id": thread_id, "response": response}

@app.get("/")
def root():
    return FileResponse("index.html")