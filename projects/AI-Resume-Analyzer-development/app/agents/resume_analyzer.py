import re

from dotenv import load_dotenv
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

from app.core import GROQ_API_KEY, HF_MODEL
from app.rag.knowledge_base import get_knowledge_base
from app.rag.retriever import Retriever
from app.schemas.job import JobOut
from app.schemas.matching import MatchResult
from app.schemas.resume import ContactInfo, EducationEntry, ExperienceEntry, ProjectEntry, ResumeAnalysis, ResumeImprovementOut, SkillSet
from app.services.groq import complete_json

load_dotenv()

_retriever: Retriever | None = None


def _ensure_kb() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever(get_knowledge_base())
    return _retriever


_SYSTEM_PROMPT = """You are a strict resume analysis agent.
Use only the supplied resume text and retrieved resume-writing guidelines.
Do not invent education, experience, dates, skills, certifications, or achievements.
Extract technical skills, soft skills, education, experience, a third-person summary, weaknesses, certifications, and learning resources.
Return raw JSON only, with empty arrays or null fields when evidence is absent.

Retrieved resume-writing guidelines:
{guidelines}

{format_instructions}
"""


async def analyze_resume(text: str) -> ResumeAnalysis:
    if GROQ_API_KEY:
        try:
            return await _groq_analysis(text)
        except Exception:
            pass
    return _keyword_analysis(text)


async def _groq_analysis(text: str) -> ResumeAnalysis:
    guidelines = _ensure_kb().retrieve_as_context(
        text[:800], top_k=4, category="resume_guideline", mode="keyword"
    )
    system_prompt = """You are a strict resume analyzer. Use only the supplied resume text and retrieved resume-writing guidelines. Never invent facts. Return one JSON object with keys: score, summary, strengths, weaknesses, improvements, skills, contact, full_name, education, experience, projects, certifications, training, languages, achievements, and learning_resources. Every extracted value must be copied or directly supported by the resume. Use null or empty arrays when evidence is absent. Recommendations must not ask the user to claim unsupported experience."""
    user_prompt = f"Retrieved guidelines:\n{guidelines}\n\nResume text:\n{text[:12000]}"
    payload = await complete_json(system_prompt, user_prompt)
    model_analysis = ResumeAnalysis(
        full_name=payload.get("full_name"),
        contact=ContactInfo(**(payload.get("contact") or {})),
        skills=SkillSet(**(payload.get("skills") or {})),
        education=payload.get("education") or [],
        experience=payload.get("experience") or [],
        projects=payload.get("projects") or [],
        certifications=_string_list(payload.get("certifications")),
        training=_string_list(payload.get("training")),
        languages=_string_list(payload.get("languages")),
        achievements=_string_list(payload.get("achievements")),
        summary=str(payload.get("summary") or ""),
        score=_clamp_score(payload.get("score")),
        strengths=_string_list(payload.get("strengths")),
        weaknesses=_string_list(payload.get("weaknesses")),
        improvements=_string_list(payload.get("improvements")),
        learning_resources=_string_list(payload.get("learning_resources")),
    )
    return _merge_validated_analysis(text, model_analysis)


async def get_improvement_recommendations(
    text: str,
    analysis: ResumeAnalysis | None = None,
    job: JobOut | None = None,
    match_result: MatchResult | None = None,
) -> ResumeImprovementOut:
    if analysis is None:
        analysis = await analyze_resume(text)
    if job is None:
        categories = _build_general_recommendation_categories(text, analysis)
        return ResumeImprovementOut(
            scope="general",
            resume_id=0,
            job_id=None,
            job_title=None,
            job_company=None,
            score=analysis.score,
            strengths=analysis.strengths,
            weaknesses=analysis.weaknesses,
            recommendations=_build_general_recommendations(analysis),
            high_priority_fixes=categories["high_priority_fixes"],
            impact_metrics=categories["impact_metrics"],
            skills_ats_optimization=categories["skills_ats_optimization"],
            professional_summary_polish=categories["professional_summary_polish"],
            certifications=analysis.certifications,
            learning_resources=analysis.learning_resources,
        )
    if match_result is None:
        raise ValueError("Match evidence is required for job-specific recommendations.")

    recommendations = _build_job_recommendations(analysis, job, match_result)
    categories = _build_recommendation_categories(text, analysis, job, match_result)
    return ResumeImprovementOut(
        scope="job_specific",
        resume_id=0,
        job_id=job.id,
        job_title=job.title,
        job_company=job.company,
        score=analysis.score,
        strengths=analysis.strengths,
        weaknesses=analysis.weaknesses,
        recommendations=recommendations,
        high_priority_fixes=categories["high_priority_fixes"],
        impact_metrics=categories["impact_metrics"],
        skills_ats_optimization=categories["skills_ats_optimization"],
        professional_summary_polish=categories["professional_summary_polish"],
        certifications=analysis.certifications,
        learning_resources=analysis.learning_resources,
    )


def _build_general_recommendations(analysis: ResumeAnalysis) -> list[str]:
    verified_skills = ", ".join((analysis.skills.technical + analysis.skills.soft)[:8])
    evidence = ", ".join(
        [entry.title for entry in analysis.experience if entry.title]
        + [project.name for project in analysis.projects if project.name]
    )
    recommendations = [
        f"Rewrite the opening summary around the verified direction already visible in the CV, such as {verified_skills or 'the strongest documented technical capabilities'}, and state the type of contribution you want next without adding unsupported seniority or qualifications.",
        "Rewrite task-heavy experience bullets with STAR: state the situation or scale, the action you personally took, the method or tool, and the verified result; use a precise qualitative outcome when the CV does not contain a number.",
        "Keep the strongest evidence first in each role and project, then remove repeated tool lists so the reader can quickly see ownership, method, and outcome rather than only activity.",
        "Use the existing evidence from " + (evidence or "the strongest documented experience") + " to build a consistent narrative across the summary, experience, and projects sections; do not add a skill or achievement that is not present in the CV.",
    ]
    if not analysis.skills.soft:
        recommendations.append("Add one truthful behavioral example under a documented role or project, showing collaboration, communication, ownership, or leadership through an action and outcome rather than inserting an unsupported keyword.")
    return recommendations[:5]


def _build_general_recommendation_categories(text: str, analysis: ResumeAnalysis) -> dict[str, list[str]]:
    categories: dict[str, list[str]] = {
        "high_priority_fixes": [],
        "impact_metrics": [],
        "skills_ats_optimization": [],
        "professional_summary_polish": [],
    }
    if not analysis.summary.strip():
        categories["high_priority_fixes"].append("Add a concise professional summary that names the verified specialization, strongest evidence, and intended direction; do not claim a title, level, or capability that the CV does not support.")
    if analysis.projects:
        dense = next((project.name for project in analysis.projects if project.name and project.description and len(project.description.split()) > 55), None)
        if dense:
            categories["high_priority_fixes"].append(f"Reduce the scanning burden in {dense}: separate the problem, your contribution, implementation, and verified result into distinct bullets before secondary tools or background detail.")
    if not categories["high_priority_fixes"]:
        categories["high_priority_fixes"].append("Prioritize the first page: lead with the verified role direction, strongest experience evidence, and one or two projects that best demonstrate delivery instead of opening with an undifferentiated skills inventory.")

    measure_source = " ".join(
        [entry.description for entry in analysis.experience if entry.description]
        + [project.description for project in analysis.projects if project.description]
    )
    verified_measures = list(dict.fromkeys(item.strip() for item in re.findall(r"\b\d[\d,.]*(?:\+|%|\s*(?:ms|mAP@\d+|million|M|K))?\b", measure_source, re.I) if any(char.isdigit() for char in item)))
    if verified_measures:
        categories["impact_metrics"].append(f"Use STAR bullets and preserve the CV's verified measures, such as {', '.join(verified_measures[:6])}: state the situation or scale, your personal action, the method, and the result without inflating the figures.")
    else:
        categories["impact_metrics"].append("For each task-only bullet, identify a truthful scope or outcome such as records processed, latency, error reduction, adoption, or delivery reliability; if no number is documented, use a precise qualitative result instead of inventing one.")
    if analysis.experience:
        role = next((entry.title for entry in analysis.experience if entry.title), "the strongest role")
        categories["impact_metrics"].append(f"Start with the clearest outcome from {role}, then place the tool or method beside it so the reader can see ownership and impact without inferring it from a task list.")

    verified_skills = analysis.skills.technical + analysis.skills.soft
    if verified_skills:
        categories["skills_ats_optimization"].append(f"Group and repeat the CV-supported keywords naturally in the headline, summary, and relevant bullets: {', '.join(verified_skills[:10])}. Remove duplicates and do not add an unverified keyword simply to improve ATS density.")
    else:
        categories["skills_ats_optimization"].append("Build an ATS-readable skills section from technologies explicitly demonstrated in the CV, grouped consistently by language, framework, tool, data, and domain; do not add technologies that appear nowhere in the source text.")
    categories["skills_ats_optimization"].append("Mirror the exact terminology used by the roles you apply to only when the CV contains corresponding evidence; otherwise mark the capability as a development goal rather than an existing skill.")

    evidence = ", ".join(([entry.title for entry in analysis.experience if entry.title] + [project.name for project in analysis.projects if project.name])[:4]) or "the strongest verified experience"
    categories["professional_summary_polish"].append(f"Rewrite the summary in three sentences: verified specialization; strongest proof from {evidence}; and the contribution you want to make next. Keep every claim anchored to the selected CV.")
    categories["professional_summary_polish"].append("Place the most relevant evidence in the first two lines, keep the summary concise, and move secondary tools, training, and certifications into their dedicated sections.")
    return categories


def _build_job_recommendations(
    analysis: ResumeAnalysis,
    job: JobOut,
    match_result: MatchResult,
) -> list[str]:
    recommendations: list[str] = []
    matched = list(dict.fromkeys(match_result.matched_skills + match_result.matched_requirements))
    missing = list(dict.fromkeys(match_result.missing_skills + match_result.missing_requirements))
    partial = list(dict.fromkeys(match_result.partially_matched))
    evidence_terms = ", ".join(matched[:6]) if matched else "the verified skills already present in the CV"
    job_label = job.title + (f" at {job.company}" if job.company else "")

    recommendations.append(
        f"Target this version to {job_label}: keep the headline and opening summary focused on the selected role, then foreground only CV-supported evidence that matches the job, including {evidence_terms}. Do not add an unmatched requirement as if it were already held."
    )
    if missing:
        missing_text = ", ".join(missing[:6])
        recommendations.append(
            f"Bridge the actual gaps first: {missing_text}. For each gap, either add a truthful example already present elsewhere in the CV, or label it as a development goal; never claim the requirement without source evidence."
        )
    if partial:
        partial_text = ", ".join(partial[:5])
        recommendations.append(
            f"Clarify the partial evidence for {partial_text}. Rewrite the relevant bullet with the exact scope, method, and outcome already supported by the CV so the recruiter can see what is transferable to {job.title}."
        )
    if analysis.experience:
        role = next((entry for entry in analysis.experience if entry.title), analysis.experience[0])
        recommendations.append(
            f"Rewrite {role.title or 'the strongest experience'} for {job.title} using STAR: state the context or scale, your personal action, the job-relevant technology or method, and the verified outcome. Put the strongest job-matching evidence in the first bullet."
        )
    if analysis.projects:
        project = next((item for item in analysis.projects if item.name), analysis.projects[0])
        recommendations.append(
            f"Use {project.name or 'the strongest project'} as supporting evidence for {job.title}: separate the problem, your contribution, implementation, and result into concise bullets, and keep every metric tied to the project text."
        )
    if not analysis.skills.soft:
        recommendations.append(
            f"Add one truthful behavioral example under the most relevant role or project for {job.title}, showing collaboration, communication, ownership, or leadership through an action and outcome rather than inserting an unsupported keyword."
        )
    return recommendations[:6]


def _build_recommendation_categories(
    text: str,
    analysis: ResumeAnalysis,
    job: JobOut,
    match_result: MatchResult,
) -> dict[str, list[str]]:
    matched = list(dict.fromkeys(match_result.matched_skills + match_result.matched_requirements))
    missing = list(dict.fromkeys(match_result.missing_skills + match_result.missing_requirements))
    partial = list(dict.fromkeys(match_result.partially_matched))
    job_label = job.title + (f" at {job.company}" if job.company else "")
    categories: dict[str, list[str]] = {
        "high_priority_fixes": [],
        "impact_metrics": [],
        "skills_ats_optimization": [],
        "professional_summary_polish": [],
    }

    gap_items = missing + partial
    if gap_items:
        categories["high_priority_fixes"].append(
            f"For {job_label}, address the evidence gaps in this order: {', '.join(gap_items[:6])}. "
            "Keep each item labeled as missing or partial unless the CV already contains direct proof; do not upgrade a qualification or imply experience that is not documented."
        )
    if analysis.projects:
        dense = next((project.name for project in analysis.projects if project.name and project.description and len(project.description.split()) > 55), None)
        if dense:
            categories["high_priority_fixes"].append(
                f"Reduce the scanning burden in {dense}: place the problem, your personal contribution, the implementation, and the verified result in separate bullets before secondary tools or background detail."
            )
    if not categories["high_priority_fixes"]:
        categories["high_priority_fixes"].append(
            f"Make the first half of the CV immediately prove fit for {job_label}: lead with the strongest verified role, project, and outcome instead of a broad skills inventory."
        )

    measure_source = " ".join(
        [entry.description for entry in analysis.experience if entry.description]
        + [project.description for project in analysis.projects if project.description]
    )
    verified_measures = re.findall(
        r"\b\d[\d,.]*(?:\+|%|\s*(?:ms|mAP@\d+|million|M|K))?\b",
        measure_source,
        re.I,
    )
    verified_measures = list(dict.fromkeys(item.strip() for item in verified_measures if any(char.isdigit() for char in item)))
    if verified_measures:
        categories["impact_metrics"].append(
            f"Use STAR bullets and preserve the CV's verified measures, such as {', '.join(verified_measures[:6])}: state the situation or scale, the action you personally took, the method, and the result."
        )
    else:
        categories["impact_metrics"].append(
            "Rewrite task-only bullets with STAR and add a verified scope or outcome such as records processed, latency, error reduction, adoption, or delivery reliability; if the CV does not contain a number, use a precise qualitative result rather than inventing one."
        )
    if analysis.experience:
        role = next((entry.title for entry in analysis.experience if entry.title), "the strongest role")
        categories["impact_metrics"].append(
            f"Start with the strongest outcome from {role}, then move the tool or method into the same bullet so a recruiter can see ownership and impact without inferring it from a task list."
        )

    if matched:
        categories["skills_ats_optimization"].append(
            f"Prioritize the selected-job keywords already supported by the CV: {', '.join(matched[:10])}. Repeat them naturally in the headline, summary, and the relevant experience or project bullets; do not add a keyword without evidence."
        )
    if missing:
        categories["skills_ats_optimization"].append(
            f"For missing requirements ({', '.join(missing[:6])}), either add a truthful example already present elsewhere in the CV or list the capability as a development goal. Never present a missing requirement as an existing skill."
        )
    elif not categories["skills_ats_optimization"]:
        categories["skills_ats_optimization"].append(
            "Keep the skills section ATS-readable: group verified technologies consistently and remove duplicates or broad terms that are not supported by the CV text."
        )

    roles = [entry.title for entry in analysis.experience if entry.title]
    projects = [project.name for project in analysis.projects if project.name]
    evidence = ", ".join((roles + projects)[:4]) or "the strongest verified experience"
    categories["professional_summary_polish"].append(
        f"Rewrite the opening summary for {job_label} in three sentences: target role and verified specialization; strongest proof from {evidence}; then the contribution you want to make next. Keep the summary anchored to the selected CV and avoid unsupported seniority, metrics, or qualifications."
    )
    categories["professional_summary_polish"].append(
        "Move the most relevant evidence into the first two lines and reserve secondary tools or training for later sections so the recruiter sees the role fit before the full inventory."
    )
    return categories


def _string_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _clamp_score(value) -> float:
    try:
        return round(min(100.0, max(0.0, float(value))), 1)
    except (TypeError, ValueError):
        return 0.0


async def _langchain_analysis(text: str) -> ResumeAnalysis:
    guidelines = _ensure_kb().retrieve_as_context(
        text[:800], top_k=3, category="resume_guideline", mode="hybrid"
    )
    llm = HuggingFaceEndpoint(repo_id=HF_MODEL, task="text-generation")
    chat = ChatHuggingFace(llm=llm)
    parser = JsonOutputParser(pydantic_object=ResumeAnalysis)
    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        ("user", "--- RESUME TEXT ---\n{resume_text}\n--- END RESUME ---"),
    ]).partial(
        format_instructions=parser.get_format_instructions(),
        guidelines=guidelines,
    )
    result = await (prompt | chat | parser).ainvoke({"resume_text": text[:12000]})
    return ResumeAnalysis(**result)


_TECH_PATTERNS = {
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "ruby", "php", "swift", "kotlin", "sql", "html", "css", "react", "angular",
    "vue", "node.js", "nodejs", "django", "flask", "fastapi", "docker", "kubernetes",
    "aws", "azure", "gcp", "git", "linux", "tensorflow", "pytorch", "pandas",
    "numpy", "mongodb", "postgresql", "postgres", "mysql", "redis", "graphql", "devops",
    "machine learning", "data science", "agile", "scrum", "rest api", "microservices",
}

_SOFT_PATTERNS = {
    "leadership", "communication", "teamwork", "problem solving", "critical thinking",
    "time management", "adaptability", "creativity", "collaboration", "project management",
    "mentoring", "negotiation", "presentation", "ownership",
}

_SOFT_EVIDENCE_PATTERNS = {
    "leadership": r"\b(?:led|lead|managed|owned)\b",
    "collaboration": r"\b(?:collaborat\w*|cross[- ]functional|teamwork|teams?)\b",
    "mentoring": r"\b(?:mentored|coached|trained|training cohorts?|learners?)\b",
    "communication": r"\b(?:presented|stakeholders?|weekly insight reports?)\b",
}

_CERT_MAP = {
    "aws": "AWS Certified Cloud Practitioner",
    "azure": "Microsoft Certified: Azure Fundamentals",
    "gcp": "Google Cloud Digital Leader",
    "python": "PCEP - Certified Entry-Level Python Programmer",
    "docker": "Docker Certified Associate",
    "kubernetes": "Certified Kubernetes Application Developer (CKAD)",
    "machine learning": "DeepLearning.AI Machine Learning Specialization",
    "data science": "IBM Data Science Professional Certificate",
    "sql": "Microsoft Certified: Azure Data Fundamentals",
    "agile": "PMI Agile Certified Practitioner (PMI-ACP)",
    "scrum": "Certified ScrumMaster (CSM)",
    "project management": "Google Project Management Certificate",
}

_SECTION_NAMES = {
    "education", "academic background", "qualifications", "experience", "work experience",
    "professional experience", "employment", "skills", "technical skills", "soft skills",
    "summary", "professional summary", "profile", "objective", "certifications", "certificates", "projects", "key projects",
    "training", "courses", "coursework", "languages", "achievements", "awards", "honors",
}


def _clean_line(line: str) -> str:
    return re.sub(r"^\s*(?:[-*•▪◦]|\d+[.)])\s*", "", line).strip()


def _section_lines(text: str, names: set[str]) -> list[str]:
    lines = [_clean_line(line) for line in text.splitlines()]
    active = False
    collected: list[str] = []
    for line in lines:
        heading = re.sub(r"[:|]$", "", line.lower()).strip()
        if heading in _SECTION_NAMES:
            active = heading in names
            continue
        if active:
            if heading in _SECTION_NAMES:
                break
            if line:
                collected.append(line)
    return collected


def _find_skills(text: str, patterns: set[str]) -> list[str]:
    lower = text.lower()
    found = []
    for pattern in sorted(patterns, key=len, reverse=True):
        expression = rf"(?<![a-z0-9]){re.escape(pattern)}(?![a-z0-9])"
        if re.search(expression, lower):
            found.append(pattern.replace("nodejs", "node.js"))
    return sorted(set(found))


def _extract_soft_skills(text: str) -> list[str]:
    found = set(_find_skills(text, _SOFT_PATTERNS))
    lower = text.lower()
    for label, expression in _SOFT_EVIDENCE_PATTERNS.items():
        if re.search(expression, lower):
            found.add(label)
    return sorted(found)


def _behavioral_anchor(experience: list[ExperienceEntry]) -> str:
    for entry in experience:
        evidence = f"{entry.title or ''} {entry.description or ''}"
        if re.search(r"\b(?:led|lead|managed|owned|mentor\w*|coach\w*|train\w*|collaborat\w*|cross[- ]functional|team\w*)\b", evidence, re.I):
            return entry.title or "the strongest role"
    return next((entry.title for entry in experience if entry.title), "the strongest role")


def _extract_year(line: str) -> str | None:
    month = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    range_match = re.search(rf"\b(?:{month}\s+)?((?:19|20)\d{{2}})\s*[-–]\s*(?:(?:{month})\s+)?((?:19|20)\d{{2}}|present|current)\b", line, re.I)
    if range_match:
        return range_match.group(0).strip()
    single_match = re.search(r"\b((?:19|20)\d{2})\b", line, re.I)
    return single_match.group(0).strip() if single_match else None


def _extract_education(text: str) -> list[EducationEntry]:
    lines = _section_lines(text, {"education", "academic background", "qualifications"})
    if not lines:
        lines = [
            _clean_line(line) for line in text.splitlines()
            if re.search(r"\b(bachelor|master|phd|doctorate|degree|diploma|university|college)\b", line, re.I)
        ]
    entries: list[EducationEntry] = []
    for line in lines:
        degree_match = re.search(r"\b((?:bachelor|master|phd|doctorate|associate|diploma|b\.?\s*sc\.?|b\.?\s*s\.?|b\.?\s*a\.?|m\.?\s*sc\.?|m\.?\s*s\.?|m\.?\s*a\.?)[^,;|\n]*)", line, re.I)
        institution_match = re.search(r"\b([A-Z][A-Za-z&.' -]*(?:University|College|Institute|School))\b", line)
        year = _extract_year(line)
        degree = degree_match.group(1).strip(" -,:;") if degree_match else None
        institution = institution_match.group(1).strip() if institution_match else None
        if degree or institution or year:
            entries.append(EducationEntry(degree=degree, institution=institution, year=year, details=line))
    return _unique_models(entries, ("degree", "institution", "year"))


def _extract_experience(text: str) -> list[ExperienceEntry]:
    lines = _section_lines(text, {"experience", "work experience", "professional experience", "employment"})
    if not lines:
        lines = [_clean_line(line) for line in text.splitlines() if re.search(r"\b(at|@)\b|\b(?:19|20)\d{2}\s*[-–]", line, re.I)]
    entries: list[ExperienceEntry] = []
    for index, line in enumerate(lines):
        duration = _extract_year(line)
        role_match = re.match(r"(.+?)(?:\s+at\s+|\s+@\s+|\s*\|\s*)", line, re.I)
        company_match = re.search(r"(?:\s+at\s+|\s+@\s+)([^,|\d]+)", line, re.I)
        title = role_match.group(1).strip() if role_match else None
        company = company_match.group(1).strip() if company_match else None
        if role_match and "|" in line and not company:
            pipe_parts = [part.strip() for part in line.split("|") if part.strip()]
            if len(pipe_parts) >= 2:
                title = pipe_parts[0]
                company = re.sub(r"\s*(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)?\s*(?:19|20)\d{2}.*$", "", pipe_parts[1], flags=re.I).strip(" ,-") or pipe_parts[1]
        if duration and not (title or company):
            without_duration = re.sub(re.escape(duration), "", line, flags=re.I).strip(" ,|-")
            parts = [part.strip() for part in re.split(r"\s*[|,]\s*", without_duration) if part.strip()]
            if len(parts) >= 2:
                title, company = parts[0], parts[1]
        if not (duration or title or company) or (not duration and not role_match):
            continue
        if not title and duration:
            title = re.sub(r"\b(?:19|20)\d{2}\s*[-–]\s*(?:19|20)\d{2}|\bpresent\b|\bcurrent\b", "", line, flags=re.I).strip(" -|,")
        description_lines = []
        for following in lines[index + 1:index + 3]:
            if not _extract_year(following) and not re.search(r"\s+at\s+|\s+@\s+|\s*\|\s*", following, re.I):
                description_lines.append(following)
        if title or company or duration:
            entries.append(ExperienceEntry(
                title=title,
                company=company,
                duration=duration,
                description=" ".join(description_lines) or line,
            ))
    return _unique_models(entries, ("title", "company", "duration"))


def _unique_models(entries: list, fields: tuple[str, ...]) -> list:
    seen = set()
    result = []
    for entry in entries:
        key = tuple(getattr(entry, field) for field in fields)
        if key not in seen:
            seen.add(key)
            result.append(entry)
    return result[:10]


_PROGRAMMING_PATTERNS = {"python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "ruby", "php", "swift", "kotlin"}
_FRAMEWORK_PATTERNS = {"react", "angular", "vue", "django", "flask", "fastapi", "tensorflow", "pytorch"}
_LIBRARY_PATTERNS = {"pandas", "numpy", "scikit-learn", "graphql"}
_TOOL_PATTERNS = {"git", "linux", "docker", "kubernetes", "agile", "scrum", "devops"}
_DATABASE_PATTERNS = {"sql", "mongodb", "postgresql", "postgres", "mysql", "redis"}
_CLOUD_PATTERNS = {"aws", "azure", "gcp"}
_ML_PATTERNS = {"machine learning", "deep learning", "scikit-learn", "tensorflow", "pytorch"}
_DATA_PATTERNS = {"data science", "pandas", "numpy", "sql"}
_AI_PATTERNS = {"artificial intelligence", "ai", "machine learning", "deep learning"}
_COMPUTER_VISION_PATTERNS = {"computer vision", "opencv"}
_NLP_PATTERNS = {"nlp", "natural language processing", "spacy", "nltk", "transformers"}


def _first_resume_name(text: str) -> str | None:
    for raw_line in text.splitlines()[:8]:
        line = _clean_line(raw_line)
        if not line or re.search(r"@|https?://|\d", line):
            continue
        if re.match(r"^(name|contact|email|phone|address)\s*:", line, re.I):
            candidate = re.sub(r"^[^:]+:\s*", "", line).strip()
        else:
            candidate = line
        words = candidate.split()
        if 2 <= len(words) <= 5 and all(re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", word) for word in words):
            if candidate.lower() not in _SECTION_NAMES:
                return candidate
    return None


def _extract_contact(text: str) -> ContactInfo:
    email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I)
    phone_candidates = re.findall(r"(?:\+?\d[\d ()-]{7,}\d)", text)
    phone_match = next((candidate for candidate in phone_candidates if len(re.sub(r"\D", "", candidate)) >= 9), None)
    linkedin_match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/[^\s,;|]+", text, re.I)
    github_match = re.search(r"(?:https?://)?(?:www\.)?github\.com/[^\s,;|]+", text, re.I)
    location = None
    location_match = re.search(r"(?:location|address)\s*:\s*([^\n|]+)", text, re.I)
    if location_match:
        location = location_match.group(1).strip()
    if not location:
        for line in text.splitlines()[:8]:
            if "|" not in line or "@" not in line:
                continue
            candidates = [part.strip() for part in line.split("|") if part.strip()]
            for candidate in candidates:
                if email_match and candidate == email_match.group(0):
                    continue
                if re.search(r"\+?\d[\d ()-]{7,}\d", candidate) or re.search(r"linkedin\.com|github\.com", candidate, re.I):
                    continue
                if candidate:
                    location = candidate
                    break
            if location:
                break
    return ContactInfo(
        email=email_match.group(0) if email_match else None,
        phone=phone_match.strip() if phone_match else None,
        location=location,
        linkedin=linkedin_match.group(0).rstrip(".,") if linkedin_match else None,
        github=github_match.group(0).rstrip(".,") if github_match else None,
    )


def _extract_line_section(text: str, names: set[str]) -> list[str]:
    return _section_lines(text, names)


def _extract_projects(text: str) -> list[ProjectEntry]:
    lines = _extract_line_section(text, {"projects", "key projects"})
    grouped: list[dict[str, object]] = []
    for line in lines:
        is_heading = bool(re.search(r"\s[—–]\s", line))
        if is_heading or not grouped:
            grouped.append({"line": line, "details": []})
        else:
            grouped[-1]["details"].append(line)
    entries: list[ProjectEntry] = []
    for group in grouped:
        line = str(group["line"])
        name_match = re.split(r"\s+[—–]\s+|\s+\-\s+", line, maxsplit=1)
        name = name_match[0].strip() if name_match else line
        details = [str(item) for item in group["details"]]
        description = " ".join([line] + details)
        technologies = _find_skills(description, _TECH_PATTERNS)
        entries.append(ProjectEntry(name=name or None, technologies=technologies, description=description or None))
    return entries[:10]


def _extract_list_section(text: str, names: set[str]) -> list[str]:
    return _extract_line_section(text, names)[:10]


def _extract_certifications(text: str) -> list[str]:
    return _extract_list_section(text, {"certifications", "certificates"})


def _extract_training(text: str) -> list[str]:
    return _extract_list_section(text, {"training", "courses", "coursework"})


def _extract_languages(text: str) -> list[str]:
    lines = _extract_list_section(text, {"languages"})
    values: list[str] = []
    for line in lines:
        values.extend(part.strip() for part in re.split(r"[,;|]", line) if part.strip())
    return list(dict.fromkeys(values))[:10]


def _extract_achievements(text: str) -> list[str]:
    return _extract_list_section(text, {"achievements", "awards", "honors"})


def _extract_structured(text: str) -> ResumeAnalysis:
    technical = _find_skills(text, _TECH_PATTERNS)
    soft = _extract_soft_skills(text)
    skills = SkillSet(
        technical=technical,
        soft=soft,
        programming_languages=_find_skills(text, _PROGRAMMING_PATTERNS),
        frameworks=_find_skills(text, _FRAMEWORK_PATTERNS),
        libraries=_find_skills(text, _LIBRARY_PATTERNS),
        tools=_find_skills(text, _TOOL_PATTERNS),
        databases=_find_skills(text, _DATABASE_PATTERNS),
        cloud=_find_skills(text, _CLOUD_PATTERNS),
        machine_learning=_find_skills(text, _ML_PATTERNS),
        data_science=_find_skills(text, _DATA_PATTERNS),
        ai=_find_skills(text, _AI_PATTERNS),
        computer_vision=_find_skills(text, _COMPUTER_VISION_PATTERNS),
        nlp=_find_skills(text, _NLP_PATTERNS),
    )
    education = _extract_education(text)
    experience = _extract_experience(text)
    return ResumeAnalysis(
        full_name=_first_resume_name(text),
        contact=_extract_contact(text),
        skills=skills,
        education=education,
        experience=experience,
        projects=_extract_projects(text),
        certifications=_extract_certifications(text),
        training=_extract_training(text),
        languages=_extract_languages(text),
        achievements=_extract_achievements(text),
    )


def _merge_validated_analysis(text: str, model_analysis: ResumeAnalysis) -> ResumeAnalysis:
    validated = _keyword_analysis(text)
    return ResumeAnalysis(
        full_name=validated.full_name,
        contact=validated.contact,
        skills=validated.skills,
        education=validated.education,
        experience=validated.experience,
        projects=validated.projects,
        certifications=validated.certifications,
        training=validated.training,
        languages=validated.languages,
        achievements=validated.achievements,
        summary=validated.summary,
        score=validated.score,
        strengths=validated.strengths,
        weaknesses=validated.weaknesses,
        improvements=validated.improvements,
        learning_resources=validated.learning_resources,
    )


def _keyword_analysis(text: str) -> ResumeAnalysis:
    normalized = "\n".join(_clean_line(line) for line in text.splitlines() if line.strip())
    structured = _extract_structured(normalized)
    technical = structured.skills.technical
    soft = structured.skills.soft
    education = structured.education
    experience = structured.experience
    summary = _build_summary(technical, soft, education, experience, structured.projects)
    weaknesses = _detect_weaknesses(normalized, technical, soft, education, experience, structured.projects)
    strengths = _detect_strengths(technical, soft, education, experience, structured.projects)
    improvements = _build_recommendations(normalized, technical, soft, education, experience, structured.projects, weaknesses)
    score = _calculate_score(technical, soft, education, experience, normalized)
    learning_resources = _suggest_learning_resources(technical, weaknesses)
    structured.summary = summary
    structured.score = score
    structured.strengths = strengths
    structured.weaknesses = weaknesses
    structured.improvements = improvements
    structured.learning_resources = learning_resources
    return structured


def _detect_strengths(
    technical: list[str],
    soft: list[str],
    education: list[EducationEntry],
    experience: list[ExperienceEntry],
    projects: list[ProjectEntry],
) -> list[str]:
    strengths: list[str] = []
    if technical:
        strengths.append(
            f"The CV establishes a clear technical direction through {', '.join(technical[:6])}, "
            "which gives an ATS a coherent profile to match against technical roles."
        )
    if experience:
        titled = [entry.title for entry in experience if entry.title]
        if titled:
            strengths.append(
                f"The experience section shows practical progression through {', '.join(titled[:3])}; "
                "the role and date structure gives the reader evidence of applied work rather than skills alone."
            )
    if projects:
        named = [project.name for project in projects if project.name]
        if named:
            strengths.append(
                f"The project portfolio is a differentiator: {', '.join(named[:3])} demonstrate applied delivery "
                "and can support a strong project-led portfolio narrative."
            )
    if education:
        entry = education[0]
        degree = entry.degree or "a formal degree"
        institution = f" from {entry.institution}" if entry.institution else ""
        strengths.append(f"The CV clearly states {degree}{institution}, improving baseline ATS and recruiter trust.")
    if soft:
        strengths.append(
            f"Behavioral evidence is present through {', '.join(soft[:4])}; connect each signal to a concrete outcome "
            "so it reads as demonstrated behavior rather than a keyword."
        )
    return strengths[:5]


def _calculate_score(
    technical: list[str], soft: list[str], education: list[EducationEntry], experience: list[ExperienceEntry], text: str
) -> float:
    score = min(len(technical), 5) * 3.0
    score += min(len(soft), 3) * 2.0
    for entry in education:
        if entry.degree:
            score += 4.0
        if entry.institution:
            score += 3.0
        if entry.year:
            score += 3.0
        break
    for entry in experience[:3]:
        if entry.title:
            score += 3.0
        if entry.company:
            score += 3.0
        if entry.duration:
            score += 3.0
        if entry.description and len(entry.description.split()) >= 8:
            score += 4.0
    if re.search(r"\b(?:project|projects)\b", text, re.I):
        score += 5.0
    if re.search(r"\b(?:reduced|increased|improved|saved|grew|achieved|managed)\b[^\n]{0,80}(?:\d+|%)", text, re.I):
        score += 10.0
    word_count = len(text.split())
    if word_count >= 180:
        score += 10.0
    elif word_count >= 100:
        score += 5.0
    return round(min(100.0, score), 1)


def _build_summary(
    technical: list[str],
    soft: list[str],
    education: list[EducationEntry],
    experience: list[ExperienceEntry],
    projects: list[ProjectEntry],
) -> str:
    if technical:
        focus = ", ".join(technical[:6])
        opening = f"AI/data and software profile centered on {focus}."
    elif experience:
        opening = "Early-career profile with practical experience that needs a clearer target-role narrative."
    else:
        opening = "The CV does not yet establish a sufficiently specific professional direction."
    evidence_parts: list[str] = []
    if experience:
        roles = [entry.title for entry in experience if entry.title]
        if roles:
            evidence_parts.append(f"Applied evidence appears in {', '.join(roles[:3])}")
    if projects:
        names = [project.name for project in projects if project.name]
        if names:
            evidence_parts.append(f"the portfolio includes {', '.join(names[:3])}")
    if education:
        evidence_parts.append("formal education is stated")
    if soft:
        evidence_parts.append(f"behavioral evidence includes {', '.join(soft[:3])}")
    evidence = "; ".join(evidence_parts)
    closing = (
        "The next improvement priority is to convert activity descriptions into concise, role-targeted achievement bullets "
        "with clear ownership, method, and measurable outcome."
    )
    return " ".join(part for part in (opening, evidence + "." if evidence else "", closing) if part)


def _detect_weaknesses(
    text: str,
    technical: list[str],
    soft: list[str],
    education: list[EducationEntry],
    experience: list[ExperienceEntry],
    projects: list[ProjectEntry],
) -> list[str]:
    issues: list[str] = []
    if not technical:
        issues.append("The CV does not yet establish a searchable technical target; select the intended role and mirror its truthful core keywords in the headline, summary, and skills section.")
    elif len(technical) < 3:
        issues.append(f"The technical footprint is narrow ({', '.join(technical)}); add only source-supported tools, methods, and platforms that are relevant to the target role.")
    if not soft:
        if experience:
            role = _behavioral_anchor(experience)
            issues.append(f"Behavioral evidence is implied but not explicit in {role}; add one truthful bullet showing how you communicated, collaborated, mentored, or led and state the result.")
        else:
            issues.append("Behavioral evidence is not visible; add one truthful example of communication, collaboration, ownership, or problem solving tied to a real project or role.")
    if not re.search(r"\d|%", text):
        issues.append("Impact evidence is not quantified; use verified numbers, percentages, scope, or a precise qualitative outcome to show what changed because of the work.")
    if experience:
        activity_only = [entry.title for entry in experience if entry.description and not re.search(r"\d|%", entry.description)]
        if activity_only:
            issues.append(f"The bullets for {', '.join(activity_only[:2])} describe activity without a measurable outcome; quantify scale, speed, quality, cost, adoption, or reliability where the source evidence supports it.")
    else:
        issues.append("Professional evidence is missing; add each real role or project with title, organization, dates, contribution, and outcome rather than adding assumed experience.")
    if projects:
        dense_projects = [project.name for project in projects if project.description and len(project.description.split()) > 55]
        if dense_projects:
            issues.append(f"The project evidence for {', '.join(dense_projects[:2])} is dense; split it into bullets covering the problem, your contribution, technology, and measurable result for faster ATS and recruiter scanning.")
    if not education:
        issues.append("Education is not explicit; add the actual degree, institution, and completion year if present in the source record.")
    if len(text.split()) < 120:
        issues.append("The document is light on evidence; expand the strongest role or project with context, action, and verified result rather than generic responsibility statements.")
    return issues[:5]


def _build_recommendations(
    text: str,
    technical: list[str],
    soft: list[str],
    education: list[EducationEntry],
    experience: list[ExperienceEntry],
    projects: list[ProjectEntry],
    weaknesses: list[str],
) -> list[str]:
    recommendations: list[str] = []
    if technical:
        recommendations.append(
            f"Positioning: choose one target role before editing. Rewrite the headline and opening summary around the strongest verified stack ({', '.join(technical[:5])}) and repeat the role-aligned terms naturally in the relevant experience or project bullets."
        )
    else:
        recommendations.append(
            "Positioning: choose the target role first, then build the headline and summary from skills actually evidenced in the CV; do not add a technology merely because it appears in a job description."
        )
    if experience:
        role = next((entry for entry in experience if entry.title), experience[0])
        recommendations.append(
            f"Experience rewrite: turn the strongest evidence in {role.title or 'the lead role'} into 2–4 bullets using STAR: situation or scale, the action you personally took, the tools or method, and the verified result. Start with a strong verb and keep the outcome at the end of each bullet."
        )
    if projects:
        project = next((item for item in projects if item.name), projects[0])
        recommendations.append(
            f"Project presentation: restructure {project.name or 'the strongest project'} into separate bullets for problem, personal contribution, implementation, and outcome. Put the most ATS-relevant technologies in the first bullet and keep claims tied to the project text."
        )
    if not soft:
        role_name = _behavioral_anchor(experience) if experience else "the most relevant project"
        recommendations.append(
            f"Behavioral proof: add one source-supported bullet under {role_name} showing collaboration, communication, mentoring, ownership, or leadership. Use the pattern `action + people/context + outcome`; do not insert a soft-skill keyword without an example."
        )
    if any(entry.description and not re.search(r"\d|%", entry.description) for entry in experience):
        recommendations.append(
            "Impact upgrade: audit every bullet and replace task-only phrasing with a verified metric or scope indicator such as records processed, latency, accuracy, adoption, time saved, or error reduction. If the source does not contain a number, use a precise qualitative outcome instead of inventing one."
        )
    if education and not any(entry.degree and entry.institution and entry.year for entry in education):
        recommendations.append(
            "Education clarity: put the actual degree, institution, and completion year on one ATS-readable line; preserve the source wording and do not upgrade the qualification level."
        )
    if not recommendations:
        recommendations.append(
            "Final ATS pass: tailor the summary, reorder evidence for the target role, and verify that every keyword and achievement remains supported by the original CV text."
        )
    return recommendations[:6]


def _suggest_certifications(technical: list[str]) -> list[str]:
    result = []
    for skill in technical:
        if skill in _CERT_MAP and _CERT_MAP[skill] not in result:
            result.append(_CERT_MAP[skill])
    return result[:5]


def _suggest_learning_resources(technical: list[str], weaknesses: list[str]) -> list[str]:
    query = " ".join(technical[:4]) if technical else "resume improvement"
    try:
        chunks = _ensure_kb().retrieve(query, top_k=5, category="learning_resource", mode="keyword")
        return [chunk.title for chunk in chunks if chunk.title][:5]
    except Exception:
        return []
