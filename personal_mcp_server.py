from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, List
import datetime

app = FastAPI()

# In-memory context store
context_store: Dict[str, List[Dict]] = {}

class ContextItem(BaseModel):
    id: str
    content: str
    metadata: Dict = {}

@app.post("/add_context")
async def add_context(item: ContextItem):
    if item.id not in context_store:
        context_store[item.id] = []
    context_store[item.id].append({
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "role": "system",
        "content": item.content,
        "metadata": item.metadata
    })
    return {"status": "added", "id": item.id}

@app.get("/get_context")
async def get_context(target: str):
    return {"messages": context_store.get(target, [])}

@app.post("/repos/update_context")
async def update_repo_context(data: ContextItem):
    repo_id = f"repo_{data.id}"
    return await add_context(ContextItem(
        id=repo_id,
        content=data.content,
        metadata={"type": "repo_update", **data.metadata}
    ))

@app.get("/status")
async def status():
    return {"status": "ok", "stored_contexts": list(context_store.keys())}
