import streamlit as st
import json
import anthropic
from typing import List, Literal
from pydantic import BaseModel, ValidationError
import os

# ====================
# Load API Key from Streamlit secrets
# ====================
api_key = st.secrets["ANTHROPIC_API_KEY"]

if not api_key:
    st.error("❌ ANTHROPIC_API_KEY not found in Streamlit secrets")
    st.stop()

# ====================
# Pydantic Models
# ====================
class StartupAnalysis(BaseModel):
    title: str
    description: str
    stage: Literal["IDEATION & PLANNING", "PROTOTYPE DEVELOPMENT"]
    burningProblems: List[str]

# ====================
# Guardrails with Descriptions
# ====================
IDEATION_GUARDRAILS = [
    ("PROBLEM RELEVANCE", "Checks whether the target user faces the problem the product solves. Helps reveal frequency & intensity of the problem."),
    ("PROBLEM AWARENESS", "Measures if users know they have this problem. Distinguishes latent vs obvious problems."),
    ("CURRENT SOLUTIONS", "Understand what users currently use to solve the problem. Reveals competition and workarounds."),
    ("WILLINGNESS TO PAY", "Measures if users value the solution enough to pay or switch. Gauges monetization potential."),
    ("TARGET USER FIT", "Confirms if the respondent matches the intended persona. Ensures relevance of data."),
    ("OUTCOME EXPECTATION", "Understand the result users hope to achieve. Clarifies value proposition."),
    ("DEMOGRAPHIC FIT", "Captures job, location, age, behavior, etc. Useful for segmentation."),
    ("MARKET TIMING SENSITIVITY", "Whether users feel this is the right time for the solution. Signals market readiness.")
]

PROTOTYPE_GUARDRAILS = [
    ("WILLINGNESS TO PAY", "Measures if users value the solution enough to pay or switch. Gauges monetization potential."),
    ("TARGET USER FIT", "Confirms if the respondent matches the intended persona. Ensures relevance of data."),
    ("FEATURE PRIORITY", "Identifies which features matter most to the user. Prioritizes MVP scope."),
    ("FREQUENCY OF USE", "How often the product would be used. Estimates stickiness and utility."),
    ("ADOPTION BARRIERS", "What might stop the user from trying the product. Uncovers friction or confusion."),
    ("OUTCOME EXPECTATION", "Understand the result users hope to achieve. Clarifies value proposition."),
    ("DEMOGRAPHIC FIT", "Captures job, location, age, behavior, etc. Useful for segmentation."),
    ("REFERRAL LIKELIHOOD", "Whether users would tell others about the product. Measures viral potential.")
]

def get_guardrails_for_stage(stage: str):
    if stage == "IDEATION & PLANNING":
        return IDEATION_GUARDRAILS
    elif stage == "PROTOTYPE DEVELOPMENT":
        return PROTOTYPE_GUARDRAILS
    else:
        return []

# ====================
# Prompt Builder
# ====================
def build_guardrail_based_prompt(surveyPurpose: str, startupAnalysis: StartupAnalysis):
    guardrails = get_guardrails_for_stage(startupAnalysis.stage)
    guardrail_section = "\n".join([f"- {g[0]}: {g[1]}" for g in guardrails])

    prompt = f"""
You are a user researcher creating a 10-question survey designed to validate assumptions for a startup in the **{startupAnalysis.stage}** stage.

--- Startup Overview ---
Title: {startupAnalysis.title}
Description: {startupAnalysis.description}
Stage: {startupAnalysis.stage}
Survey Purpose: {surveyPurpose}

--- Burning Problems to Validate ---
{chr(10).join([f"{i+1}. {p}" for i, p in enumerate(startupAnalysis.burningProblems)])}

--- Guardrail Categories and Goals ---
{guardrail_section}

INSTRUCTIONS:
- Generate **exactly 10 customer-facing questions** based on the above problems and guardrails
- Each question must test a real-world assumption that a user (not the founder) can answer
- Use a mix of **scale** and **text** questions
- Include questions for all burning problems (2 per problem)
- Include additional questions covering **guardrails**, especially ones not covered by problems
- Prioritize actionable learning over generic opinion
- If necessary, use references beyond just the provided problems to create insightful questions

Return only valid JSON in the following format:
[
  {{
    "text": "...",
    "bucket": "burning_problem_1" | "burning_problem_2" | "burning_problem_3" | "guardrail:<guardrail_name>",
    "type": "scale" | "text",
    "burning_problem_reference": 1 | 2 | 3 | null
  }},
  ...
]
"""
    return prompt.strip()

# ====================
# Claude API Call
# ====================
def query_claude(prompt: str) -> str:
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000
        )
        return response.content[0].text.strip() if response.content else ""
    except Exception as e:
        st.error(f"❌ Claude API Error: {e}")
        return ""

# ====================
# Streamlit App UI
# ====================
st.title("🧠 Outlaw Survey Generator (Guardrail-Based)")

with st.form("survey_form"):
    study_id = st.text_input("Study ID", "sample_study_vapi")
    purpose = st.text_input("Survey Purpose", "Understand user need, pain intensity, and feature expectation")
    title = st.text_input("Startup Title", "Vapi")
    description = st.text_area("Startup Description", "Vapi is a developer-first platform that simplifies the creation, testing, and deployment of voice AI agents. It enables real-time voice orchestration, function calling, and text-to-speech generation for building conversational AI experiences across industries.")
    stage = st.selectbox("Startup Stage", ["IDEATION & PLANNING", "PROTOTYPE DEVELOPMENT"])

    burning_1 = st.text_input("Burning Problem 1", "Developers spend too much time building voice AI agents from scratch")
    burning_2 = st.text_input("Burning Problem 2", "Existing tools lack real-time orchestration and integration flexibility")
    burning_3 = st.text_input("Burning Problem 3", "There's no seamless way to combine voice analytics with function-calling in custom flows")

    submitted = st.form_submit_button("Generate Survey")

    if submitted:
        try:
            input_obj = StartupAnalysis(
                title=title,
                description=description,
                stage=stage,
                burningProblems=[burning_1, burning_2, burning_3]
            )
            prompt = build_guardrail_based_prompt(purpose, input_obj)
            raw_output = query_claude(prompt)

            try:
                parsed = json.loads(raw_output)
                st.success("✅ Survey questions generated!")
                st.json(parsed)
            except Exception as parse_error:
                st.error("❌ Failed to parse output as JSON. Here's the raw output:")
                st.code(raw_output)
        except ValidationError as ve:
            st.error(f"Input Validation Failed: {ve}")
