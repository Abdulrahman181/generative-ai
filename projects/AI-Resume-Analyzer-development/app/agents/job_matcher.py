import re
from datetime import datetime

from app.schemas.job import JobOut
from app.schemas.matching import MatchResult


_ALIASES = {
    "js": "javascript",
    "nodejs": "node.js",
    "node": "node.js",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "ml": "machine learning",
    "rest api": "rest apis",
    "rest apis": "rest apis",
}

_DEGREE_RANK = {
    "diploma": 1,
    "associate": 1,
    "bachelor": 2,
    "b.sc": 2,
    "b.s": 2,
    "b.a": 2,
    "master": 3,
    "m.sc": 3,
    "m.s": 3,
    "m.a": 3,
    "phd": 4,
    "doctorate": 4,
}


def _normalize(value: str) -> str:
    clean = re.sub(r"[^a-z0-9+#. ]+", " ", str(value).lower()).strip()
    clean = re.sub(r"\s+", " ", clean)
    return _ALIASES.get(clean, clean)


def _terms(value: str) -> set[str]:
    normalized = re.sub(r"[^a-z0-9+#. ]+", " ", str(value).lower())
    words = re.sub(r"\s+", " ", normalized).strip().split()
    terms = set(words)
    for size in (2, 3):
        terms.update(" ".join(words[index:index + size]) for index in range(len(words) - size + 1))
    return {_ALIASES.get(term, term) for term in terms if term}


def _supports_skill(skill: str, resume_terms: set[str]) -> bool:
    return _normalize(skill) in resume_terms


def _partially_supports_skill(skill: str, resume_terms: set[str]) -> bool:
    words = _normalize(skill).split()
    if len(words) < 2:
        return False
    return len(set(words) & resume_terms) >= max(1, len(words) // 2)


def _parse_year_requirement(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)?\s*\+?\s*(?:years?|yrs?)", str(value).lower())
    if not match:
        match = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)", str(value).lower())
    if not match:
        return None
    return float(match.group(1))


def _job_experience_requirement(job: JobOut) -> float | None:
    explicit = _parse_year_requirement(job.experience_years)
    if explicit is not None:
        return explicit
    description_match = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:professional\s+)?experience", job.description.lower())
    return float(description_match.group(1)) if description_match else None


def _section_text(text: str, names: set[str]) -> str:
    headings = {
        "education", "academic background", "qualifications", "experience", "work experience",
        "professional experience", "employment", "skills", "technical skills", "soft skills",
        "summary", "professional summary", "profile", "objective", "certifications", "certificates",
        "projects", "key projects", "training", "courses", "coursework", "languages", "achievements", "awards", "honors",
    }
    active = False
    collected: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        heading = re.sub(r"[:|]$", "", line.lower()).strip()
        if heading in headings:
            active = heading in names
            continue
        if active and line:
            collected.append(line)
    return "\n".join(collected)


_MONTH = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
# A year range, optionally preceded on either side by a month name/abbreviation, e.g.
# "January 2025 - Present", "Aug 2022 – Dec 2024", "July 2021 - July 2022", or bare "2021-2022".
_DATE_RANGE_RE = re.compile(
    rf"(?:{_MONTH}\.?\s+)?((?:19|20)\d{{2}})\s*(?:[-–—]|to)\s*(?:{_MONTH}\.?\s+)?((?:19|20)\d{{2}}|present|current)\b",
    re.I,
)


def extract_date_ranges(text: str) -> list[tuple[int, int]]:
    """Extract explicit (start_year, end_year) pairs from resume text, resolving
    'present'/'current' to the current year. Recognizes bare 'YYYY-YYYY' as well as
    'Month YYYY - Month YYYY' style ranges."""
    ranges: list[tuple[int, int]] = []
    for start, end in _DATE_RANGE_RE.findall(text):
        end_year = datetime.now().year if end.lower() in {"present", "current"} else int(end)
        ranges.append((int(start), max(int(start), end_year)))
    return ranges


def _merge_intervals(intervals: list[tuple[int, int]]) -> list[list[int]]:
    merged: list[list[int]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def calculate_experience_years(text: str) -> float | None:
    """Total professional-experience years from explicit resume date ranges, merging
    overlapping periods so they are never double-counted. Returns None when no explicit
    date evidence is present."""
    intervals = extract_date_ranges(text)
    merged = _merge_intervals(intervals)
    if not merged:
        return None
    return float(sum(end - start for start, end in merged))


def _candidate_experience_years(resume_text: str) -> float | None:
    experience_text = _section_text(resume_text, {"experience", "work experience", "professional experience", "employment"})
    if not experience_text:
        experience_text = "\n".join(
            line for line in resume_text.splitlines()
            if re.search(r"\b(?:employment|employed|worked|professional experience|years of experience)\b", line, re.I)
            and not re.search(r"\b(?:project|course|training|certification)\b", line, re.I)
        )
    professional_lines = [
        line for line in experience_text.splitlines()
        if not re.search(r"\b(?:intern|internship|trainee|project|course|training)\b", line, re.I)
    ]
    professional_text = "\n".join(professional_lines)
    explicit = re.findall(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:professional\s+)?experience", professional_text.lower())
    values = [float(value) for value in explicit]
    merged_from_section = calculate_experience_years(professional_text)
    if merged_from_section is not None:
        values.append(merged_from_section)
    if not values:
        # Some resumes list dated roles without an "Experience" heading the section
        # detector recognizes; fall back to scanning the whole document for date ranges,
        # still excluding lines that look like education/training/projects.
        whole_doc_lines = [
            line for line in resume_text.splitlines()
            if not re.search(r"\b(?:intern|internship|trainee|project|course|training|certification|university|college|bachelor|master|degree)\b", line, re.I)
        ]
        fallback = calculate_experience_years("\n".join(whole_doc_lines))
        if fallback is not None:
            values.append(fallback)
    return max(values) if values else None


def _education_requirement(job: JobOut) -> tuple[str | None, bool]:
    value = job.education_required or ""
    if not value:
        match = re.search(r"([^.;\n]*(?:degree|bachelor|master|phd|doctorate)[^.;\n]*)", job.description, re.I)
        value = match.group(1).strip() if match else ""
    if not value:
        return None, False
    preferred = bool(re.search(r"\b(preferred|nice to have|plus|desirable)\b", value, re.I))
    return value, preferred


def _candidate_degree_rank(resume_text: str) -> int | None:
    education_text = _section_text(resume_text, {"education", "academic background", "qualifications"})
    source = education_text or "\n".join(
        line for line in resume_text.splitlines()
        if re.search(r"\b(?:degree|bachelor|master|phd|doctorate|associate|diploma|b\.?\s*sc\.?|b\.?\s*s\.?|b\.?\s*a\.?|m\.?\s*sc\.?|m\.?\s*s\.?|m\.?\s*a\.?)\b", line, re.I)
        and not re.search(r"\b(?:course|training|certification|certificate)\b", line, re.I)
    )
    found = []
    lower = source.lower()
    for degree, rank in _DEGREE_RANK.items():
        pattern = re.escape(degree).replace(r"\.", r"\.?\s*")
        if re.search(rf"\b{pattern}\b", lower):
            found.append(rank)
    return max(found) if found else None


def _degree_label(value: str) -> str:
    match = re.search(r"\b(phd|doctorate|master(?:'s)?|bachelor(?:'s)?|associate|diploma|b\.?\s*sc\.?|b\.?\s*s\.?|b\.?\s*a\.?|m\.?\s*sc\.?|m\.?\s*s\.?|m\.?\s*a\.?)\b", value, re.I)
    return match.group(1) if match else "required education"


def _experience_label(required_years: float) -> str:
    value = int(required_years) if required_years.is_integer() else required_years
    return f"{value}+ years experience"


def _requirement_components(
    job: JobOut,
    resume_terms: set[str],
    resume_text: str,
) -> tuple[list[str], list[str], list[str], list[str], list[str], list[str], list[tuple[float, float]]]:
    matched_skills = [skill for skill in job.skills_required if _supports_skill(skill, resume_terms)]
    partial_skills = [skill for skill in job.skills_required if skill not in matched_skills and _partially_supports_skill(skill, resume_terms)]
    missing_skills = [skill for skill in job.skills_required if skill not in matched_skills and skill not in partial_skills]
    matched_requirements = list(matched_skills)
    partial_requirements = list(partial_skills)
    missing_requirements = list(missing_skills)
    components: list[tuple[float, float]] = []

    if job.skills_required:
        skill_value = (len(matched_skills) + 0.5 * len(partial_skills)) / len(job.skills_required)
        components.append((skill_value, 0.65))

    required_years = _job_experience_requirement(job)
    if required_years is not None and required_years > 0:
        candidate_years = _candidate_experience_years(resume_text)
        label = _experience_label(required_years)
        if candidate_years is None:
            missing_requirements.append(label)
        elif candidate_years >= required_years:
            matched_requirements.append(label)
        else:
            partial_requirements.append(f"{label} (resume evidence: {candidate_years:g} years)")
        experience_value = min(1.0, candidate_years / required_years) if candidate_years is not None and required_years > 0 else 0.0
        components.append((experience_value, 0.2))

    education_text, education_preferred = _education_requirement(job)
    if education_text:
        required_rank_match = re.search(r"\b(phd|doctorate|master|bachelor|associate|diploma|b\.?\s*sc\.?|b\.?\s*s\.?|b\.?\s*a\.?|m\.?\s*sc\.?|m\.?\s*s\.?|m\.?\s*a\.?)\b", education_text, re.I)
        required_rank = next((rank for degree, rank in _DEGREE_RANK.items() if re.fullmatch(re.escape(degree).replace(r"\.", r"\.?\s*"), required_rank_match.group(1).lower().replace("'s", ""))), 1) if required_rank_match else 1
        candidate_rank = _candidate_degree_rank(resume_text)
        candidate_years = _candidate_experience_years(resume_text)
        equivalent_experience = bool(re.search(r"\bequivalent experience\b", education_text, re.I)) and candidate_years is not None and required_years is not None and candidate_years >= required_years
        label = f"{_degree_label(education_text)} degree"
        if candidate_rank is None and equivalent_experience:
            matched_requirements.append("Equivalent professional experience for education requirement")
        elif candidate_rank is None:
            missing_requirements.append(label)
        elif candidate_rank >= required_rank:
            matched_requirements.append(label)
        else:
            partial_requirements.append(f"{label} (lower degree evidence)")
        education_value = 1.0 if (candidate_rank is not None and candidate_rank >= required_rank) or equivalent_experience else 0.5 if candidate_rank else 0.0
        components.append((education_value, 0.05 if education_preferred else 0.15))

    return matched_skills, partial_skills, missing_skills, matched_requirements, partial_requirements, missing_requirements, components


def _evidence_line(term: str, resume_text: str) -> str | None:
    """Return the raw resume line that literally contains ``term``, or None."""
    normalized = str(term).replace("'", "").replace("\u2019", "")
    pattern = re.escape(normalized).replace(r"\ ", r"\s+")
    for line in resume_text.splitlines():
        clean_line = line.replace("'", "").replace("\u2019", "")
        if re.search(rf"(?<![A-Za-z0-9]){pattern}(?![A-Za-z0-9])", clean_line, re.I):
            return line.strip()
    return None


class RequirementRow:
    __slots__ = ("requirement", "evidence", "status")

    def __init__(self, requirement: str, evidence: str, status: str) -> None:
        self.requirement = requirement
        self.evidence = evidence
        self.status = status

    def as_dict(self) -> dict[str, str]:
        return {"requirement": self.requirement, "evidence": self.evidence, "status": self.status}


def build_requirement_table(
    resume_skills: list[str], resume_text: str, resume_summary: str, job: JobOut
) -> list[RequirementRow]:
    """Build a requirement-by-requirement comparison of ``job`` against the resume.

    Every row is derived only from explicit resume text/skill evidence. Related or
    adjacent technologies are never treated as evidence for a requirement that is not
    itself explicitly present (e.g. Docker is never evidence for Kubernetes).
    """
    resume_terms = _terms(f"{resume_text} {resume_summary}")
    for skill in resume_skills:
        resume_terms.update(_terms(skill))

    rows: list[RequirementRow] = []

    for skill in job.skills_required:
        evidence = _evidence_line(skill, resume_text)
        if _supports_skill(skill, resume_terms):
            status = "SUPPORTED"
        elif _partially_supports_skill(skill, resume_terms):
            status = "PARTIAL"
        else:
            status = "NOT_SUPPORTED"
        rows.append(RequirementRow(skill, evidence or "No explicit evidence.", status))

    for skill in job.skills_preferred:
        evidence = _evidence_line(skill, resume_text)
        status = "SUPPORTED" if _supports_skill(skill, resume_terms) else "NOT_SUPPORTED"
        rows.append(RequirementRow(f"Preferred: {skill}", evidence or "No explicit evidence.", status))

    required_years = _job_experience_requirement(job)
    if required_years is not None and required_years > 0:
        candidate_years = _candidate_experience_years(resume_text)
        label = _experience_label(required_years)
        date_evidence = "; ".join(f"{start}-{end}" for start, end in extract_date_ranges(resume_text))
        if candidate_years is None:
            rows.append(RequirementRow(label, "No explicit evidence.", "NOT_SUPPORTED"))
        elif candidate_years >= required_years:
            rows.append(RequirementRow(label, f"{candidate_years:g} years evidenced ({date_evidence or 'explicit resume dates'}).", "SUPPORTED"))
        else:
            rows.append(RequirementRow(label, f"{candidate_years:g} years evidenced ({date_evidence or 'explicit resume dates'}).", "PARTIAL"))

    education_text, _ = _education_requirement(job)
    if education_text:
        required_rank_match = re.search(r"\b(phd|doctorate|master|bachelor|associate|diploma|b\.?\s*sc\.?|b\.?\s*s\.?|b\.?\s*a\.?|m\.?\s*sc\.?|m\.?\s*s\.?|m\.?\s*a\.?)\b", education_text, re.I)
        required_rank = next((rank for degree, rank in _DEGREE_RANK.items() if re.fullmatch(re.escape(degree).replace(r"\.", r"\.?\s*"), required_rank_match.group(1).lower().replace("'s", ""))), 1) if required_rank_match else 1
        candidate_rank = _candidate_degree_rank(resume_text)
        label = f"{_degree_label(education_text)} degree"
        degree_evidence = _evidence_line(_degree_label(education_text), resume_text)
        if candidate_rank is None:
            rows.append(RequirementRow(label, degree_evidence or "No explicit evidence.", "NOT_SUPPORTED"))
        elif candidate_rank >= required_rank:
            rows.append(RequirementRow(label, degree_evidence or "Degree evidenced in resume education section.", "SUPPORTED"))
        else:
            rows.append(RequirementRow(label, degree_evidence or "Lower degree evidenced in resume.", "PARTIAL"))

    return rows


def _suggestions(missing_requirements: list[str], partial_requirements: list[str]) -> list[str]:
    suggestions = [f"Address the missing requirement only with truthful evidence: {requirement}." for requirement in missing_requirements]
    suggestions.extend(f"Clarify existing resume evidence for: {requirement}." for requirement in partial_requirements)
    return suggestions[:8]


def match_resume_to_jobs(
    resume_skills: list[str], resume_text: str, resume_summary: str, jobs: list[JobOut]
) -> list[MatchResult]:
    results = [_keyword_match(resume_skills, resume_text, resume_summary, job) for job in jobs]
    suitable = [result for result in results if result.match_score > 0]
    return sorted(suitable, key=lambda result: (-result.match_score, result.job.id))


def match_resume_to_single_job(
    resume_skills: list[str], resume_text: str, resume_summary: str, job: JobOut
) -> MatchResult:
    return _keyword_match(resume_skills, resume_text, resume_summary, job)


def _keyword_match(
    resume_skills: list[str], resume_text: str, resume_summary: str, job: JobOut
) -> MatchResult:
    resume_terms = _terms(f"{resume_text} {resume_summary}")
    for skill in resume_skills:
        resume_terms.update(_terms(skill))
    matched_skills, partial_skills, missing_skills, matched_requirements, partial_requirements, missing_requirements, components = _requirement_components(job, resume_terms, resume_text)
    for preferred_skill in job.skills_preferred:
        if _supports_skill(preferred_skill, resume_terms):
            matched_skills.append(preferred_skill)
            matched_requirements.append(f"Preferred: {preferred_skill}")
        else:
            missing_requirements.append(f"Preferred: {preferred_skill}")
    if job.skills_preferred:
        preferred_value = sum(1.0 for skill in job.skills_preferred if _supports_skill(skill, resume_terms)) / len(job.skills_preferred)
        components.append((preferred_value, 0.1))
    total_weight = sum(weight for _, weight in components)
    score = round((sum(value * weight for value, weight in components) / total_weight) * 100, 1) if total_weight else 0.0
    matched_text = ", ".join(matched_requirements) or "None"
    partial_text = ", ".join(partial_requirements) or "None"
    reducing_requirements = list(dict.fromkeys(missing_requirements + partial_requirements))
    reducing_text = ", ".join(reducing_requirements) or "None"
    explanation = f"Score {score}%. Required evidence matched: {matched_text}. Partial evidence: {partial_text}. Requirements reducing the score: {reducing_text}."
    return MatchResult(
        job=job,
        match_score=score,
        explanation=explanation,
        matched_skills=list(dict.fromkeys(matched_skills)),
        matched_requirements=list(dict.fromkeys(matched_requirements)),
        partially_matched=list(dict.fromkeys(partial_requirements)),
        missing_skills=list(dict.fromkeys(missing_skills)),
        missing_requirements=list(dict.fromkeys(missing_requirements)),
        improvement_suggestions=_suggestions(missing_requirements, partial_requirements),
    )
