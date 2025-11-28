from fastapi import FastAPI, Request, Response
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from google.genai.chats import GenerateContentResponse
from uuid import uuid4
from gemini import SessionStorage, validator
from models import JudgeResponse, AgentPrompt, AgentResponse
import os

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_storage = SessionStorage(api_key=os.getenv("API_KEY"))

@app.get("/")
def get_root():
    return {"Hello": "World"}

@app.post("/prompt", response_model=AgentResponse)
async def post_prompt(req: Request, resp: Response, prompt: AgentPrompt):
    session_id = req.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid4())
        resp.set_cookie('session_id', value=session_id, max_age=86400, samesite='lax')

    expert_session = session_storage.get_or_new(
        session_id,
        instructions="""
        You are an expert in quantum computing and programming, and a good teacher and lecturer.
        You have a teaching philosophy similar to Leonard Susskind and Richard Feynman, but you do not oversimplify.
        You think that the student should understand the mathematical explanation behind each concept, such that their understanding is concrete.
        """,
        session_label="expert"
    )

    judge_session = session_storage.get_or_new(
        session_id,
        instructions="""You are a rigorous academic judge specialized in quantum computing and quantum mechanics. Your role is to evaluate AI responses for:
        - IMPORTANT: Relation to quantum computing and quantum mechanics
        - Factual accuracy and scientific validity
        - Clarity and pedagogical effectiveness  
        - Mathematical rigor and proper explanations
        - Absence of oversimplification or misleading analogies
        
        Provide specific, constructive feedback and a quality score (1-10). Ensure the response is related to quantum computing & mechanics, if not, you should score it lower.
        
        CRITICAL: You MUST respond with ONLY a valid JSON object in this exact format:
        {
            "verdict": "APPROVED|REVISE|REJECTED",
            "score": score_as_float,
            "overall_feedback": "Concise summary of assessment",
            "recommended_changes": "Specific instructions for improvement"
        }

        Make sure to escape special characters, and do not include any other text, explanations, or formatting (eg. code block).
        """,
        session_label="judge"
    )

    @validator(id="academic_judge", validates=expert_session, using=judge_session)
    def expert_response_validator(validator_response: GenerateContentResponse, expert_response: GenerateContentResponse, prompt: str):
        parsed_response = JudgeResponse.from_json(validator_response.text)

        match parsed_response.verdict:
            case "APPROVED":
                return None, parsed_response
            case "REVISE":
                return f"""Your response needs revisions based on feedback:

                FEEDBACK:
                - Overall Score: {parsed_response.score}/10
                - Overall Feedback: {parsed_response.overall_feedback}
                - Specific Changes Requested: {parsed_response.recommended_changes}

                Please revise your previous response accordingly while maintaining the core content.
                """, parsed_response
            case "REJECTED":
                return f"""Your response was REJECTED by based on feedback:

                FEEDBACK:
                - Overall Score: {parsed_response.score}/10
                - Overall Feedback: {parsed_response.overall_feedback}
                - Specific Changes Requested: {parsed_response.recommended_changes}

                Please provide a completely new, improved response to: {prompt}
                """, parsed_response

    expert_response, validator_data = expert_session.send_message(message=prompt.message)

    return AgentResponse(
        message=expert_response.text,
        judge_data=validator_data["academic_judge"]
    )