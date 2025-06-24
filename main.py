from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional, Literal
from fastapi.responses import JSONResponse
import json
import anthropic

# You can replace this with your actual secrets manager in production
import streamlit as st  # Required for `st.secrets["anthropic"]["api_key"]`

app = FastAPI()

# ====================
# Input Schemas
# ====================
class Idea(BaseModel):
    title: str
    description: str

class StartupAnalysis(BaseModel):
    title: str
    description: str
    stage: Literal["IDEATION & PLANNING", "PROTOTYPE DEVELOPMENT", "VALIDATION & ITERATION", "LAUNCH & SCALING", "GROWTH & OPTIMIZATION"]
    burningProblems: List[str]  # Exactly 3 burning problems

class SurveyRequest(BaseModel):
    studyId: str
    surveyPurpose: str
    startupAnalysis: StartupAnalysis  # Required field with title, description, stage and burning problems

# ====================
# Stage-Specific Survey Strategy
# ====================
def get_stage_focus(stage: str) -> dict:
    """Define what each stage should focus on for survey questions"""
    stage_strategies = {
        "IDEATION & PLANNING": {
            "primary_focus": "Problem validation and market need confirmation",
            "question_types": [
                "Problem severity and frequency validation",
                "Current solution gaps and pain points", 
                "Market size and willingness to pay",
                "Competitive landscape awareness"
            ],
            "validation_goal": "Confirm the problems are real and worth solving"
        },
        "PROTOTYPE DEVELOPMENT": {
            "primary_focus": "Solution fit and technical feasibility validation",
            "question_types": [
                "Solution approach validation",
                "Feature priority and core functionality",
                "Technical constraints and requirements",
                "User workflow and interaction patterns"
            ],
            "validation_goal": "Validate the proposed solution addresses the core problems effectively"
        },
        "VALIDATION & ITERATION": {
            "primary_focus": "Product-market fit and user experience optimization",
            "question_types": [
                "Product satisfaction and recommendation likelihood",
                "Usage patterns and adoption barriers",
                "Feature gaps and improvement priorities",
                "Pricing sensitivity and value perception"
            ],
            "validation_goal": "Optimize product-market fit and identify iteration priorities"
        },
        "LAUNCH & SCALING": {
            "primary_focus": "Go-to-market validation and scaling readiness",
            "question_types": [
                "Market positioning and messaging effectiveness",
                "Distribution channel preferences",
                "Scaling bottlenecks and operational challenges",
                "Customer acquisition and retention factors"
            ],
            "validation_goal": "Validate go-to-market strategy and identify scaling challenges"
        },
        "GROWTH & OPTIMIZATION": {
            "primary_focus": "Growth levers and market expansion opportunities",
            "question_types": [
                "Growth constraint identification",
                "Market expansion and new use case validation",
                "Customer lifetime value optimization",
                "Competitive differentiation and moat building"
            ],
            "validation_goal": "Identify growth opportunities and optimize market position"
        }
    }
    return stage_strategies.get(stage, stage_strategies["IDEATION & PLANNING"])

# ====================
# Enhanced Prompt Builder
# ====================
def build_stage_specific_survey_prompt(surveyPurpose: str, startupAnalysis: StartupAnalysis):
    stage_strategy = get_stage_focus(startupAnalysis.stage)
    
    prompt = f"""
You are an expert product researcher helping a founder run a user survey for a startup in the **{startupAnalysis.stage}** stage.

--- Startup Details ---
Title: {startupAnalysis.title}
Description: {startupAnalysis.description}
Current Stage: {startupAnalysis.stage}
Survey Purpose: {surveyPurpose}

--- Critical Burning Problems to Address ---
{chr(10).join([f"{i+1}. {problem}" for i, problem in enumerate(startupAnalysis.burningProblems)])}

--- Stage-Specific Focus ---
Primary Focus: {stage_strategy['primary_focus']}
Validation Goal: {stage_strategy['validation_goal']}

CRITICAL INSTRUCTIONS:
- Generate **exactly 10 questions** that are laser-focused on the 3 burning problems above
- Each question must directly validate assumptions related to these specific problems
- Tailor questions to the **{startupAnalysis.stage}** stage requirements
- Focus on: {stage_strategy['primary_focus']}

Question Distribution Strategy:
- 6 questions directly addressing the 3 burning problems (2 questions per burning problem)
- 2 questions about stage-specific validation needs
- 1 question about user behavior/workflow 
- 1 question about future priorities/concerns

Question Types Based on Stage:
{chr(10).join([f"• {qtype}" for qtype in stage_strategy['question_types']])}

Guidelines:
- Make questions specific to the burning problems, not generic
- Use "scale" for quantitative validation, "text" for qualitative insights
- Avoid multiple choice questions
- Each question should test a specific assumption about the burning problems

Return only a valid JSON array with exactly 10 items, each structured like this:
[
  {{
    "text": "...",
    "bucket": "burning_problem_1" | "burning_problem_2" | "burning_problem_3" | "stage_validation" | "user_behavior" | "future_priorities",
    "type": "scale" | "text",
    "burning_problem_reference": 1 | 2 | 3 | null
  }},
  ...
]
"""
    
    return prompt

# ====================
# Claude 3.5 API Call
# ====================
def query_claude(prompt: str) -> str:
    client = anthropic.Anthropic(api_key=st.secrets["anthropic"]["api_key"])
    model_id = "claude-3-5-haiku-20241022"

    try:
        # Use strict JSON output format
        response = client.messages.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            format="json",
        )
    except TypeError:
        # Fallback if SDK is old  
        response = client.messages.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )

    return response.content[0].text if response.content else ""

# ====================
# Main FastAPI Endpoint
# ====================
@app.post("/api/ai/survey-generator")
async def generate_survey(payload: SurveyRequest):
    # Validate burning problems count
    if len(payload.startupAnalysis.burningProblems) != 3:
        return JSONResponse(content={
            "error": "Exactly 3 burning problems are required",
            "received": len(payload.startupAnalysis.burningProblems),
            "studyId": payload.studyId
        }, status_code=400)
    
    # Generate stage-specific prompt
    prompt = build_stage_specific_survey_prompt(
        payload.surveyPurpose, 
        payload.startupAnalysis
    )
    
    raw_output = query_claude(prompt)

    try:
        parsed = json.loads(raw_output)
        if isinstance(parsed, list) and len(parsed) == 10:
            return JSONResponse(content={
                "questions": parsed,
                "stage": payload.startupAnalysis.stage,
                "burningProblems": payload.startupAnalysis.burningProblems,
                "studyId": payload.studyId,
                "metadata": {
                    "stage_focus": get_stage_focus(payload.startupAnalysis.stage)['primary_focus'],
                    "validation_goal": get_stage_focus(payload.startupAnalysis.stage)['validation_goal']
                }
            })
        else:
            return JSONResponse(content={
                "error": "Output is not a valid list of 10 items",
                "raw": raw_output,
                "studyId": payload.studyId
            }, status_code=200)
    except Exception as e:
        return JSONResponse(content={
            "error": f"Could not parse JSON: {str(e)}",
            "raw_output": raw_output,
            "studyId": payload.studyId
        }, status_code=200)