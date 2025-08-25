from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ScoreResponse(BaseModel):
    candidate_name: str
    filename: str
    final_score_0_10: float
    final_score_0_100: float
    component_scores: Dict[str, float]
    per_component_0_10: Dict[str, float]
    matched_skills: List[str]
    jd_skills: List[str]
    resume_skills: List[str]
    years_experience_estimate: float
    technical_years_estimate: float
    skill_evidence: Dict[str, List[str]]
    confidence_scores: Dict[str, float]
    match_statistics: Dict[str, Any]
    missing_requirements: List[str]
    llm_justification: Dict[str, Any]
    tts_audio_base64: Optional[str] = None
    tts_saved_filename: Optional[str] = None
    experience_data: Dict[str, Any]
    feedback_report_base64: Optional[str] = None
    