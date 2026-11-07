"""Lab page. Tool cards follow the Computer & AI Learning Lab screen."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from backend.academy_flow import boards, grades, labs_for, open_lab, portal_student, enrollments_for
from backend.pages.common import shell, templates

router = APIRouter()

_CLASS_NAME = re.compile(r"(?:public\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)")
_MAX_OUTPUT = 8000


class JavaRun(BaseModel):
    code: str = Field(max_length=20000)


def _clip(text: str) -> str:
    cleaned = text.strip()
    if len(cleaned) <= _MAX_OUTPUT:
        return cleaned
    return cleaned[:_MAX_OUTPUT] + "\n… output truncated"


def _run_java(code: str) -> str:
    source = code.replace("\r\n", "\n").strip()
    if not source:
        return "Add a Java program, then click Run Java."
    found = _CLASS_NAME.search(source)
    if found is None:
        return "Add a class, for example: public class Main { ... }"
    class_name = found.group(1)
    javac = shutil.which("javac")
    java = shutil.which("java")
    if not javac or not java:
        return "Java is not installed on this computer, so the program cannot run here."
    try:
        with tempfile.TemporaryDirectory(prefix="java-lab-") as folder:
            path = Path(folder) / f"{class_name}.java"
            path.write_text(source + "\n", encoding="utf-8")
            compiled = subprocess.run(
                [javac, path.name],
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=12,
            )
            if compiled.returncode != 0:
                return _clip(compiled.stderr or compiled.stdout or "The program did not compile.")
            ran = subprocess.run(
                [java, "-cp", folder, class_name],
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=8,
            )
    except subprocess.TimeoutExpired:
        return "The program took too long and was stopped."
    text = (ran.stdout or "") + (("\n" + ran.stderr) if ran.stderr else "")
    return _clip(text) or "No output"


@router.get("/lab")
def lab_page(request: Request):
    student = portal_student(request)
    enrolled = enrollments_for(student["id"]) if student else []
    primary = next((item for item in enrolled if item["subject_code"] == "ai_cs"), enrolled[0] if enrolled else None)
    board_rows = boards()
    grade_rows = grades()
    selected_board = (request.query_params.get("board") or (primary["board"] if primary else "CBSE")).upper()
    try:
        selected_grade = int(request.query_params.get("grade") or (primary["grade"] if primary else 7))
    except ValueError:
        selected_grade = primary["grade"] if primary else 7
    codes = {item["code"] for item in board_rows}
    if selected_board not in codes:
        selected_board = primary["board"] if primary else "CBSE"
    if selected_grade not in grade_rows:
        selected_grade = primary["grade"] if primary else 7
    context = shell("lab")
    context.update(
        {
            "boards": board_rows,
            "classes": grade_rows,
            "selected_board": selected_board,
            "selected_grade": selected_grade,
            "tools": labs_for(selected_board, selected_grade),
        }
    )
    return templates.TemplateResponse(request, "pages/lab.html", context)


@router.get("/lab/open/{lab_id}")
def lab_open(lab_id: str, request: Request):
    student = portal_student(request)
    destination = open_lab(student["id"] if student else None, lab_id)
    if destination is None:
        return RedirectResponse("/lab", status_code=303)
    return RedirectResponse(destination, status_code=303)


@router.get("/lab/java")
def java_lab_page(request: Request):
    return templates.TemplateResponse(request, "pages/java_lab.html", {"request": request})


@router.post("/api/java/run")
def java_run(body: JavaRun):
    return {"output": _run_java(body.code)}
