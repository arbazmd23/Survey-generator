# Solution 1: Using python-dotenv (Recommended)
# First install: pip install python-dotenv

import streamlit as st
import json
import anthropic
from typing import List, Literal
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv
import os

# ====================
# Load API Key using python-dotenv
# ====================
load_dotenv()  # This loads the .env file
api_key = os.getenv("ANTHROPIC_API_KEY")

if not api_key:
    st.error("❌ ANTHROPIC_API_KEY not found in .env file")
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
# Detailed Guardrails with Example Questions
# ====================
IDEATION_GUARDRAILS = {
    "PROBLEM RELEVANCE": {
        "description": "Checks whether the target user faces the problem the product solves. Helps reveal frequency & intensity of the problem.",
        "example_questions": [
            "How often do you face [the problem] in your daily or professional life?",
            "On a scale of 1–10, how disruptive is [this problem] to your goals or tasks?",
            "What's the most frustrating part of dealing with [insert problem domain] in your daily routine?",
            "On a scale of 1–5, how important is solving this problem for you right now?",
            "If you had a magic wand, which problem would you fix first? [Option A: Problem the startup solves] [Option B: Another major problem] [Option C: None]",
            "How often does this problem interrupt or slow down your work/life? (1 = Never, 5 = Constantly)",
            "What have you done in the past to try to fix or avoid this problem?",
            "Have you ever wished there was a better solution for this issue? Yes/No?"
        ]
    },
    "PROBLEM AWARENESS": {
        "description": "Measures if users know they have this problem. Distinguishes latent vs obvious problems.",
        "example_questions": [
            "Have you ever actively tried to solve [this problem]?",
            "Before hearing about this solution, how aware were you of [this problem] being an issue for you?",
            "How clearly do you understand the nature of this problem in your own context? (1 = I've never thought about it, 5 = I think about it all the time)",
            "When did you first become aware that this was a problem?",
            "Do you think most people in your role even recognize this as a problem? Yes/No",
            "How much do you feel this issue affects people like you? (1 = Very little, 5 = Very significantly)",
            "How would you describe your awareness of this problem? [I'm very aware] [I've seen it happen but don't think about it] [I didn't realize it was a real issue until now] [I'm not sure it exists]",
            "Can you describe a moment or example when this problem stood out to you?"
        ]
    },
    "CURRENT SOLUTIONS": {
        "description": "Understand what users currently use to solve the problem. Reveals competition and workarounds.",
        "example_questions": [
            "What tools or methods do you currently use to deal with [this problem]?",
            "How satisfied are you with your current way of handling [this problem]?",
            "How are you currently solving this problem today?",
            "What do you currently use? [Excel/Manual methods] [Known competitor] [Internal workaround] [I don't solve it — I tolerate it]",
            "How satisfied are you with your current solution? (1 = Not at all, 5 = Very satisfied)",
            "What's the biggest limitation of your current approach?",
            "Have you ever considered switching to another solution? Yes/No",
            "If something better came along, how likely are you to switch? (1 = Not likely, 5 = Immediately)"
        ]
    },
    "WILLINGNESS TO PAY": {
        "description": "Measures if users value the solution enough to pay or switch. Gauges monetization potential.",
        "example_questions": [
            "If a solution solved this problem completely, would you be willing to pay for it?",
            "What is the maximum you'd consider paying for a solution that addresses this need well?",
            "If a solution truly solved this for you, how much would you pay per month for it? (1 = Nothing, 5 = Premium pricing if it works)",
            "What kind of pricing would feel fair to you for solving this?",
            "Have you paid for any similar tools or services before? Yes/No",
            "Which pricing model would you prefer? [Monthly Subscription] [One-time Payment] [Pay-per-use] [Freemium]",
            "How confident are you that you'd pay for a working solution today? (1 = Not at all, 5 = Very confident)",
            "What would stop you from paying for a solution like this?"
        ]
    },
    "TARGET USER FIT": {
        "description": "Confirms if the respondent matches the intended persona. Ensures relevance of data.",
        "example_questions": [
            "Which best describes your role when encountering [this problem]?",
            "Have you experienced [this problem] in your personal or professional context?",
            "What best describes your role, background, or daily work/life context?",
            "Which of these applies to you? [Student] [Professional] [Founder] [Other: _______]",
            "How closely do you feel this solution is built for someone like you? (1 = Not at all, 5 = Exactly like me)",
            "Do you regularly face the kind of situations this solution addresses? Yes/No",
            "Who else do you know that faces this same problem?",
            "How many people in your circle would also relate to this issue? [Just me] [A few people] [A lot of people I know]"
        ]
    },
    "OUTCOME EXPECTATION": {
        "description": "Understand the result users hope to achieve. Clarifies value proposition.",
        "example_questions": [
            "What would success look like if a product solved this problem for you?",
            "What is the most important result you'd expect from using a product like this?",
            "If this problem was magically solved for you, what would your life/work look like afterward?",
            "How much impact would a working solution make for you? (1 = Minimal, 5 = Game-changing)",
            "What does success look like for you when using a solution to this problem?",
            "What kind of result do you care about most? [Saving time] [Reducing stress] [Saving money] [Improving performance] [Other: ______]",
            "How confident are you that a new product could deliver the outcome you want? (1 = Not at all, 5 = Very confident)",
            "Have you ever tried a tool that failed to meet your expectations? What was missing?"
        ]
    },
    "DEMOGRAPHIC FIT": {
        "description": "Captures job, location, age, behavior, etc. Useful for segmentation.",
        "example_questions": [
            "What is your age group, job role, or industry (if relevant to this context)?",
            "Which category best describes your current situation as it relates to [this product/problem]?",
            "Which of these best describes your role or occupation? [Student] [Working professional] [Entrepreneur] [Freelancer] [Other: ______]",
            "Which city and country are you based in?",
            "How experienced are you in [problem area]? (1 = Newbie, 5 = Very experienced)",
            "What is your age range? [Under 18] [18–24] [25–34] [35–44] [45+]",
            "Do you consider yourself tech-savvy? Yes/No",
            "Briefly describe your work/study background (e.g., design, tech, healthcare, education)."
        ]
    },
    "MARKET TIMING SENSITIVITY": {
        "description": "Whether users feel this is the right time for the solution. Signals market readiness.",
        "example_questions": [
            "Is solving this problem a priority for you this month/quarter/year?",
            "If this product were available today, how soon would you consider trying it?",
            "How urgent is this problem for you right now? (1 = Can wait, 5 = Needs solving immediately)",
            "Why do you think now is the right time for a solution like this?",
            "If this was available today, how soon would you try it? [Immediately] [Within a week] [Eventually] [Never]",
            "Has something changed recently that made this problem worse? Yes/No",
            "Do you think the timing is right for this solution to succeed in the market? (1 = Too early, 5 = Just right)",
            "What would make now the best time to bring this idea to life?"
        ]
    }
}

PROTOTYPE_GUARDRAILS = {
    "WILLINGNESS TO PAY": {
        "description": "Measures if users value the solution enough to pay or switch. Gauges monetization potential.",
        "example_questions": [
            "If this product solved your problem well, how likely are you to pay for it? (1 = Not at all, 5 = Definitely)",
            "What would feel like a fair monthly or one-time price for this product?",
            "Have you paid for similar tools or services before? Yes/No",
            "Which pricing model would you prefer? [Monthly subscription] [One-time fee] [Freemium + premium upgrade] [Pay-per-use]",
            "How confident are you that this product is worth paying for? (1 = Not confident, 5 = Absolutely worth it)",
            "What would make you willing to pay more for this product?",
            "If this product improved [key feature], would you consider upgrading to a paid version? Yes/No",
            "How painful would it be to lose access to this tool once you've used it? (1 = Not at all, 5 = Very painful)"
        ]
    },
    "TARGET USER FIT": {
        "description": "Confirms if the respondent matches the intended persona. Ensures relevance of data.",
        "example_questions": [
            "What do you do professionally (or in daily life)?",
            "Does this product feel like it's designed for someone like you? Yes/No",
            "How well does this solution fit your lifestyle/workflow? (1 = Not at all, 5 = Perfect fit)",
            "Which industry best describes your work? [Tech] [Education] [Healthcare] [Finance] [Other]",
            "How often do you face the problem this product solves?",
            "Do you feel like your use case was clearly considered in the prototype? (1 = Not at all, 5 = Definitely)",
            "Would you be willing to join a user feedback or beta testing group for this product? Yes/No",
            "What's the #1 reason this product does or doesn't feel like it's for you?"
        ]
    },
    "FEATURE PRIORITY": {
        "description": "Identifies which features matter most to the user. Prioritizes MVP scope.",
        "example_questions": [
            "What's the one feature in this product you would not want to lose?",
            "Which feature do you consider absolutely essential? [Feature A] [Feature B] [Feature C] [None of these]",
            "How useful is [specific feature] to your workflow? (1 = Not useful, 5 = Extremely useful)",
            "Rank these features based on importance to you.",
            "If we removed your favorite feature, would you still use this product? Yes/No",
            "Which feature feels unnecessary or overbuilt right now?",
            "How well does the current feature set solve your problem? (1 = Poorly, 5 = Perfectly)",
            "What feature do you wish we had included in this version?"
        ]
    },
    "FREQUENCY OF USE": {
        "description": "How often the product would be used. Estimates stickiness and utility.",
        "example_questions": [
            "How often would you use this tool if it worked perfectly? (1 = Once a year, 5 = Daily)",
            "What type of task would make you return to this product often?",
            "Would this replace any tool or habit you currently use? Yes/No",
            "When would you most likely use this? [Daily task] [Weekly planning] [Monthly project] [Emergency-only]",
            "What would increase your frequency of use?",
            "How much does the product feel like a \"daily tool\" vs. a \"one-off\"? (1 = One-off, 5 = Daily essential)",
            "Would you recommend your team or colleagues use it regularly? Yes/No",
            "What needs to change for this tool to become part of your routine?"
        ]
    },
    "ADOPTION BARRIERS": {
        "description": "What might stop the user from trying the product. Uncovers friction or confusion.",
        "example_questions": [
            "What would prevent you from using this product regularly?",
            "What's the biggest barrier to adoption? [I don't understand it] [Trust issues] [Too expensive] [Doesn't solve my problem fully] [No clear need right now]",
            "How easy was the product to understand and get started with? (1 = Very hard, 5 = Super easy)",
            "Did you feel confident using the product on your own? Yes/No",
            "How likely are you to continue using this after the first try? (1 = Not likely, 5 = Very likely)",
            "What additional help (onboarding, demos, videos) would make you adopt this faster?",
            "What was confusing about the product (if anything)? [Interface] [Features] [Terminology] [Nothing was confusing]",
            "What's one thing we can fix to make adoption frictionless?"
        ]
    },
    "OUTCOME EXPECTATION": {
        "description": "Understand the result users hope to achieve. Clarifies value proposition.",
        "example_questions": [
            "What was the result you expected from using the prototype?",
            "Did this product deliver the outcome you hoped for? Yes/No",
            "How satisfied were you with the end result? (1 = Not at all, 5 = Extremely)",
            "What did the product not do that you expected it to?",
            "What type of value do you expect most from this tool? [Save time] [Save money] [Reduce effort] [Improve output]",
            "How well did this match your mental model of the ideal solution? (1 = Not close, 5 = Spot on)",
            "If we improved one thing to better match your expectations, what would it be?",
            "Would you say the product is effective enough to solve your problem long-term? Yes/No"
        ]
    },
    "DEMOGRAPHIC FIT": {
        "description": "Captures job, location, age, behavior, etc. Useful for segmentation.",
        "example_questions": [
            "What is your age range? [Under 18] [18–24] [25–34] [35–44] [45–54] [55+]",
            "What city and country are you currently based in?",
            "What is your highest level of education? [High school] [Bachelor's degree] [Master's degree] [PhD] [Other]",
            "What is your current profession or area of work/study?",
            "Do you use digital tools or software regularly in your daily routine? Yes/No",
            "How would you describe your tech familiarity? [Beginner] [Intermediate] [Advanced] [Expert]",
            "How often do you face the specific problem this product aims to solve?",
            "How much does this product fit people in your demographic group? (1 = Not at all, 5 = Perfectly)"
        ]
    },
    "REFERRAL LIKELIHOOD": {
        "description": "Whether users would tell others about the product. Measures viral potential.",
        "example_questions": [
            "How likely are you to recommend this product to someone else? (1 = Never, 5 = Definitely)",
            "Why would or wouldn't you tell a friend or colleague about this?",
            "Would you share this product on your LinkedIn/Twitter/WhatsApp group? Yes/No",
            "Who in your network would find this most useful? [Coworkers] [Friends] [Students] [Industry peers] [Not sure]",
            "How confident are you in the value this product delivers to others? (1 = Not confident, 5 = Very confident)",
            "What feature or moment made you say \"Wow — others need this\"?",
            "Would you refer this product if you got early access or perks? Yes/No",
            "What would make this product something you're proud to recommend?"
        ]
    }
}

def get_guardrails_for_stage(stage: str):
    if stage == "IDEATION & PLANNING":
        return IDEATION_GUARDRAILS
    elif stage == "PROTOTYPE DEVELOPMENT":
        return PROTOTYPE_GUARDRAILS
    else:
        return {}

# ====================
# Enhanced Prompt Builder
# ====================
def build_guardrail_based_prompt(surveyPurpose: str, startupAnalysis: StartupAnalysis):
    guardrails = get_guardrails_for_stage(startupAnalysis.stage)
    
    # Build detailed guardrail section with examples
    guardrail_sections = []
    for guardrail_name, guardrail_data in guardrails.items():
        example_questions = "\n    ".join([f"- {q}" for q in guardrail_data["example_questions"]])
        guardrail_section = f"""
{guardrail_name}: {guardrail_data["description"]}
  Example questions you can reference (DO NOT copy exactly, but use as inspiration):
    {example_questions}
"""
        guardrail_sections.append(guardrail_section)
    
    guardrail_content = "\n".join(guardrail_sections)

    prompt = f"""
You are a user researcher creating a 10-question survey designed to validate assumptions for a startup in the **{startupAnalysis.stage}** stage.

--- Startup Overview ---
Title: {startupAnalysis.title}
Description: {startupAnalysis.description}
Stage: {startupAnalysis.stage}
Survey Purpose: {surveyPurpose}

--- Burning Problems to Validate ---
{chr(10).join([f"{i+1}. {p}" for i, p in enumerate(startupAnalysis.burningProblems)])}

--- Guardrail Categories with Example Questions ---
{guardrail_content}

SURVEY STRUCTURE REQUIREMENTS:
- Generate **exactly 10 questions**
- **3 questions** must reference burning problems (1 question per burning problem)
- **7 questions** must be based on guardrails from the above list
- Use a **diverse mix of question types**:
  * **scale** questions (1-5 or 1-10 rating scales)
  * **mcq** questions (multiple choice with options)
  * **yes_no** questions (simple Yes/No)
  * **text** questions (open-ended text responses)

QUESTION REQUIREMENTS:
- Each question must test a real-world assumption that a user (not the founder) can answer
- Questions should be customer-facing and user-friendly
- Use the example questions as REFERENCE ONLY - do not copy them exactly
- Create original questions inspired by the guardrail concepts
- Ensure questions are actionable and provide meaningful insights
- For MCQ questions, provide 3-5 relevant options in square brackets

Return only valid JSON in this EXACT format:
[
  {{
    "text": "Your question text here",
    "bucket": "burning_problem_1" | "burning_problem_2" | "burning_problem_3" | "guardrail:<GUARDRAIL_NAME>",
    "type": "scale" | "mcq" | "yes_no" | "text",
    "burning_problem_reference": 1 | 2 | 3 | null
  }},
  ...
]

IMPORTANT: 
- For MCQ questions, include options within the question text using square brackets
- For scale questions, specify the scale range in the question text
- Ensure exactly 3 questions have burning_problem_reference values (1, 2, 3)
- Ensure exactly 7 questions have guardrail buckets
- Use diverse question types across all 10 questions
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
            max_tokens=3000
        )
        return response.content[0].text.strip() if response.content else ""
    except Exception as e:
        st.error(f"❌ Claude API Error: {e}")
        return ""

# ====================
# Streamlit App UI
# ====================
st.title("🧠 Enhanced Outlaw Survey Generator")
st.markdown("*Generates 10 questions: 3 for burning problems + 7 for guardrails with diverse question types*")

with st.form("survey_form"):
    study_id = st.text_input("Study ID", "sample_study_vapi")
    purpose = st.text_input("Survey Purpose", "Understand user need, pain intensity, and feature expectation")
    title = st.text_input("Startup Title", "Vapi")
    description = st.text_area("Startup Description", "Vapi is a developer-first platform that simplifies the creation, testing, and deployment of voice AI agents. It enables real-time voice orchestration, function calling, and text-to-speech generation for building conversational AI experiences across industries.")
    stage = st.selectbox("Startup Stage", ["IDEATION & PLANNING", "PROTOTYPE DEVELOPMENT"])
    
    st.subheader("Burning Problems (3 required)")
    burning_1 = st.text_input("Burning Problem 1", "Developers spend too much time building voice AI agents from scratch")
    burning_2 = st.text_input("Burning Problem 2", "Existing tools lack real-time orchestration and integration flexibility")
    burning_3 = st.text_input("Burning Problem 3", "There's no seamless way to combine voice analytics with function-calling in custom flows")

    submitted = st.form_submit_button("Generate Enhanced Survey")

    if submitted:
        try:
            input_obj = StartupAnalysis(
                title=title,
                description=description,
                stage=stage,
                burningProblems=[burning_1, burning_2, burning_3]
            )
            
            with st.spinner("Generating survey questions..."):
                prompt = build_guardrail_based_prompt(purpose, input_obj)
                raw_output = query_claude(prompt)

            try:
                parsed = json.loads(raw_output)
                st.success("✅ Enhanced survey questions generated!")
                
                # Display summary
                question_types = {}
                burning_problem_count = 0
                guardrail_count = 0
                
                for q in parsed:
                    q_type = q.get("type", "unknown")
                    question_types[q_type] = question_types.get(q_type, 0) + 1
                    
                    if q.get("burning_problem_reference"):
                        burning_problem_count += 1
                    elif q.get("bucket", "").startswith("guardrail:"):
                        guardrail_count += 1
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Questions", len(parsed))
                with col2:
                    st.metric("Burning Problem Questions", burning_problem_count)
                with col3:
                    st.metric("Guardrail Questions", guardrail_count)
                
                st.subheader("Question Type Distribution")
                for q_type, count in question_types.items():
                    st.write(f"**{q_type.upper()}**: {count} questions")
                
                st.subheader("Generated Questions")
                st.json(parsed)
                
            except Exception as parse_error:
                st.error("❌ Failed to parse output as JSON. Here's the raw output:")
                st.code(raw_output)
                
        except ValidationError as ve:
            st.error(f"Input Validation Failed: {ve}")

# ====================
# Display Available Guardrails
# ====================
with st.expander("📋 View Available Guardrails for Current Stage"):
    if st.session_state.get('stage'):
        current_stage = st.session_state.get('stage', 'IDEATION & PLANNING')
    else:
        current_stage = 'IDEATION & PLANNING'
    
    guardrails = get_guardrails_for_stage(current_stage)
    st.write(f"**Available guardrails for {current_stage}:**")
    for name, data in guardrails.items():
        st.write(f"• **{name}**: {data['description']}")