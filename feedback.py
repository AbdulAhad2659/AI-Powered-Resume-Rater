import base64
from datetime import datetime
from typing import Any, Dict, Optional

from config import logger
from llm_utils import call_llm_with_fallback


def generate_candidate_feedback_pdf(result: Dict[str, Any]) -> Optional[bytes]:
    candidate_name = result.get("candidate_name", "Candidate")

    overall_assessment = result.get("llm_justification", {}).get("overall_assessment", {})
    skills_eval = result.get("llm_justification", {}).get("skills_evaluation", {})
    recommendation = result.get("llm_justification", {}).get("recommendation", {})

    feedback_prompt = f"""
Write a constructive, encouraging feedback letter for {candidate_name} who applied for a technical position.

Key information:
- Overall score: {result.get('final_score_0_10', 0)}/10
- Matched skills: {result.get('matched_skills', [])}
- Experience level: {result.get('years_experience_estimate', 0)} years
- Key strengths: {overall_assessment.get('key_strengths', [])}
- Areas for improvement: {overall_assessment.get('areas_for_improvement', [])}

Write a professional, encouraging 3-4 paragraph letter that:
1. Thanks them for their application and acknowledges their efforts
2. Highlights their strengths and potential 
3. Provides specific, actionable advice for skill development
4. Ends with encouragement about their career journey

Tone: Professional, supportive, constructive (not harsh or discouraging)
"""
    try:
        feedback_text = call_llm_with_fallback(feedback_prompt, json_expected=False)
        if not feedback_text:
            return None
    except Exception as e:
        logger.error(f"Error generating feedback text: {e}")
        return None

    try:
        from fpdf import FPDF

        sanitized_name = candidate_name.encode('latin-1', 'replace').decode('latin-1')
        sanitized_feedback = feedback_text.encode('latin-1', 'replace').decode('latin-1')

        pdf = FPDF()
        pdf.add_page()

        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, f"Career Development Feedback - {sanitized_name}", 0, 1, "C")
        pdf.ln(5)

        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 10, f"Date: {datetime.now().strftime('%B %d, %Y')}", 0, 1, "R")
        pdf.ln(5)

        pdf.set_font("Helvetica", "", 12)
        pdf.multi_cell(0, 6, sanitized_feedback)
        pdf.ln(5)

        pdf.set_font("Helvetica", "I", 10)
        pdf.multi_cell(0, 5, "Best wishes for your continued professional development!")

        return pdf.output()

    except ImportError:
        logger.error("fpdf2 is not installed. Please run 'pip install fpdf2' to enable PDF generation.")
        return None
    except Exception as e:
        logger.error(f"Failed to create PDF report: {e}")
        return None
    