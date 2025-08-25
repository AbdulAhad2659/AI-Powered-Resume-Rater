import os
from pathlib import Path
from typing import List, Optional, Any, Dict

import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse

from config import (
    AUDIO_SAVE_DIR,
    RECOMMENDED_FILE,
    GOOGLE_API_KEY,
    groq_client,
    logger,
    STATIC_DIR,
)
from openapi_patch import custom_openapi
from models import ScoreResponse
from service import process_single_resume_enhanced
from llm_utils import extract_skills_with_gemini
from utils import append_to_recommended_file

app = FastAPI(title="Resume Rating", version="1.0.0")
app.openapi = lambda: custom_openapi(app)


@app.post("/rate", response_model=ScoreResponse)
async def rate_resume_enhanced(
    job_description: str = Form(...),
    resume: UploadFile = File(...),
    include_audio: Optional[bool] = Form(False)
):
    result = await process_single_resume_enhanced(
        job_description, resume, jd_skills=None, include_audio=bool(include_audio)
    )
    return JSONResponse(content=result)


@app.post("/batch-rate", response_model=List[ScoreResponse])
async def batch_rate_enhanced(
    job_description: str = Form(...),
    resumes: List[UploadFile] = File(...),
    include_audio: Optional[bool] = Form(False)
):
    # Clear old recommendations file
    try:
        if os.path.exists(RECOMMENDED_FILE):
            os.remove(RECOMMENDED_FILE)
            logger.info(f"Cleared old recommendations file: {RECOMMENDED_FILE}")
    except Exception as e:
        logger.warning(f"Could not remove old recommendations file: {e}")

    jd_skills = extract_skills_with_gemini(job_description, role="job_description", max_skills=50)
    if not jd_skills:
        logger.warning("No JD skills extracted, using fallback parsing")
        jd_skills = []

    results = []
    recommended_count = 0

    for resume_file in resumes:
        try:
            result = await process_single_resume_enhanced(
                job_description, resume_file, jd_skills=jd_skills, include_audio=bool(include_audio)
            )

            justification = result.get("llm_justification", {})
            recommendation = justification.get("recommendation", {})
            decision = recommendation.get("decision", "").lower()
            score = result.get("final_score_0_10", 0)

            should_recommend = (
                score >= 6.5 and any(keyword in decision for keyword in ["strong recommend", "recommend"]) or
                score >= 7.5
            )

            if should_recommend:
                try:
                    next_steps = justification.get("next_steps", [])
                    append_to_recommended_file(
                        result.get("candidate_name", "Unknown"),
                        next_steps,
                        result.get("final_score_0_10", 0.0),
                        justification
                    )
                    recommended_count += 1
                except Exception as e:
                    logger.warning(f"Failed to add {resume_file.filename} to recommended list: {e}")

            results.append(result)

        except Exception as e:
            logger.exception("Error processing resume %s: %s", getattr(resume_file, "filename", "<unknown>"), e)
            error_result = {
                "candidate_name": "Processing Failed",
                "filename": getattr(resume_file, "filename", "unknown"),
                "final_score_0_10": 0.0,
                "final_score_0_100": 0.0,
                "component_scores": {},
                "per_component_0_10": {},
                "matched_skills": [],
                "jd_skills": jd_skills,
                "resume_skills": [],
                "years_experience_estimate": 0.0,
                "technical_years_estimate": 0.0,
                "skill_evidence": {},
                "confidence_scores": {},
                "match_statistics": {},
                "missing_requirements": ["processing_error"],
                "llm_justification": {
                    "overall_assessment": {
                        "summary": f"Processing failed: {str(e)}",
                        "key_strengths": [],
                        "areas_for_improvement": ["File processing error"]
                    },
                    "recommendation": {
                        "decision": "Not Recommended",
                        "reasoning": "Technical processing error"
                    }
                },
                "tts_audio_base64": None,
                "tts_saved_filename": None,
                "experience_data": {},
                "feedback_report_base64": None
            }
            results.append(error_result)

    logger.info(f"Batch processing complete: {len(results)} resumes processed, {recommended_count} candidates recommended")
    return JSONResponse(content=results)


@app.get("/", response_class=HTMLResponse)
async def uploader_page():
    index_path = Path(STATIC_DIR) / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Missing static/index.html")
    return FileResponse(index_path)


@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    if ".." in filename or filename.startswith("/") or not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    path = Path(AUDIO_SAVE_DIR) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    ext = path.suffix.lower()
    media_type = {
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
        ".wav": "audio/wav"
    }.get(ext, "audio/wav")

    return FileResponse(path, media_type=media_type, filename=filename)


@app.get("/download-recommended")
async def download_recommended():
    if not Path(RECOMMENDED_FILE).exists():
        return JSONResponse(
            status_code=404,
            content={"detail": "No recommendations file found. Process some resumes first."}
        )

    try:
        with open(RECOMMENDED_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return JSONResponse(
                    status_code=404,
                    content={"detail": "No candidates have been recommended yet. The recommendations file is empty."}
                )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error reading recommendations file: {str(e)}"}
        )

    return FileResponse(
        RECOMMENDED_FILE,
        media_type="text/plain",
        filename="recommended_candidates.txt"
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "2.0-enhanced",
        "features": {
            "advanced_skill_matching": True,
            "fair_scoring_algorithm": True,
            "enhanced_pdf_parsing": True,
            "audio_generation": bool(GOOGLE_API_KEY),
            "groq_fallback": bool(groq_client),
            "feedback_reports": True
        },
        "audio_dir": str(Path(AUDIO_SAVE_DIR).resolve()),
        "recommended_file": str(Path(RECOMMENDED_FILE).resolve()),
        "total_audio_files": len(list(Path(AUDIO_SAVE_DIR).glob("*"))),
    }


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )