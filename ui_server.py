import os
import json
import requests
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, FileResponse

# Your EXISTING agent on Render (no changes needed there)
AGENT_URL = os.environ.get("AGENT_URL", "https://your-agent.onrender.com").rstrip("/")

app = FastAPI()


def build_input(messages):
    """The /agent route takes one string, so fold recent history into it."""
    recent = messages[-7:]
    if len(recent) == 1:
        return recent[0]["content"]
    lines = []
    for m in recent[:-1]:
        who = "User" if m["role"] == "user" else "Assistant"
        lines.append(f"{who}: {m['content']}")
    history = "\n".join(lines)
    return f"Earlier in this conversation:\n{history}\n\nNew message from the user: {recent[-1]['content']}"


@app.post("/chat")
def chat(body: dict):
    text = build_input(body.get("messages", []))

    def stream():
        try:
            r = requests.post(f"{AGENT_URL}/agent/invoke", json={"input": text}, timeout=120)
            r.raise_for_status()
            answer = r.json().get("output", "")
            if not isinstance(answer, str):
                answer = str(answer)
        except Exception as e:
            answer = f"Could not reach the agent: {e}"
        yield json.dumps({"type": "token", "text": answer}) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@app.get("/")
def home():
    return FileResponse(os.path.join(os.path.dirname(__file__), "agent-ui.html"))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
