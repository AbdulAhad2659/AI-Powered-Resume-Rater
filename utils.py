import re
from datetime import datetime
from pathlib import Path
from typing import List

from config import RECOMMENDED_FILE, logger

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
URL_RE = re.compile(r"https?://[^\s]+")


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned[:100] if len(cleaned) > 100 else cleaned


def append_to_recommended_file(candidate_name: str, suggested_steps: List[str],
                               rating: float, justification: dict,
                               recommended_file: str = RECOMMENDED_FILE):
    try:
        Path(recommended_file).parent.mkdir(parents=True, exist_ok=True)
        with open(recommended_file, "a", encoding="utf-8") as fh:
            fh.write(f"=" * 50 + "\n")
            fh.write(f"CANDIDATE: {candidate_name}\n")
            fh.write(f"OVERALL SCORE: {rating}/10\n")

            rec_data = justification.get("recommendation", {})
            fh.write(f"DECISION: {rec_data.get('decision', 'Unknown')}\n")
            fh.write(f"CONFIDENCE: {rec_data.get('confidence', 'Unknown')}\n")

            strengths = justification.get("overall_assessment", {}).get("key_strengths", [])
            if strengths:
                fh.write("KEY STRENGTHS:\n")
                for strength in strengths[:3]:
                    fh.write(f"  • {strength}\n")

            fh.write("SUGGESTED NEXT STEPS:\n")
            if isinstance(suggested_steps, list):
                for step in suggested_steps:
                    fh.write(f"  • {step}\n")
            else:
                fh.write(f"  • {suggested_steps}\n")

            interview_focus = rec_data.get("interview_focus", [])
            if interview_focus:
                fh.write("INTERVIEW FOCUS AREAS:\n")
                for area in interview_focus:
                    fh.write(f"  • {area}\n")

            fh.write(f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            fh.write("\n" + "=" * 50 + "\n\n")
    except Exception as e:
        logger.warning(f"Failed to append to recommended file {recommended_file}: {e}")
        