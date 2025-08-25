import base64
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import UploadFile

from config import AUDIO_SAVE_DIR, logger
from parsing import parse_resume_file
from llm_utils import (
    extract_skills_with_gemini,
    extract_experience_with_enhanced_analysis,
    extract_name_with_gemini,
    generate_speech_from_text,
    generate_enhanced_llm_justification,
)
from scoring import compute_enhanced_component_scores, aggregate_enhanced_scores
from feedback import generate_candidate_feedback_pdf
from utils import sanitize_filename


async def process_single_resume_enhanced(job_description: str,
                                         resume_file: UploadFile,
                                         jd_skills: Optional[List[str]] = None,
                                         include_audio: bool = False) -> Dict[str, Any]:
    parsed = parse_resume_file(resume_file)
    resume_text = parsed["text"]
    candidate_name = extract_name_with_gemini(resume_text, filename=parsed.get("filename"))

    if jd_skills is None:
        jd_skills_local = extract_skills_with_gemini(job_description, role="job_description", max_skills=50)
    else:
        jd_skills_local = jd_skills

    resume_skills = extract_skills_with_gemini(resume_text, role="resume", max_skills=80)
    experience_data = extract_experience_with_enhanced_analysis(resume_text)

    component_scores = compute_enhanced_component_scores(
        job_description, resume_text, jd_skills_local, resume_skills, experience_data
    )

    aggregated_scores = aggregate_enhanced_scores(component_scores)

    llm_justification = generate_enhanced_llm_justification(
        candidate_name=candidate_name,
        job_description=job_description,
        component_scores=component_scores,
        skill_analysis={
            'matched_skills': component_scores.get('matched_skills', []),
            'confidence_scores': component_scores.get('confidence_scores', {}),
            'total_jd_skills': len(jd_skills_local),
            'match_statistics': component_scores.get('match_statistics', {})
        },
        experience_data=experience_data,
        final_score_0_10=aggregated_scores['score_0_10']
    )

    tts_b64 = None
    saved_audio_filename = None
    if include_audio:
        try:
            decision = llm_justification.get("recommendation", {}).get("decision", "")
            summary = llm_justification.get("overall_assessment", {}).get("summary", "")
            next_steps = llm_justification.get("next_steps", [])

            speak_text = f"Assessment for {candidate_name}: {decision}. {summary} Recommended next steps: {' '.join(next_steps[:2])}"

            tts_result = await generate_speech_from_text(speak_text)
            if tts_result and tts_result.get("b64"):
                tts_b64 = tts_result.get("b64")
                audio_format = tts_result.get("format", "wav")

                try:
                    filename_safe = sanitize_filename(candidate_name) or "candidate"
                    out_filename = f"{filename_safe}.{audio_format}"
                    out_path = Path(AUDIO_SAVE_DIR) / out_filename

                    with open(out_path, "wb") as f:
                        f.write(base64.b64decode(tts_b64))
                    saved_audio_filename = out_filename
                except Exception as file_e:
                    logger.warning(f"Failed to save TTS file for {candidate_name}: {file_e}")
        except Exception as e:
            logger.warning(f"TTS generation failed: {e}")

    response = {
        "candidate_name": candidate_name,
        "filename": parsed["filename"],
        "final_score_0_10": aggregated_scores["score_0_10"],
        "final_score_0_100": aggregated_scores["score_0_100"],
        "component_scores": {k: round(v, 3) for k, v in component_scores.items() if k.endswith('_score')},
        "per_component_0_10": aggregated_scores["per_component_0_10"],
        "matched_skills": component_scores.get("matched_skills", []),
        "jd_skills": jd_skills_local,
        "resume_skills": resume_skills,
        "years_experience_estimate": experience_data.get("total_years_experience", 0),
        "technical_years_estimate": experience_data.get("technical_years_experience", 0),
        "skill_evidence": component_scores.get("skill_evidence", {}),
        "confidence_scores": component_scores.get("confidence_scores", {}),
        "match_statistics": component_scores.get("match_statistics", {}),
        "missing_requirements": [s for s in jd_skills_local if s not in component_scores.get("matched_skills", [])],
        "llm_justification": llm_justification,
        "tts_audio_base64": tts_b64,
        "tts_saved_filename": saved_audio_filename,
        "experience_data": experience_data
    }

    feedback_report_base64 = None
    recommendation = llm_justification.get("recommendation", {}).get("decision", "").lower()
    if "not recommended" in recommendation or aggregated_scores["score_0_10"] < 6.0:
        pdf_bytes = generate_candidate_feedback_pdf(response)
        if pdf_bytes:
            feedback_report_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

    response["feedback_report_base64"] = feedback_report_base64
    return response
