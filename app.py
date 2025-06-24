import streamlit as st
import json
import anthropic
from typing import List, Optional, Literal
from pydantic import BaseModel, ValidationError

# ====================
# Pydantic Models (for validation)
# ====================
class Idea(BaseModel):
    title: str
    description: str

class StartupAnalysis(BaseModel):
    title: str
    description: str
    stage: Literal["IDEATION & PLANNING", "PROTOTYPE DEVELOPMENT", "VALIDATION & ITERATION", "LAUNCH & SCALING", "GROWTH & OPTIMIZATION"]
    burningProblems: List[str]  # Exactly 3 burning problems

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
    try:
        # Access API key from Streamlit secrets
        api_key = st.secrets["anthropic"]["api_key"]
        client = anthropic.Anthropic(api_key=api_key)
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
    
    except KeyError:
        st.error("❌ Anthropic API key not found in secrets. Please configure it in Streamlit Cloud.")
        return ""
    except Exception as e:
        st.error(f"❌ Error calling Claude API: {str(e)}")
        return ""

# ====================
# Streamlit UI
# ====================
def main():
    st.set_page_config(
        page_title="AI Survey Generator",
        page_icon="📋",
        layout="wide"
    )
    
    st.title("🚀 AI-Powered Survey Generator")
    st.markdown("Generate stage-specific surveys for your startup based on burning problems")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        study_id = st.text_input("Study ID", value=f"study_{hash(str(st.session_state))}")
        
    # Main form
    with st.form("survey_generator_form"):
        st.header("📝 Startup Information")
        
        # Basic startup info
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Startup Title*", placeholder="e.g., EcoTrack")
        with col2:
            stage = st.selectbox(
                "Current Stage*",
                options=[
                    "IDEATION & PLANNING",
                    "PROTOTYPE DEVELOPMENT", 
                    "VALIDATION & ITERATION",
                    "LAUNCH & SCALING",
                    "GROWTH & OPTIMIZATION"
                ]
            )
        
        description = st.text_area(
            "Startup Description*",
            placeholder="Describe what your startup does and the value it provides...",
            height=100
        )
        
        survey_purpose = st.text_area(
            "Survey Purpose*",
            placeholder="What specific insights are you trying to gain from this survey?",
            height=80
        )
        
        st.subheader("🔥 Burning Problems")
        st.markdown("*Enter exactly 3 critical problems your startup addresses:*")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            problem1 = st.text_area("Problem 1*", height=80, key="prob1")
        with col2:
            problem2 = st.text_area("Problem 2*", height=80, key="prob2")
        with col3:
            problem3 = st.text_area("Problem 3*", height=80, key="prob3")
        
        # Submit button
        submitted = st.form_submit_button("🎯 Generate Survey", type="primary")
    
    # Handle form submission outside the form
    if submitted:
            # Validation
            if not all([title, description, survey_purpose, problem1, problem2, problem3]):
                st.error("❌ Please fill in all required fields")
                return
            
            # Create startup analysis object
            try:
                startup_analysis = StartupAnalysis(
                    title=title,
                    description=description,
                    stage=stage,
                    burningProblems=[problem1.strip(), problem2.strip(), problem3.strip()]
                )
            except ValidationError as e:
                st.error(f"❌ Validation error: {e}")
                return
            
            # Generate survey
            with st.spinner("🤖 Generating your custom survey..."):
                prompt = build_stage_specific_survey_prompt(survey_purpose, startup_analysis)
                raw_output = query_claude(prompt)
                
                if not raw_output:
                    return
                
                try:
                    parsed_questions = json.loads(raw_output)
                    
                    if isinstance(parsed_questions, list) and len(parsed_questions) == 10:
                        # Display success
                        st.success("✅ Survey generated successfully!")
                        
                        # Prepare and store data
                        stage_info = get_stage_focus(stage)
                        st.session_state.export_data = {
                            "studyId": study_id,
                            "startup": {
                                "title": title,
                                "description": description,
                                "stage": stage
                            },
                            "surveyPurpose": survey_purpose,
                            "burningProblems": [problem1, problem2, problem3],
                            "questions": parsed_questions,
                            "metadata": {
                                "stage_focus": stage_info['primary_focus'],
                                "validation_goal": stage_info['validation_goal']
                            }
                        }
                        
                        # Display JSON output only
                        st.json(st.session_state.export_data)
                        
                    else:
                        st.error("❌ Generated survey doesn't contain exactly 10 questions")
                        with st.expander("View Raw Output"):
                            st.code(raw_output)
                    
                except json.JSONDecodeError as e:
                    st.error(f"❌ Could not parse AI response as JSON: {str(e)}")
                    with st.expander("View Raw Output"):
                        st.code(raw_output)
    
    # Download section outside the form
    if 'export_data' in st.session_state:
        st.header("💾 Export Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # JSON download
            st.download_button(
                label="📄 Download as JSON",
                data=json.dumps(st.session_state.export_data, indent=2),
                file_name=f"survey_{st.session_state.export_data['studyId']}.json",
                mime="application/json"
            )
        
        with col2:
            # CSV-like format for easy copying
            csv_content = "Question Number,Question Text,Type,Bucket,Burning Problem Reference\n"
            for i, q in enumerate(st.session_state.export_data['questions'], 1):
                csv_content += f"{i},\"{q['text']}\",{q['type']},{q['bucket']},{q.get('burning_problem_reference', '')}\n"
            
            st.download_button(
                label="📊 Download as CSV",
                data=csv_content,
                file_name=f"survey_questions_{st.session_state.export_data['studyId']}.csv",
                mime="text/csv"
            )

# ====================
# App Entry Point
# ====================
if __name__ == "__main__":
    main()