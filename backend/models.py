from __future__ import annotations
from pydantic import BaseModel
import json

class AgentPrompt(BaseModel):
    message: str

class AgentResponse(BaseModel):
    message: str
    judge_data: JudgeResponse

class JudgeResponse(BaseModel):
    verdict: str
    score: float
    overall_feedback: str
    recommended_changes: str

    @staticmethod
    def from_json(json_string: str) -> JudgeResponse:
        try:
            json_string = json_string.strip()
            if json_string.startswith('```json'):
                json_string = json_string[7:]
            if json_string.endswith('```'):
                json_string = json_string[:-3]
            json_string = json_string.strip()

            raw_data = json.loads(json_string)
            return JudgeResponse(**raw_data)
        except (json.JSONDecodeError, ValueError) as e:
            # Default u slucaju da nije tacan format
            print(json_string)

            return JudgeResponse(
                score=5,
                verdict="APPROVED",
                overall_feedback="Judge response parsing failed",
                recommended_changes="None"
            )