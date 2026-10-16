from app.agents.supervisor import _keyword_route
from app.schemas.job import JobOut

job = JobOut.model_construct(id=1, title="AI Engineer", company="Example", description="Build AI systems", skills_required=["Python"], skills_preferred=[], experience_years=None, education_required=None)
questions = [
    "Which AI Engineer requirements are explicitly supported by the resume?",
    "Which AI Engineer requirements are not supported by the resume?",
    "How strong is this candidate's fit for the AI Engineer role?",
    "What are the top 3 strengths and top 3 gaps for this candidate against the selected job?",
    "Using only the currently selected resume and the currently selected AI Engineer job, identify the candidate's name, summarize the candidate's strongest relevant skills, list the AI Engineer requirements that are explicitly supported by the resume, list the requirements that are not supported, and give an overall fit assessment. Do not infer or invent any information that is not explicitly supported by either the resume or the selected job.",
]
for question in questions:
    print(_keyword_route(question, available_jobs=[job], selected_job=job), question)

resume_questions = [
    "What is the candidate's full name in the currently selected resume?",
    "What projects are explicitly listed in the selected resume?",
    "What are the candidate's highest educational qualifications?",
    "List only the candidate's skills that are explicitly supported by the resume.",
    "Does the selected resume explicitly mention Kubernetes?",
    "List only the candidate's skills that are explicitly supported by the resume, without adding any job requirements.",
]
for question in resume_questions:
    print(_keyword_route(question, available_jobs=[job], selected_job=job), question)
