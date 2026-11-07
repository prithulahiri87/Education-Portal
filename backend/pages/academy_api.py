"""JSON view of the academy flow: student, modules, and labs."""

from fastapi import APIRouter, HTTPException, Request

from backend.academy_flow import enrollments_for, labs_for, modules_for, open_lab, portal_student

router = APIRouter()


def _student(request: Request) -> dict:
    student = portal_student(request)
    if student is None:
        raise HTTPException(status_code=404, detail="No student is available.")
    return student


@router.get("/api/academy/student")
def academy_student(request: Request):
    student = _student(request)
    return {"student": student, "enrollments": enrollments_for(student["id"])}


@router.get("/api/academy/modules")
def academy_modules(request: Request, offering_id: str = ""):
    student = _student(request)
    enrolled = enrollments_for(student["id"])
    chosen = next((item for item in enrolled if item["offering_id"] == offering_id), None)
    if chosen is None:
        chosen = next((item for item in enrolled if item["subject_code"] == "ai_cs"), None)
    if chosen is None and enrolled:
        chosen = enrolled[0]
    if chosen is None:
        return {"offering": None, "modules": []}
    return {
        "offering": chosen,
        "modules": modules_for(chosen["offering_id"], chosen["enrollment_id"]),
    }


@router.get("/api/academy/labs")
def academy_labs(board: str, grade: int):
    return {"board": board, "grade": grade, "labs": labs_for(board, grade)}


@router.post("/api/academy/labs/{lab_id}/sessions")
def academy_lab_session(lab_id: str, request: Request):
    student = portal_student(request)
    destination = open_lab(student["id"] if student else None, lab_id)
    if destination is None:
        raise HTTPException(status_code=404, detail="Lab not found.")
    return {"href": destination}
