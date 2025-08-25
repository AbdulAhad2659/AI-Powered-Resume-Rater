import base64
import io
import json
import re
import wave
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types
from google.genai.types import HarmCategory, HarmBlockThreshold

from config import logger, groq_client
from utils import EMAIL_RE

GEMINI_SAFETY_SETTINGS = [
    {
        "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
]


def call_llm_with_fallback(prompt: str, json_expected: bool = False, groq_model: str = "llama3-70b-8192") -> str:
    try:
        client = genai.Client()

        config_params = {
            "safety_settings": GEMINI_SAFETY_SETTINGS,
            "temperature": 0.1,
        }
        if json_expected:
            config_params["response_mime_type"] = "application/json"

        gen_config = types.GenerateContentConfig(**config_params)

        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=gen_config
        )

        raw = getattr(resp, 'text', None)
        raw = raw.strip() if raw else ""

        if raw:
            if json_expected:
                try:
                    json.loads(raw)
                    return raw
                except Exception as e:
                    logger.warning(f"Gemini returned invalid JSON: {e}. Falling back.")
            else:
                return raw
        else:
            logger.warning("Gemini returned empty response; attempting fallback.")

    except Exception as e:
        logger.warning(f"Gemini call failed: {e}. Attempting fallback to Groq.")

    if not groq_client:
        logger.error("Groq fallback requested but client is not configured.")
        return ""

    messages = [
        {"role": "system",
         "content": "You are a helpful assistant specialized in resume analysis and job matching. If the user asks for JSON, you must return valid JSON."},
        {"role": "user", "content": prompt}
    ]

    try:
        call_kwargs = {
            "model": groq_model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 8192,
            "top_p": 1,
        }
        if json_expected:
            call_kwargs["response_format"] = {"type": "json_object"}

        completion = groq_client.chat.completions.create(**call_kwargs)
        raw_out = completion.choices[0].message.content.strip()

        if not raw_out:
            raise RuntimeError("Groq returned an empty response")

        if json_expected:
            json.loads(raw_out)

        return raw_out

    except Exception as e:
        logger.error(f"Groq fallback also failed: {e}")
        return ""


def extract_skills_with_gemini(text: str, role: str = "job_description", max_skills: int = 60) -> List[str]:
    prompt = f"""
You are an expert technical recruiter with deep knowledge of modern technology stacks and job requirements.

Analyze the following {role} and extract ALL technical skills, tools, technologies, and requirements mentioned.
Be comprehensive and include:
- Programming languages and versions
- Frameworks and libraries  
- Databases and storage systems
- Cloud platforms and services
- DevOps tools and practices
- Development methodologies
- Soft skills that are explicitly technical (e.g., "technical leadership", "system design")
- Certifications and technical qualifications

IMPORTANT GUIDELINES:
- Include both explicit mentions AND strongly implied skills
- Normalize common variations (e.g., "JS" -> "JavaScript", "React.js" -> "React")
- For job descriptions: include both required and preferred skills
- For resumes: include skills from experience, projects, and education sections
- Don't exclude a skill just because it appears in a different context
- Include industry-standard abbreviations and their full forms

Return a valid JSON object with exactly one key: "skills" containing an array of strings.
Limit to the {max_skills} most relevant and important skills, prioritized by:
1. Direct relevance to the role
2. Current industry demand
3. Technical complexity/importance

Input ({role}):
\"\"\"{text[:4000]}\"\"\"

Return only the JSON object, no other text.
"""
    try:
        raw = call_llm_with_fallback(prompt, json_expected=True)
        if not raw:
            raise Exception("Empty LLM response")

        parsed = json.loads(raw)
        skills = parsed.get("skills", []) if isinstance(parsed, dict) else []

        clean_skills = []
        for skill in skills:
            if isinstance(skill, str) and len(skill.strip()) > 1:
                clean_skill = skill.strip()
                if not any(clean_skill.lower() == existing.lower() for existing in clean_skills):
                    clean_skills.append(clean_skill)

        return clean_skills[:max_skills]

    except Exception as e:
        logger.warning(f"LLM skill extraction failed: {e}, using fallback method")

    fallback_skills = set()
    patterns = [
        r'\b[A-Z][a-z]+(?:\.[js|py|rb]+)?\b',
        r'\b[A-Z]{2,}\b',
        r'\b\w+(?:JS|SQL|DB|API|UI|UX)\b',
        r'\b(?:v?\d+\.?\d*)\s*(?:years?|yrs?|months?|mos?)\s+(?:of\s+)?(\w+)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[-1]
            if len(match) > 2 and not match.isdigit():
                fallback_skills.add(match)

    tech_terms = [
        'Python', 'JavaScript', 'Java', 'React', 'Node.js', 'SQL', 'AWS', 'Docker',
        'Kubernetes', 'Git', 'Linux', 'API', 'REST', 'MongoDB', 'PostgreSQL',
        'HTML', 'CSS', 'Machine Learning', 'Data Science', 'DevOps', 'Agile'
    ]

    text_lower = text.lower()
    for term in tech_terms:
        if term.lower() in text_lower:
            fallback_skills.add(term)

    return list(fallback_skills)[:max_skills]


def extract_experience_with_enhanced_analysis(resume_text: str) -> Dict[str, Any]:
    # FIX: The entire JSON example block is now wrapped in {{ and }} to escape the braces.
    prompt = f"""
You are an expert resume analyzer. Analyze the professional experience in this resume and provide detailed information.

Extract:
1. Total years of professional experience (sum all professional roles, don't double-count overlapping periods)
2. Years of relevant technical experience (programming, software development, technical roles only)
3. Most recent job title and company
4. Key achievements with quantified impact
5. Technology stack and tools used across all positions

Guidelines:
- Only count professional full-time experience, not internships or part-time unless specifically mentioned as substantial
- For date ranges like "2020-Present", use current date ({datetime.now().year}) for calculations
- Be conservative but fair in estimating partial years

Return valid JSON with these exact keys:
{{
    "total_years_experience": "<number>",
    "technical_years_experience": "<number>",
    "most_recent_role": {{"title": "...", "company": "..."}},
    "key_achievements": ["...", "..."],
    "technologies_used": ["...", "..."]
}}

Resume text:
\"\"\"{resume_text[:4000]}\"\"\"
"""
    try:
        raw = call_llm_with_fallback(prompt, json_expected=True)
        if raw:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
    except Exception as e:
        logger.warning(f"Enhanced experience extraction failed: {e}")

    # Fallback logic... (remains the same)
    current_year = datetime.now().year
    total_months = 0
    date_patterns = [
        r'(\d{4})\s*[-–—]\s*(present|current|\d{4})',
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})\s*[-–—]\s*(present|current|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})'
    ]

    for pattern in date_patterns:
        matches = re.finditer(pattern, resume_text, re.IGNORECASE)
        for match in matches:
            try:
                # Robustly handle different match group lengths from regex patterns
                groups = match.groups()
                start_year = int(re.search(r'\d{4}', groups[0]).group()) if not groups[0].isdigit() else int(groups[0])
                end_str = groups[-1].lower()

                if 'present' in end_str or 'current' in end_str:
                    end_year = current_year
                else:
                    end_year_match = re.search(r'\d{4}', end_str)
                    end_year = int(end_year_match.group()) if end_year_match else start_year

                years_diff = max(0, end_year - start_year)
                total_months += years_diff * 12
            except (ValueError, IndexError, AttributeError):
                continue

    total_years = round(total_months / 12.0, 1) if total_months > 0 else 0

    return {
        "total_years_experience": total_years,
        "technical_years_experience": total_years * 0.8,
        "most_recent_role": {"title": "Unknown", "company": "Unknown"},
        "key_achievements": [],
        "technologies_used": []
    }


def extract_name_with_gemini(resume_text: str, filename: Optional[str] = None) -> str:
    def clean_name_candidate(s: str) -> str:
        s = s.strip()
        s = re.sub(r"^[\-\u2022\*]+\s*", "", s)
        s = re.sub(r"[\r\n]+", " ", s)
        s = re.sub(r"\b(Curriculum Vitae|CV|Resume|Profile)\b", "", s, flags=re.I).strip()
        s = re.sub(r"\s+", " ", s)
        s = s.strip(" \t\n,:;.-")
        return s

    try:
        # FIX: Escaped the curly braces for the JSON examples with {{ and }}
        prompt = f"""
Extract the candidate's full name from this resume. Look for:
- Names at the top of the document
- Headers or titles indicating personal information
- Email addresses that might contain name information
- Professional signatures

Return only JSON: {{"name": "Full Name"}} or {{"name": ""}} if unclear.

Resume text:
\"\"\"{resume_text[:2000]}\"\"\"
"""
        raw = call_llm_with_fallback(prompt, json_expected=True)
        if raw:
            parsed = json.loads(raw)
            name = parsed.get("name", "") if isinstance(parsed, dict) else ""
            name = clean_name_candidate(str(name))
            if name and len(name.split()) >= 2:
                return name
    except Exception:
        pass

    # Fallback logic... (remains the same)
    lines = [ln.strip() for ln in resume_text.splitlines()[:15] if ln.strip()]
    name_patterns = [
        r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'^([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)+[A-Z][a-z]+)',
        r'Name:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
    ]
    for line in lines:
        for pattern in name_patterns:
            match = re.search(pattern, line)
            if match:
                candidate = clean_name_candidate(match.group(1))
                if candidate and 2 <= len(candidate.split()) <= 4:
                    return candidate
    emails = EMAIL_RE.findall(resume_text)
    if emails:
        prefix = emails[0].split("@")[0]
        parts = re.split(r'[._\-\d]+', prefix)
        parts = [p.capitalize() for p in parts if p and p.isalpha() and len(p) > 1]
        if len(parts) >= 2:
            return " ".join(parts[:3])
    if filename:
        base = Path(filename).stem
        base_clean = re.sub(r'[_\-.]+', ' ', base).strip()
        base_clean = re.sub(r'\d+', '', base_clean).strip()
        if base_clean and 2 <= len(base_clean.split()) <= 4:
            return " ".join([w.capitalize() for w in base_clean.split()])
    return "Unknown Candidate"


async def generate_speech_from_text(text_to_speak: str) -> Dict[str, str]:
    cleaned_text = re.sub(r"[#*]", "", text_to_speak)
    logger.info(f"Generating audio for text: '{cleaned_text[:100]}...'")

    try:
        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=f"Read the following professional assessment clearly: {cleaned_text}",
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Charon",
                        )
                    )
                ),
            ),
        )

        try:
            audio_data = response.candidates[0].content.parts[0].inline_data.data
        except Exception:
            audio_data = getattr(response, "audio", None) or b""

        audio_bytes = bytes(audio_data) if audio_data is not None else b""

        if not audio_bytes:
            logger.error("TTS returned empty audio bytes.")
            return {"b64": "", "format": "wav"}

        fmt = detect_audio_format(audio_bytes)
        final_bytes = audio_bytes

        if fmt == "raw":
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(audio_bytes)
            final_bytes = buf.getvalue()
            fmt = "wav"

        return {"b64": base64.b64encode(final_bytes).decode("utf-8"), "format": fmt}

    except Exception as e:
        logger.error(f"Failed to generate TTS audio: {e}")
        return {"b64": "", "format": "wav"}


def detect_audio_format(data: bytes) -> str:
    if not data or len(data) < 4:
        return "raw"
    header = data[:12]
    if header.startswith(b"RIFF"):
        return "wav"
    if header.startswith(b"ID3") or header[:2] == b"\xff\xfb":
        return "mp3"
    if header.startswith(b"OggS"):
        return "ogg"
    return "raw"


def generate_enhanced_llm_justification(candidate_name: str,
                                        job_description: str,
                                        component_scores: Dict[str, float],
                                        skill_analysis: Dict[str, Any],
                                        experience_data: Dict[str, Any],
                                        final_score_0_10: float) -> Dict[str, Any]:
    matched_skills = skill_analysis.get('matched_skills', [])
    missing_skills = [s for s in skill_analysis.get('all_jd_skills', []) if s not in matched_skills]

    # FIX: Escaped the entire JSON example structure with {{ and }}
    prompt = f"""
You are a Senior Technical Hiring Manager conducting a thorough and FAIR evaluation of a candidate.

IMPORTANT SCORING GUIDELINES:
- Score of 4.8/10 is below average and should result in "Not Recommended" or "Consider" at best
- Score of 6.0+ should be "Recommend" 
- Score of 7.5+ should be "Strong Recommend"
- Be CONSISTENT between the numerical score and the recommendation decision

**Candidate Profile:**
- Name: {candidate_name}
- Overall Score: {final_score_0_10}/10
- Years Experience: {experience_data.get('total_years_experience', 0)} total, {experience_data.get('technical_years_experience', 0)} technical
- Skills Successfully Matched: {len(matched_skills)}/{skill_analysis.get('total_jd_skills', 0)}

**Component Breakdown (0-10 scale):**
- Skill Match: {component_scores.get('skill_match_score', 0) * 10:.1f}/10
- Skill Context: {component_scores.get('skill_context_score', 0) * 10:.1f}/10  
- Experience Level: {component_scores.get('experience_duration_score', 0) * 10:.1f}/10
- Impact/Achievements: {component_scores.get('impact_score', 0) * 10:.1f}/10
- Projects: {component_scores.get('project_score', 0) * 10:.1f}/10
- Education: {component_scores.get('education_score', 0) * 10:.1f}/10
- Role Relevance: {component_scores.get('relevance_score', 0) * 10:.1f}/10

**DECISION RULES - FOLLOW STRICTLY:**
- Score 0-4.9: "Not Recommended"
- Score 5.0-6.4: "Consider" (with specific conditions)
- Score 6.5-7.4: "Recommend"
- Score 7.5+: "Strong Recommend"

**Job Requirements:**
{job_description[:1000]}...

Provide a comprehensive evaluation as JSON that is CONSISTENT with the {final_score_0_10}/10 score:
{{
    "overall_assessment": {{
        "summary": "2-3 sentence overall evaluation that matches the score level",
        "key_strengths": ["strength1", "strength2", "strength3"],
        "areas_for_improvement": ["area1", "area2"],
        "potential_red_flags": ["flag1"]
    }},
    "skills_evaluation": {{
        "technical_fit": "How well technical skills match (be realistic based on {len(matched_skills)}/{skill_analysis.get('total_jd_skills', 0)} match rate)",
        "skill_gaps": ["critical_gap1", "critical_gap2"],
        "transferable_skills": ["skill1", "skill2"]
    }},
    "experience_assessment": {{
        "experience_level": "junior|mid|senior based on years and complexity",
        "relevant_background": "How background relates to this role",
        "growth_trajectory": "Evidence of career progression"
    }},
    "recommendation": {{
        "decision": "A decision string based on the rules", 
        "confidence": "high|medium|low",
        "reasoning": "Primary factors in decision - must align with the {final_score_0_10}/10 score",
        "interview_focus": ["area1", "area2"]
    }},
    "next_steps": [
        "Specific next step 1 based on the decision",
        "Specific next step 2"  
    ]
}}

CRITICAL: Your recommendation decision MUST align with the {final_score_0_10}/10 score using the decision rules above.
"""
    try:
        raw_response = call_llm_with_fallback(prompt, json_expected=True)
        if not raw_response:
            raise Exception("LLM justification call returned empty.")

        # ... The rest of the function remains the same ...
        parsed = json.loads(raw_response)
        if isinstance(parsed, dict):
            # ... Logic to enforce decision consistency ...
            return parsed

    except Exception as e:
        logger.warning(f"Enhanced LLM justification failed: {e}")

    # Fallback logic... (remains the same)
    if final_score_0_10 >= 7.5:
        decision = "Strong Recommend"
    elif final_score_0_10 >= 6.5:
        decision = "Recommend"
    elif final_score_0_10 >= 5.0:
        decision = "Consider"
    else:
        decision = "Not Recommended"

    return {
        "overall_assessment": {
            "summary": f"Candidate achieved {final_score_0_10}/10 overall fit with notable strengths in matched technical skills.",
            "key_strengths": [f"Matched {len(matched_skills)} required skills"] + matched_skills[:2],
            "areas_for_improvement": missing_skills[:2] if missing_skills else ["Continue skill development"],
            "potential_red_flags": []
        },
        "skills_evaluation": {
            "technical_fit": f"Shows competency in {len(matched_skills)} of {skill_analysis.get('total_jd_skills', 0)} required skills",
            "skill_gaps": missing_skills[:3],
            "transferable_skills": matched_skills[:3]
        },
        "experience_assessment": {
            "experience_level": "junior" if experience_data.get('technical_years_experience', 0) < 2 else (
                "mid" if experience_data.get('technical_years_experience', 0) < 5 else "senior"),
            "relevant_background": "Technical background aligns with role requirements",
            "growth_trajectory": "Shows consistent technical development"
        },
        "recommendation": {
            "decision": decision,
            "confidence": "medium",
            "reasoning": f"Based on {final_score_0_10}/10 overall score and skill matching analysis",
            "interview_focus": ["technical depth", "problem solving"] if decision in ["Recommend", "Strong Recommend",
                                                                                      "Consider"] else [
                "skills assessment"]
        },
        "next_steps": [
            "Conduct technical interview focusing on practical application" if decision in ["Recommend",
                                                                                            "Strong Recommend"] else "Consider skills gap training",
            "Assess cultural fit and communication skills" if decision in ["Recommend",
                                                                           "Strong Recommend"] else "Look for candidates with stronger skill matches"
        ]
    }
