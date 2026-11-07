"""Home page. The profile is a row in the edcrm students table."""

from __future__ import annotations

import re

from fastapi import APIRouter, Request

from backend.academy_flow import enrollments_for
from backend.db import one, rows
from backend.pages.common import shell, templates

router = APIRouter()

_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_GRADES = {"7", "8", "9", "10"}

_STUDENT_SQL = """
SELECT s.id, s.first_name, s.last_name, s.student_number, s.enrollment_status,
       s.program_name, s.grade_level, s.start_date, s.account_id,
       a.name AS account_name
FROM public.students s
LEFT JOIN public.accounts a ON a.id = s.account_id
"""


def _initials(first_name: str, last_name: str) -> str:
    return f"{(first_name or ' ')[0]}{(last_name or ' ')[0]}".upper()


def _class_code(title: str) -> str:
    words = [word for word in title.split() if word[:1].isalnum()]
    if not words:
        return "C"
    if len(words) == 1:
        return words[0][:2].upper()
    return "".join(word[0] for word in words[:3]).upper()


def _class_label(grade_level: str | None) -> str:
    grade = (grade_level or "").strip()
    if grade.isdigit():
        return f"Class {grade}"
    return grade or "—"


def _profile(raw: dict) -> dict:
    start = raw["start_date"]
    return {
        "id": raw["id"],
        "name": f"{raw['first_name']} {raw['last_name']}".strip(),
        "initials": _initials(raw["first_name"], raw["last_name"]),
        "student_code": raw["student_number"],
        "enrollment": raw["enrollment_status"],
        "degree": f"CBSE Class {grade}" if (grade := (raw.get("grade_level") or "").strip()).isdigit() else (raw["program_name"] or "—"),
        "account_name": raw.get("account_name") or "—",
        "advisor": "—",
        "join_date": start.strftime("%b %Y") if start else "—",
        "semester": _class_label(raw["grade_level"]),
        "credits_earned": 0,
        "credits_total": 0,
    }


_UPLOAD_COPY = {
    "Documents": "Notes, articles, and files",
    "Videos": "Intro to Python lessons",
    "Video Classes": "Live class recordings",
    "Resources": "Slides, labs, and references",
}


def _upload_items() -> list[dict]:
    items = rows("SELECT * FROM content_items ORDER BY id")
    for item in items:
        item["summary"] = _UPLOAD_COPY.get(item["name"], item["summary"])
    return items


def _load_student(student_id: str | None) -> dict | None:
    if not student_id or not _UUID.match(student_id):
        return None
    return one(_STUDENT_SQL + " WHERE s.id = ?", (student_id,))


@router.get("/")
def home_page(request: Request):
    requested_id = (request.query_params.get("student_id") or request.cookies.get("spl_student") or "").strip()
    requested_class = (request.query_params.get("class") or "").strip()
    raw = _load_student(requested_id)
    if raw is None:
        raw = one(
            _STUDENT_SQL + " WHERE s.first_name = ? AND s.last_name = ? ORDER BY s.created_at DESC LIMIT 1",
            ("Prithu", "Lahiri"),
        )
    if raw is None:
        raw = one(_STUDENT_SQL + " ORDER BY s.created_at LIMIT 1")
    if raw is not None and not (raw.get("grade_level") or "").strip() and requested_class in _GRADES:
        raw["grade_level"] = requested_class
    student = _profile(raw) if raw else None
    student_id = student["id"] if student else None
    classes = []
    attendance = []
    progress_rows = []
    assignments = []
    if student_id is not None:
        teachers = rows(
            """
            SELECT DISTINCT t.first_name, t.last_name
            FROM public.enrollments e
            JOIN public.teachers t ON t.id = e.teacher_id
            WHERE e.student_id = ?
            ORDER BY t.last_name, t.first_name
            """,
            (student_id,),
        )
        if teachers:
            student["advisor"] = ", ".join(f"{item['first_name']} {item['last_name']}" for item in teachers)
        credit = one(
            """
            SELECT COALESCE(SUM(e.weeks_completed), 0) AS earned,
                   COALESCE(SUM(c.duration_weeks), 0) AS total
            FROM public.enrollments e
            JOIN public.courses c ON c.id = e.course_id
            WHERE e.student_id = ?
            """,
            (student_id,),
        )
        if credit:
            student["credits_earned"] = int(credit["earned"])
            student["credits_total"] = int(credit["total"])
        classes = [
            {"code": _class_code(item["title"]), "title": item["title"], "summary": item["summary"]}
            for item in rows(
                """
                SELECT c.title, c.summary
                FROM public.enrollments e
                JOIN public.courses c ON c.id = e.course_id
                WHERE e.student_id = ?
                ORDER BY c.title
                """,
                (student_id,),
            )
        ]
        progress_rows = rows(
            """
            SELECT c.title AS label,
                   CASE
                       WHEN c.duration_weeks > 0
                       THEN ROUND(e.weeks_completed * 100.0 / c.duration_weeks)::int
                       ELSE 0
                   END AS percent,
                   '' AS bar_class
            FROM public.enrollments e
            JOIN public.courses c ON c.id = e.course_id
            WHERE e.student_id = ?
            ORDER BY c.title
            """,
            (student_id,),
        )
        for index, item in enumerate(progress_rows):
            item["bar_class"] = "alt" if index % 2 else ""
            attendance.append({"label": f"{item['label']} attendance", "percent": item["percent"]})
        assignments = []
        for item in rows(
            """
            SELECT a.title AS name, sa.assigned_at, sa.submitted_at, sa.status AS score
            FROM public.student_assignments sa
            JOIN public.assignments a ON a.id = sa.assignment_id
            WHERE sa.student_id = ?
            ORDER BY sa.assigned_at
            """,
            (student_id,),
        ):
            assigned = item["assigned_at"]
            submitted = item["submitted_at"]
            assignments.append(
                {
                    "name": item["name"],
                    "due_date": assigned.strftime("%m/%d/%Y") if assigned else "—",
                    "submitted_date": submitted.strftime("%m/%d/%Y") if submitted else "—",
                    "score": item["score"],
                }
            )
    offerings = enrollments_for(str(student_id)) if student_id is not None else []
    if student is not None and offerings:
        primary = next((item for item in offerings if item["subject_code"] == "ai_cs"), offerings[0])
        student["degree"] = f"{primary['board']} Class {primary['grade']}"
        student["semester"] = f"Class {primary['grade']}"
    context = shell("home")
    context.update(
        {
            "student": student,
            "classes": classes,
            "offerings": offerings,
            "session": None,
            "content_items": _upload_items(),
            "attendance": attendance,
            "progress_rows": progress_rows,
            "assignments": assignments,
        }
    )
    response = templates.TemplateResponse(request, "pages/home.html", context)
    passed_id = (request.query_params.get("student_id") or "").strip()
    if raw is not None and passed_id and str(raw["id"]).lower() == passed_id.lower():
        response.set_cookie(
            "spl_student",
            str(raw["id"]),
            max_age=8 * 60 * 60,
            httponly=True,
            samesite="lax",
            path="/",
        )
    return response
