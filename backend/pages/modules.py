"""Course Modules page. Modules come from the student's academy offering."""

from fastapi import APIRouter, Request

from backend.academy_flow import enrollments_for, modules_for, portal_student
from backend.pages.common import shell, templates

router = APIRouter()


@router.get("/modules")
def modules_page(request: Request):
    student = portal_student(request)
    enrolled = enrollments_for(student["id"]) if student else []
    requested = (request.query_params.get("offering") or "").strip()
    chosen = next((item for item in enrolled if item["offering_id"] == requested), None)
    if chosen is None:
        chosen = next((item for item in enrolled if item["subject_code"] == "ai_cs"), None)
    if chosen is None and enrolled:
        chosen = enrolled[0]
    modules = []
    completed = 0
    if chosen:
        modules = modules_for(chosen["offering_id"], chosen["enrollment_id"])
        lab_href = f"/lab?board={chosen['board']}&grade={chosen['grade']}"
        for item in modules:
            if item["status"] == "Completed":
                completed += 1
            elif item["action"]:
                item["href"] = lab_href
    total = len(modules)
    percent = round(completed * 100 / total) if total else 0
    context = shell("modules")
    context.update(
        {
            "modules": modules,
            "offerings": enrolled,
            "offering": chosen,
            "completed": completed,
            "total": total,
            "percent": percent,
            "continue_href": f"/lab?board={chosen['board']}&grade={chosen['grade']}" if chosen else "/lab",
        }
    )
    return templates.TemplateResponse(request, "pages/modules.html", context)
