from __future__ import annotations

import re
from typing import Any

from app.schemas.job import JobOut


_SUPPORTED_SCOPE = "Stored profile information, uploaded resume data, available job listings and requirements, and the application's existing career knowledge"
_KNOWN_CAREER_TERMS = {"python", "java", "javascript", "typescript", "react", "angular", "vue", "django", "flask", "fastapi", "docker", "kubernetes", "aws", "azure", "gcp", "sql", "postgresql", "pandas", "numpy", "tensorflow", "pytorch", "machine learning", "data science", "devops", "agile", "scrum", "rest api", "microservices", "tailwind css", "graphql", "terraform", "figma", "selenium"}
_UNSUPPORTED_PERSONAL_TOPICS = ("salary", "age", "political", "favorite football", "favorite team", "religion", "marital status")


def _mentions_unsupported_topic(text: str) -> bool:
    """Word-boundary check so short topics like 'age' never match inside unrelated
    words such as 'language' or 'manager'."""
    return any(re.search(rf"(?<![A-Za-z]){re.escape(topic)}(?![A-Za-z])", text, re.I) for topic in _UNSUPPORTED_PERSONAL_TOPICS)


def _keyword_route(question: str, available_jobs: list[JobOut] | None = None, selected_job: JobOut | None = None) -> str:
    query = question.lower().strip()

    comparison_markers = (
        "supported by the resume", "not supported by the resume", "unsupported by the resume",
        "against the selected job", "against this job", "against the role", "fit for",
        "fit assessment", "how strong is this candidate", "strongest matches", "top 3 strengths",
        "top three strengths", "gaps for this candidate", "resume and the selected job",
        "resume and selected job", "requirements are missing", "missing requirements",
    )
    comparison_signal = any(term in query for term in ("requirement", "job", "role", "fit", "gap", "match"))
    comparison_verdict_terms = ("supported", "unsupported", "not supported", "partially supported", "missing", "gap")

    # An explicit prohibition against adding job requirements is resume-only, even when a job is selected.
    if "without adding any job requirements" in query or "do not add any job requirements" in query:
        return "resume"
    # Comparison language is evaluated before neutral "using only" phrasing.
    # Two independent signals both count: the fixed phrase list (handles "fit for", "gaps for
    # this candidate", etc. that don't necessarily mention "resume"), and the more general rule
    # that a requirement/job question paired with support-verdict language and a resume mention
    # is a comparison regardless of the exact filler words ("the resume" vs "the selected resume").
    if comparison_signal and any(marker in query for marker in comparison_markers):
        return "comparison"
    if comparison_signal and "resume" in query and any(term in query for term in comparison_verdict_terms):
        return "comparison"

    # Candidate-skill overlap and gap questions are comparisons even when the
    # user does not say "resume" explicitly. The job reference must be in the
    # question, so merely selecting a job still cannot hijack unrelated prompts.
    comparison_context = any(term in query for term in ("candidate", "resume", "cv", "skill", "requirement"))
    job_reference = any(term in query for term in ("selected job", "job", "role", "position"))
    comparison_verdict = any(term in query for term in ("match", "matches", "overlap", "missing", "gap", "fit", "supported"))
    if comparison_context and job_reference and comparison_verdict:
        return "comparison"

    # Other explicit resume-only wording wins over any selected job in the session.
    resume_only = "only" in query and "skill" in query and ("resume" in query or "cv" in query)
    if resume_only:
        return "resume"
    if selected_job and "this job" in query and any(term in query for term in ("fit", "improve", "gap", "missing", "supported")):
        return "comparison"

    if any(term in query for term in (
        "what do you know about me", "tell me about my profile", "my information", "my skills",
        "my experience", "my education", "my email", "my username", "stored profile",
    )) and not any(term in query for term in ("resume", "cv", "candidate", "explicitly", "listed")):
        return "profile"

    # Global matching is opt-in. A selected job alone must never trigger it.
    if any(term in query for term in (
        "job recommendations", "recommend jobs", "recommended jobs", "best jobs", "top jobs",
        "match my resume", "matching", "match score", "rank jobs", "ranking", "which jobs",
        "suitability across", "compare jobs", "what jobs", "available jobs",
    )):
        return "matcher"

    if any(term in query for term in (
        "improve my resume", "improve the resume", "improve resume", "improve my cv", "improve the cv",
        "improve cv", "how can i improve", "how do i improve",
    )):
        return "career"

    if any(term in query for term in (
        "selected resume", "uploaded resume", "my resume", "the resume", "resume evidence", "cv evidence",
        "candidate's full name", "candidate name", "full name", "projects", "highest educational",
        "educational qualifications", "degree", "certification", "certifications", "experience listed",
        "skills explicitly", "does the resume", "does my resume", "resume mention", "prove that",
        "candidate's skills", "candidate's experience", "candidate's education", "languages", "achievements",
    )):
        return "resume"

    if _mentions_unsupported_topic(query) and not any(term in query for term in ("resume", "cv", "job requirement")):
        return "unsupported"

    # A "which of X, Y, Z are explicitly supported" style question is a resume evidence
    # check even when it never literally says "resume" — a selected job must never hijack
    # a plain explicit-support question into the job-info route.
    if re.search(r"which of .+ (?:is|are) (?:explicitly\s+)?supported", query):
        return "resume"

    if any(term in query for term in (
        "selected job", "currently selected job", "this role", "job requirements", "job description",
        "job title", "what does this job", "what experience does this job", "what skills does this job",
        "is the job remote", "company", "location", "deadline", "applications remaining",
    )):
        return "job"
    if available_jobs and any(job.title.lower() in query or (job.company and job.company.lower() in query) for job in available_jobs):
        return "job"
    if any(term in query for term in (
        "career", "work", "qualification", "improve", "interview", "roadmap", "learn", "training",
        "certification", "strength", "weakness", "missing", "how can i", "how do i",
    )):
        return "career"
    if any(term in query for term in _KNOWN_CAREER_TERMS) and any(marker in query for marker in ("what is", "what are", "explain", "tell me about", "how do", "how can", "learn")):
        return "career"
    return "unsupported"


def _run_profile(state: dict[str, Any]) -> dict[str, Any]:
    profile = state.get("user_profile") or {}
    profile_lines = [f"{key}: {value}" for key, value in profile.items() if value]
    return {
        "profile_info": "Stored profile information:\n"
        + ("\n".join(profile_lines) if profile_lines else "No stored profile information is available.")
        + "\n\nNo uploaded resume information is available for this profile-only question."
    }


def _resume_item(state: dict[str, Any]) -> dict[str, Any] | None:
    resumes = state.get("resume_context") or []
    return resumes[0] if resumes else None


def _as_text(value: Any) -> str:
    if isinstance(value, dict):
        return "; ".join(f"{key}: {item}" for key, item in value.items() if item)
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item)
    return str(value) if value else ""


def _explicit_evidence(term: str, resume_text: str) -> str | None:
    normalized = term.replace("'", "").replace("’", "")
    pattern = re.escape(normalized).replace(r"\ ", r"\s+")
    for line in resume_text.splitlines():
        if re.search(rf"(?<![A-Za-z0-9]){pattern}(?![A-Za-z0-9])", line.replace("'", "").replace("’", ""), re.I):
            return line.strip()
    return None


def _extract_requested_items(query: str) -> list[str]:
    """Generically pull the list of items an explicit-mention/support question is asking about.

    Handles arbitrary items (not a fixed skill whitelist) by parsing the list that follows
    trigger phrasing such as "mention X, Y, and Z" or "which of X, Y, and Z are supported".
    """
    patterns = (
        r"which of (.+?)\s+(?:is|are)\s+(?:explicitly\s+)?supported",
        r"\b(?:does|do)\s+(?:the|my|your|this)?\s*(?:selected\s+)?(?:resume|cv)\s+(?:explicitly\s+)?(?:mention|support|include|contain)s?\s+(.+?)(?:\?|$)",
        r"\bprove that .+?\b(?:has|have|contains?|mentions?)\s+(.+?)(?:\?|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, query)
        if not match:
            continue
        text = match.group(1)
        # Only keep the clause listing items; drop any trailing instruction clause
        # ("for each one, answer yes or no...") that sometimes shares the sentence.
        text = re.split(r",?\s*for each\b|,?\s*and provide\b|,?\s*and (?:say|answer)\b", text)[0]
        items = re.split(r",\s*(?:and\s+)?|\s+and\s+", text)
        items = [item.strip(" .'\"") for item in items if item.strip(" .'\"")]
        if items:
            return items
    return []


_GENERIC_ITEM_SUFFIXES = (" experience", " skills", " skill", " knowledge", " background", " expertise")


def _answer_item(item: str, resume_text: str) -> str:
    from app.agents.job_matcher import calculate_experience_years, extract_date_ranges

    years_match = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*years?", item)
    if years_match and "experience" in item:
        required_years = float(years_match.group(1))
        candidate_years = calculate_experience_years(resume_text)
        if candidate_years is None:
            return f"- {item}: No explicit evidence."
        status = "Yes" if candidate_years >= required_years else "No"
        date_evidence = "; ".join(f"{start}-{end}" for start, end in extract_date_ranges(resume_text))
        return f"- {item}: {status} — {candidate_years:g} years evidenced from explicit resume dates ({date_evidence})."
    evidence = _explicit_evidence(item, resume_text)
    if evidence is None:
        # A generic qualifier word (e.g. "AWS experience", "Python skills") is stripped
        # so the underlying term is checked on its own; this is a linguistic
        # normalization, not a hardcoded skill list, so it stays generic.
        core = item
        for suffix in _GENERIC_ITEM_SUFFIXES:
            if core.lower().endswith(suffix):
                core = core[: len(core) - len(suffix)].strip(" .'\"")
                break
        core = re.sub(r"^(?:a|an|the)\s+", "", core, flags=re.I).strip()
        if core and core.lower() != item.lower():
            evidence = _explicit_evidence(core, resume_text)
    return f"- {item}: {'Yes — ' + evidence if evidence else 'No explicit evidence.'}"


def _run_resume(state: dict[str, Any]) -> dict[str, Any]:
    item = _resume_item(state)
    resume_text = state.get("resume_text") or ""
    if not item and not resume_text:
        return {"resume_info": "The requested information is unavailable because no selected resume was supplied."}

    item = item or {}
    query = state["question"].lower()
    full_name = item.get("full_name")
    skills = item.get("skills") or {}
    technical = skills.get("technical", []) if isinstance(skills, dict) else []
    soft = skills.get("soft", []) if isinstance(skills, dict) else []
    projects = item.get("projects") or []
    education = item.get("education") or []
    experience = item.get("experience") or []
    wants_evidence = any(term in query for term in ("evidence", "prove", "support"))

    # Every recognized sub-question is answered independently and appended, instead of
    # returning on the first match, so multi-part questions never silently drop a claim.
    sections: list[str] = []

    if "full name" in query or "candidate's name" in query or "candidate name" in query:
        if not full_name:
            sections.append("Full name: unavailable in the selected resume.")
        elif wants_evidence:
            line = _explicit_evidence(full_name, resume_text)
            evidence = f'"{line}" (source: raw resume text)' if line else (
                "no exact matching line in raw resume text; value stored in the structured 'full_name' extraction field."
            )
            sections.append(f"Full name: {full_name}.\nSupporting resume evidence: {evidence}")
        else:
            sections.append(f"Resume evidence — full name: {full_name}.")

    if "project" in query:
        values = [_as_text(project) for project in projects]
        sections.append(
            "Resume evidence — projects explicitly listed:\n"
            + ("\n".join(f"- {value}" for value in values if value) or "No projects are explicitly listed in the selected resume.")
        )

    if any(term in query for term in ("education", "degree", "qualification")) and "prove" not in query and "explicitly mention" not in query:
        values = [_as_text(entry) for entry in education]
        sections.append(
            "Resume evidence — educational qualifications:\n"
            + ("\n".join(f"- {value}" for value in values if value) or "No educational qualification is explicitly listed in the selected resume.")
        )

    requested_items = _extract_requested_items(query)
    if requested_items:
        sections.append("Resume evidence check:\n" + "\n".join(_answer_item(item_text, resume_text) for item_text in requested_items))

    if not requested_items:
        standalone_threshold = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*years", query)
        if standalone_threshold and "experience" in query:
            sections.append(_answer_item(f"{standalone_threshold.group(1)}+ years of experience", resume_text))
        elif "experience" in query:
            values = [_as_text(entry) for entry in experience]
            sections.append(
                "Resume evidence — experience listed:\n"
                + ("\n".join(f"- {value}" for value in values if value) or "No experience is explicitly listed in the selected resume.")
            )

    if not requested_items and ("skill" in query or "technolog" in query) and "project" not in query:
        listed = list(dict.fromkeys([str(value) for value in technical + soft if value]))
        sections.append(
            "Resume evidence — explicitly supported skills:\n"
            + (", ".join(listed) if listed else "No skills are explicitly supported by the selected resume.")
        )

    if not requested_items and _mentions_unsupported_topic(query):
        evidence = next((line.strip() for line in resume_text.splitlines() if _mentions_unsupported_topic(line.lower())), None)
        sections.append(f"Resume evidence: {evidence}" if evidence else "The requested personal fact is unavailable and is not supported by the selected resume.")

    if sections:
        return {"resume_info": "\n\n".join(sections)}

    fallback_sections = [
        f"Full name: {full_name or 'Unavailable'}",
        "Skills: " + (", ".join(str(value) for value in technical + soft if value) or "Unavailable"),
        "Education: " + ("; ".join(_as_text(entry) for entry in education if _as_text(entry)) or "Unavailable"),
        "Experience: " + ("; ".join(_as_text(entry) for entry in experience if _as_text(entry)) or "Unavailable"),
        "Projects: " + ("; ".join(_as_text(entry) for entry in projects if _as_text(entry)) or "Unavailable"),
    ]
    return {"resume_info": "Resume evidence only:\n" + "\n".join(fallback_sections)}


def _run_job(state: dict[str, Any]) -> dict[str, Any]:
    job = state.get("selected_job")
    if not job:
        return {"job_info": "The requested selected-job information is unavailable because no selected job was supplied."}
    required = ", ".join(job.skills_required) or "None listed"
    preferred = ", ".join(job.skills_preferred) or "None listed"
    return {"job_info": f"Selected job evidence: {job.title} at {job.company or 'Company not listed'}. Location: {job.location or 'Not listed'}. Required skills: {required}. Preferred skills: {preferred}. Required experience: {job.experience_years or 'Not listed'}. Required education: {job.education_required or 'Not listed'}. Status: {'Open' if job.is_open else 'Closed'}."}


async def _run_comparison(state: dict[str, Any]) -> dict[str, Any]:
    from app.agents.job_matcher import build_requirement_table, match_resume_to_single_job

    job = state.get("selected_job")
    resume_text = state.get("resume_text") or ""
    if not job or not resume_text:
        return {"comparison_info": "A selected resume and selected job are both required for a grounded comparison."}
    resume_skills = state.get("resume_skills") or []
    resume_summary = state.get("resume_summary") or ""
    result = match_resume_to_single_job(
        resume_skills=resume_skills, resume_text=resume_text, resume_summary=resume_summary, job=job,
    )
    rows = build_requirement_table(resume_skills, resume_text, resume_summary, job)
    table_lines = [f"{row.requirement} | {row.evidence} | {row.status}" for row in rows]
    supported = [row.requirement for row in rows if row.status == "SUPPORTED"]
    partial = [row.requirement for row in rows if row.status == "PARTIAL"]
    not_supported = [row.requirement for row in rows if row.status == "NOT_SUPPORTED"]
    return {
        "comparison_info": (
            "REQUIREMENT | RESUME EVIDENCE | STATUS\n"
            + "\n".join(table_lines)
            + "\n\nSUPPORTED\n" + (", ".join(supported) or "None.")
            + "\n\nPARTIALLY SUPPORTED\n" + (", ".join(partial) or "None.")
            + "\n\nNOT SUPPORTED\n" + (", ".join(not_supported) or "None.")
            + "\n\nEach status above is derived only from explicit resume text matches against the "
              "selected job's requirements; a related or adjacent technology is never treated as "
              "evidence for a requirement that is not itself explicitly present.\n\n"
            + f"Overall fit score for the selected job: {result.match_score}%."
        )
    }


async def _run_resume_analysis(state: dict[str, Any]) -> dict[str, Any]:
    from app.agents.resume_analyzer import analyze_resume

    text = state.get("resume_text") or state.get("resume_summary") or ""
    if not text:
        return {"resume_analysis": "No selected resume was supplied for analysis."}
    analysis = await analyze_resume(text)
    lines = [
        f"Summary: {analysis.summary}",
        f"Technical skills: {', '.join(analysis.skills.technical) or 'None detected'}",
        f"Soft skills: {', '.join(analysis.skills.soft) or 'None detected'}",
        f"Education: {len(analysis.education)} entry or entries",
        f"Experience: {len(analysis.experience)} entry or entries",
        f"Weaknesses: {'; '.join(analysis.weaknesses) or 'None detected'}",
    ]
    return {"resume_analysis": "\n".join(lines), "resume_skills": analysis.skills.technical + analysis.skills.soft}


async def _run_matcher(state: dict[str, Any]) -> dict[str, Any]:
    from app.agents.job_matcher import match_resume_to_jobs

    resume_text = state.get("resume_text") or ""
    jobs: list[JobOut] = state.get("available_jobs") or []
    if not resume_text:
        return {"match_info": "A resume is required before job matching."}
    if not jobs:
        return {"match_info": "No open jobs are available for matching."}
    results = match_resume_to_jobs(
        resume_skills=state.get("resume_skills") or [],
        resume_text=resume_text,
        resume_summary=state.get("resume_summary") or "",
        jobs=jobs,
    )
    lines = ["Top job matches:"]
    for index, result in enumerate(results[:3], start=1):
        lines.append(
            f"{index}. {result.job.title} at {result.job.company} — {result.match_score}%. "
            f"Matched requirements: {', '.join(result.matched_requirements) or 'None'}. "
            f"Partially matched: {', '.join(result.partially_matched) or 'None'}. "
            f"Missing requirements: {', '.join(result.missing_requirements) or 'None'}. "
            f"Suggestions: {'; '.join(result.improvement_suggestions) or 'None'}."
        )
    return {"match_info": "\n".join(lines)}


async def _run_career(state: dict[str, Any]) -> dict[str, Any]:
    from app.agents.career_advisor import get_career_advice

    result = await get_career_advice(
        question=state["question"],
        resume_summary=state.get("resume_summary"),
        resume_skills=state.get("resume_skills"),
        resume_text=state.get("resume_text"),
        user_profile=state.get("user_profile"),
        history=state.get("history"),
        selected_job=state.get("selected_job"),
    )
    return {"career_advice": result.get("reply", ""), "sources": result.get("sources", [])}


def _unsupported_response() -> str:
    return f"This question is outside the supported Career AI scope. I can use only {_SUPPORTED_SCOPE}. The requested information is unavailable from the allowed sources."


async def run_supervisor(
    question: str,
    resume_summary: str | None = None,
    resume_skills: list[str] | None = None,
    resume_text: str | None = None,
    history: list[dict[str, str]] | None = None,
    available_jobs: list[JobOut] | None = None,
    user_profile: dict[str, str | None] | None = None,
    resume_context: list[dict[str, Any]] | None = None,
    selected_job: JobOut | None = None,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "question": question,
        "resume_summary": resume_summary or "",
        "resume_skills": resume_skills or [],
        "resume_text": resume_text or "",
        "history": history or [],
        "available_jobs": available_jobs or [],
        "user_profile": user_profile or {},
        "resume_context": resume_context or [],
        "selected_job": selected_job,
    }
    route = _keyword_route(question, available_jobs=available_jobs or [], selected_job=selected_job)
    if route == "profile":
        state.update(_run_profile(state))
        reply = state["profile_info"]
    elif route == "resume":
        if any(term in question.lower() for term in ("analyze resume", "analyze cv", "extract", "parse resume", "resume sections")):
            state.update(await _run_resume_analysis(state))
            reply = state["resume_analysis"]
        else:
            state.update(_run_resume(state))
            reply = state["resume_info"]
    elif route == "comparison":
        state.update(await _run_comparison(state))
        reply = state["comparison_info"]
    elif route == "matcher":
        state.update(await _run_matcher(state))
        reply = state["match_info"]
    elif route == "job":
        state.update(_run_job(state))
        reply = state["job_info"]
    elif route == "career":
        state.update(await _run_career(state))
        reply = state["career_advice"]
    else:
        reply = _unsupported_response()
    return {
        "reply": reply,
        "sources": state.get("sources") or [],
        "resume_used": bool(resume_summary or resume_text or resume_context),
        "agent_used": route,
    }
