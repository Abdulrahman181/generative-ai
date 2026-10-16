from sqlalchemy import inspect, text

from app.database import engine


_COLUMNS = {
    "users": {
        "username": "VARCHAR(64)",
    },
    "jobs": {
        "application_deadline": "DATETIME",
        "max_applications": "INTEGER",
        "application_count": "INTEGER NOT NULL DEFAULT 0",
        "skills_preferred": "TEXT",
        "experience_years": "VARCHAR(64)",
        "education_required": "TEXT",
    },
    "chat_messages": {
        "job_id": "INTEGER",
    },
    "resumes": {
        "full_name": "VARCHAR(255)",
        "contact_info": "TEXT",
        "projects": "TEXT",
        "training": "TEXT",
        "languages": "TEXT",
        "achievements": "TEXT",
        "score": "INTEGER",
        "strengths": "TEXT",
        "improvement_recommendations": "TEXT",
        "high_priority_fixes": "TEXT",
        "impact_metrics": "TEXT",
        "skills_ats_optimization": "TEXT",
        "professional_summary_polish": "TEXT",
        "improvement_job_id": "INTEGER",
    },
}


def ensure_sqlite_schema() -> None:
    if engine.url.get_backend_name() != "sqlite":
        return
    with engine.begin() as connection:
        inspector = inspect(connection)
        table_names = set(inspector.get_table_names())
        for table_name, columns in _COLUMNS.items():
            if table_name not in table_names:
                continue
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for name, definition in columns.items():
                if name not in existing:
                    connection.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN "{name}" {definition}'))
        if "users" in table_names:
            connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS "ix_users_username" ON "users" ("username")'))
