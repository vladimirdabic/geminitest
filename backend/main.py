from fastapi import FastAPI, Request, Response
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
#from google.genai import types
from uuid import uuid4
from session import SessionStorage, JudgeResponse, AgentPrompt, AgentResponse
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

client = genai.Client(api_key=os.getenv("API_KEY"))
session_storage = SessionStorage(client=client)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/prompt", response_model=AgentResponse)
def update_item(req: Request, resp: Response, prompt: AgentPrompt):
    session_id = req.cookies.get("session_id")
    if not session_id:
        resp.set_cookie('session_id', value=str(uuid4()), max_age=86400, samesite='lax')

    expert_session = session_storage.get_or_new(
        session_id,
        instructions="""
        You are an expert in quantum computing and programming, and a good teacher and lecturer.
        You have a teaching philosophy similar to Leonard Susskind and Richard Feynman, but you do not oversimplify.
        You think that the student should understand the mathematical explanation behind each concept, such that their understanding is concrete.
        """,
        agent_type="expert"
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
        agent_type="judge"
    )

    # Prosledi odgovor od prvog na drugi
    expert_response = expert_session.chat.send_message(message=prompt.message)
    judge_response = judge_session.chat.send_message(message=f"""
        Evaluate this expert response to the user's question:
        
        USER QUESTION: {prompt.message}
        EXPERT RESPONSE: {expert_response.text}
        
        Provide specific, constructive feedback and a quality score in the JSON object you were instructed to.
    """)

    parsed_response = JudgeResponse.from_json(judge_response.text)

    match parsed_response.verdict:
        case "APPROVED":
            pass
        case "REVISE":
            expert_response = expert_session.chat.send_message(
                message=f"""Your response needs revisions based on feedback:

                FEEDBACK:
                - Overall Score: {parsed_response.score}/10
                - Overall Feedback: {parsed_response.overall_feedback}
                - Specific Changes Requested: {parsed_response.recommended_changes}

                Please revise your previous response accordingly while maintaining the core content.
                """
            )
        case "REJECTED":
            expert_response = expert_session.chat.send_message(
                message=f"""Your response was REJECTED by based on feedback:

                FEEDBACK:
                - Overall Score: {parsed_response.score}/10
                - Overall Feedback: {parsed_response.overall_feedback}
                - Specific Changes Requested: {parsed_response.recommended_changes}

                Please provide a completely new, improved response to: {prompt.message}
                """
            )

    return AgentResponse(
        message=expert_response.text,
        judge_data=parsed_response
    )