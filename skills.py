import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Set

SKILL_ALIASES = {
    'javascript': ['js', 'ecmascript', 'node.js', 'nodejs', 'node js'],
    'typescript': ['ts'],
    'python': ['py', 'python3', 'python2'],
    'java': ['java8', 'java11', 'java17', 'jdk', 'jre'],
    'c#': ['csharp', 'c sharp', '.net', 'dotnet'],
    'c++': ['cpp', 'c plus plus'],
    'objective-c': ['objc', 'objective c'],
    'go': ['golang'],
    'ruby': ['rb'],
    'php': ['php7', 'php8'],
    'swift': ['ios', 'swiftui'],
    'kotlin': ['kt'],
    'scala': ['sc'],
    'r': ['r-lang', 'rstudio'],

    'react': ['reactjs', 'react.js', 'react js'],
    'vue': ['vuejs', 'vue.js', 'vue js'],
    'angular': ['angularjs', 'angular.js', 'angular js'],
    'express': ['expressjs', 'express.js'],
    'django': ['python django'],
    'flask': ['python flask'],
    'spring': ['spring boot', 'springboot', 'spring framework'],
    'laravel': ['php laravel'],
    'rails': ['ruby on rails', 'rubyonrails', 'ror'],
    'asp.net': ['aspnet', 'asp net'],
    'jquery': ['jquery.js'],
    'bootstrap': ['bootstrap css'],
    'tailwind': ['tailwindcss', 'tailwind css'],

    'postgresql': ['postgres', 'psql'],
    'mysql': ['my sql'],
    'mongodb': ['mongo', 'mongo db'],
    'redis': ['redis cache'],
    'elasticsearch': ['elastic search', 'es'],
    'oracle': ['oracle db', 'oracledb'],
    'sql server': ['sqlserver', 'mssql', 'ms sql'],
    'sqlite': ['sqlite3'],
    'dynamodb': ['dynamo db', 'dynamo'],
    'cassandra': ['apache cassandra'],

    'aws': ['amazon web services', 'amazon aws'],
    'azure': ['microsoft azure', 'ms azure'],
    'gcp': ['google cloud', 'google cloud platform'],
    'docker': ['containerization'],
    'kubernetes': ['k8s', 'k8'],
    'jenkins': ['ci/cd', 'cicd'],
    'terraform': ['iac', 'infrastructure as code'],
    'ansible': ['configuration management'],
    'git': ['github', 'gitlab', 'bitbucket', 'version control'],
    'ci/cd': ['continuous integration', 'continuous deployment', 'cicd'],

    'rest': ['rest api', 'restful', 'restful api'],
    'graphql': ['graph ql'],
    'microservices': ['micro services', 'service oriented architecture', 'soa'],
    'machine learning': ['ml', 'artificial intelligence', 'ai'],
    'deep learning': ['dl', 'neural networks'],
    'data science': ['ds', 'data analysis'],
    'big data': ['bigdata', 'hadoop', 'spark'],
    'blockchain': ['bitcoin', 'ethereum', 'crypto'],
    'api': ['apis', 'web services'],
    'json': ['javascript object notation'],
    'xml': ['extensible markup language'],
    'html': ['html5', 'hypertext markup language'],
    'css': ['css3', 'cascading style sheets'],
    'sass': ['scss'],
    'less': ['lesscss'],
    'webpack': ['bundler'],
    'babel': ['transpiler'],
    'npm': ['node package manager'],
    'yarn': ['package manager'],
    'agile': ['scrum', 'kanban'],
    'tdd': ['test driven development'],
    'bdd': ['behavior driven development'],
}


def normalize_skill(skill: str) -> str:
    skill_lower = skill.lower().strip()
    skill_lower = re.sub(r'^(using|with|in)\s+', '', skill_lower)
    skill_lower = re.sub(r'\s+(programming|development|framework|library|database|tool)$', '', skill_lower)

    for canonical, aliases in SKILL_ALIASES.items():
        if skill_lower == canonical or skill_lower in aliases:
            return canonical
    return skill_lower


def create_skill_variants(skill: str) -> Set[str]:
    variants = set()
    normalized = normalize_skill(skill)
    variants.add(normalized)
    variants.add(skill.lower().strip())

    if normalized in SKILL_ALIASES:
        variants.update(SKILL_ALIASES[normalized])

    if ' ' in normalized:
        variants.add(normalized.replace(' ', ''))
        variants.add(normalized.replace(' ', '.'))
        variants.add(normalized.replace(' ', '-'))
    return variants


def fuzzy_match_score(text1: str, text2: str) -> float:
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def find_skill_matches(jd_skills: List[str], resume_text: str, resume_skills: List[str]) -> Dict[str, Any]:
    resume_text_lower = resume_text.lower()
    matched_skills = []
    skill_evidence = {}
    confidence_scores = {}

    for jd_skill in jd_skills:
        jd_skill_variants = create_skill_variants(jd_skill)
        best_match_score = 0.0
        evidence_snippets = []

        for variant in jd_skill_variants:
            if variant in resume_text_lower:
                best_match_score = max(best_match_score, 1.0)
                pattern = re.escape(variant)
                matches = list(re.finditer(pattern, resume_text_lower))
                for match in matches:
                    start = max(0, match.start() - 30)
                    end = min(len(resume_text), match.end() + 30)
                    evidence_snippets.append(resume_text[start:end].strip())

        for resume_skill in resume_skills:
            resume_variants = create_skill_variants(resume_skill)
            for jd_variant in jd_skill_variants:
                for resume_variant in resume_variants:
                    if jd_variant == resume_variant:
                        best_match_score = max(best_match_score, 1.0)
                    else:
                        fuzzy_score = fuzzy_match_score(jd_variant, resume_variant)
                        if fuzzy_score >= 0.85:
                            best_match_score = max(best_match_score, fuzzy_score)

        if best_match_score < 0.5:
            jd_words = set(jd_skill.lower().split())
            resume_words = set(resume_text_lower.split())

            if len(jd_words) > 1:
                word_matches = jd_words.intersection(resume_words)
                if len(word_matches) >= len(jd_words) * 0.6:
                    partial_score = len(word_matches) / len(jd_words) * 0.7
                    best_match_score = max(best_match_score, partial_score)

        if best_match_score >= 0.5:
            matched_skills.append(jd_skill)
            skill_evidence[jd_skill] = evidence_snippets[:3]
            confidence_scores[jd_skill] = best_match_score

    return {
        'matched_skills': matched_skills,
        'skill_evidence': skill_evidence,
        'confidence_scores': confidence_scores,
        'total_jd_skills': len(jd_skills),
        'match_rate': len(matched_skills) / max(1, len(jd_skills))
    }
