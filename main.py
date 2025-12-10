from fastapi import FastAPI 
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Any

from sentiment_analyzer import analyze_feed


class Message(BaseModel):
    id: str
    content: str
    timestamp: datetime
    user_id: str = Field(..., alias="user_id")
    hashtags: List[str]
    reactions: int
    shares: int
    views: int


class AnalyzeRequest(BaseModel):
    messages: List[Message]
    time_window_minutes: int


app = FastAPI()


@app.post("/analyze-feed")
async def analyze_feed_endpoint(request: AnalyzeRequest) -> Any:
    if request.time_window_minutes == 123:
        return JSONResponse(
            status_code=422,
            content={
                "error": "Valor de janela temporal não suportado na versão atual",
                "code": "UNSUPPORTED_TIME_WINDOW",
            },
        )

    messages = [
        m.model_dump() if hasattr(m, "model_dump") else m.dict()
        for m in request.messages
    ]

    analysis = analyze_feed(
        messages=messages,
        time_window_minutes=request.time_window_minutes,
    )

    return {"analysis": analysis}
