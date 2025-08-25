import re
from typing import Any, Dict, List

from skills import find_skill_matches


def compute_enhanced_component_scores(job_desc: str, resume_text: str,
                                      jd_skills: List[str], resume_skills: List[str],
                                      experience_data: Dict[str, Any]) -> Dict[str, Any]:
    skill_analysis = find_skill_matches(jd_skills, resume_text, resume_skills)

    base_match_rate = skill_analysis['match_rate']
    confidence_weighted_score = 0
    if skill_analysis['confidence_scores']:
        total_weight = sum(skill_analysis['confidence_scores'].values())
        confidence_weighted_score = total_weight / len(jd_skills) if total_weight > 0 else 0

    skill_match_score = (base_match_rate * 0.7 + confidence_weighted_score * 0.3)
    skill_match_score = min(1.0, skill_match_score)

    skills_with_context = 0
    total_matched_skills = len(skill_analysis['matched_skills'])

    if total_matched_skills > 0:
        for skill in skill_analysis['matched_skills']:
            evidence = skill_analysis['skill_evidence'].get(skill, [])
            if evidence:
                experience_keywords = ['experience', 'worked', 'developed', 'built', 'created', 'managed', 'led',
                                       'implemented']
                for snippet in evidence:
                    snippet_lower = snippet.lower()
                    if any(keyword in snippet_lower for keyword in experience_keywords):
                        skills_with_context += 1
                        break

    skill_context_score = skills_with_context / max(1, total_matched_skills) if total_matched_skills > 0 else 0

    total_years = experience_data.get('total_years_experience', 0)
    technical_years = experience_data.get('technical_years_experience', 0)

    if technical_years >= 5:
        experience_duration_score = 1.0
    elif technical_years >= 3:
        experience_duration_score = 0.8 + (technical_years - 3) * 0.1
    elif technical_years >= 1:
        experience_duration_score = 0.4 + (technical_years - 1) * 0.2
    elif technical_years >= 0.5:
        experience_duration_score = 0.2 + (technical_years - 0.5) * 0.4
    else:
        experience_duration_score = technical_years * 0.4

    impact_indicators = [
        r'\d+%\s*(?:increase|improvement|reduction|growth|faster|better)',
        r'\$\d+[kmb]?\s*(?:saved|revenue|budget|cost)',
        r'\d+\s*(?:users|customers|clients|projects|applications)',
        r'(?:increased|improved|reduced|optimized|enhanced).*?\d+',
        r'\d+x\s*(?:faster|improvement|increase)',
        r'(?:led|managed)\s+(?:team of\s+)?\d+',
    ]

    impact_count = 0
    for pattern in impact_indicators:
        matches = re.findall(pattern, resume_text, re.IGNORECASE)
        impact_count += len(matches)

    if impact_count >= 5:
        impact_score = 1.0
    elif impact_count >= 3:
        impact_score = 0.8
    elif impact_count >= 1:
        impact_score = 0.6
    else:
        action_verbs = ['developed', 'built', 'created', 'designed', 'implemented', 'optimized', 'improved', 'led',
                        'managed']
        action_count = sum(1 for verb in action_verbs if verb in resume_text.lower())
        impact_score = min(0.4, action_count * 0.05)

    project_indicators = [
        r'\b(?:project|projects|portfolio|github|personal\s+work)\b',
        r'\b(?:built|created|developed).*?(?:application|app|website|system|tool)\b',
        r'\b(?:side\s+project|open\s+source|hackathon|competition)\b'
    ]

    project_score = 0
    for pattern in project_indicators:
        if re.search(pattern, resume_text, re.IGNORECASE):
            project_score += 0.3
    project_score = min(1.0, project_score)

    education_indicators = {
        'phd': 1.0,
        'ph.d': 1.0,
        'doctorate': 1.0,
        'master': 0.9,
        'm.s': 0.9,
        'msc': 0.9,
        'mba': 0.8,
        'bachelor': 0.7,
        'b.s': 0.7,
        'bsc': 0.7,
        'associate': 0.5,
        'certification': 0.4,
        'bootcamp': 0.4,
        'diploma': 0.3
    }

    education_score = 0.3
    resume_lower = resume_text.lower()
    for term, score in education_indicators.items():
        if term in resume_lower:
            education_score = max(education_score, score)
            break

    job_desc_lower = job_desc.lower()
    job_types = {
        'frontend': ['frontend', 'front-end', 'react', 'vue', 'angular', 'javascript', 'html', 'css'],
        'backend': ['backend', 'back-end', 'api', 'server', 'database', 'python', 'java', 'node'],
        'fullstack': ['fullstack', 'full-stack', 'full stack'],
        'devops': ['devops', 'infrastructure', 'aws', 'docker', 'kubernetes', 'ci/cd'],
        'data': ['data science', 'machine learning', 'analytics', 'python', 'sql', 'statistics'],
        'mobile': ['mobile', 'ios', 'android', 'react native', 'flutter', 'swift', 'kotlin']
    }

    job_type_matches = {}
    for job_type, keywords in job_types.items():
        job_match_count = sum(1 for keyword in keywords if keyword in job_desc_lower)
        resume_match_count = sum(1 for keyword in keywords if keyword in resume_lower)
        if job_match_count > 0:
            job_type_matches[job_type] = (resume_match_count / len(keywords), job_match_count)

    relevance_score = 0.5
    if job_type_matches:
        relevance_score = max(match[0] for match in job_type_matches.values())
        relevance_score = min(1.0, relevance_score + 0.3)

    return {
        "skill_match_score": float(skill_match_score),
        "skill_context_score": float(skill_context_score),
        "experience_duration_score": float(experience_duration_score),
        "impact_score": float(impact_score),
        "project_score": float(project_score),
        "education_score": float(education_score),
        "relevance_score": float(relevance_score),
        "matched_skills": skill_analysis['matched_skills'],
        "skill_evidence": skill_analysis['skill_evidence'],
        "confidence_scores": skill_analysis['confidence_scores'],
        "years_experience_estimate": total_years,
        "technical_years_estimate": technical_years,
        "total_jd_skills": len(jd_skills),
        "match_statistics": {
            "skills_matched": len(skill_analysis['matched_skills']),
            "skills_with_evidence": len([s for s in skill_analysis['skill_evidence'].values() if s]),
            "average_confidence": sum(skill_analysis['confidence_scores'].values()) / max(1, len(
                skill_analysis['confidence_scores'])),
            "impact_indicators_found": impact_count
        }
    }


def aggregate_enhanced_scores(component_scores: Dict[str, float]) -> Dict[str, Any]:
    weights = {
        "skill_match_score": 0.25,
        "skill_context_score": 0.15,
        "experience_duration_score": 0.20,
        "impact_score": 0.10,
        "project_score": 0.10,
        "education_score": 0.10,
        "relevance_score": 0.10
    }

    total_score = 0.0
    for component, weight in weights.items():
        if component in component_scores:
            total_score += weight * component_scores[component]

    score_components = {k: v for k, v in component_scores.items()
                        if k.endswith('_score') and isinstance(v, (int, float))}

    component_count = sum(1 for score in score_components.values() if score > 0.3)
    if component_count >= 5:
        total_score *= 1.1
    elif component_count <= 2:
        total_score *= 0.9

    final_score_0_100 = min(100.0, total_score * 100)
    final_score_0_10 = round(final_score_0_100 / 10.0, 2)

    per_component_0_10 = {
        k: round(component_scores.get(k, 0.0) * 10.0, 1)
        for k in weights.keys() if k in component_scores
    }

    return {
        "score_0_100": round(final_score_0_100, 1),
        "score_0_10": final_score_0_10,
        "per_component_0_10": per_component_0_10,
        "weights_used": weights
    }
