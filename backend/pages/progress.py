"""Progress page. Counts come from the student's academy enrollment."""

from fastapi import APIRouter, Request

from backend.academy_flow import portal_student, progress_for
from backend.pages.common import shell, templates

router = APIRouter()


@router.get("/progress")
def progress_page(request: Request):
    student = portal_student(request)
    snapshot = progress_for(student["id"]) if student else {
        "total": 0,
        "completed": 0,
        "percent": 0,
        "assignments": [],
        "quiz_average": 0,
        "quiz_count": 0,
        "labs_completed": 0,
        "labs_total": 0,
        "next_title": "",
    }
    context = shell("progress")
    context["progress"] = snapshot
    return templates.TemplateResponse(request, "pages/progress.html", context)
