"""Read the academy path: student, enrollment, offering, then modules and labs.

Pages and /api/academy use these queries. No passwords are selected.
"""

from __future__ import annotations

import re
from urllib.parse import quote

from fastapi import Request

from backend.db import connect, one, rows

_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

_STUDENT_SQL = """
SELECT s.id::text AS id, s.first_name, s.last_name, s.student_number, s.enrollment_status,
       s.program_name, s.grade_level
FROM public.students s
"""

TOOL_PAGES = {
    "python": ("/static/pages/python-lab.html", False),
    "data": ("/static/pages/data-lab.html", False),
    "java": ("/lab/java", False),
    "office": ("/static/pages/office-lab.html", True),
}
TOOL_ICONS = {
    "python": "code",
    "data": "chart",
    "generative": "spark",
    "office": "grid",
    "computer": "screen",
    "java": "java",
}


def portal_student(request: Request) -> dict | None:
    requested = (request.query_params.get("student_id") or request.cookies.get("spl_student") or "").strip()
    if requested and _UUID.match(requested):
        found = one(_STUDENT_SQL + " WHERE s.id = ?", (requested,))
        if found:
            return found
    found = one(
        _STUDENT_SQL + " WHERE s.first_name = ? AND s.last_name = ? ORDER BY s.created_at DESC LIMIT 1",
        ("Prithu", "Lahiri"),
    )
    if found:
        return found
    return one(_STUDENT_SQL + " ORDER BY s.created_at LIMIT 1")


def enrollments_for(student_id: str) -> list[dict]:
    return rows(
        """
        SELECT e.id::text AS enrollment_id, o.id::text AS offering_id,
               b.code AS board, c.grade, sub.code AS subject_code, sub.name AS subject, e.status
        FROM academy.enrollments e
        JOIN academy.offerings o ON o.id = e.offering_id
        JOIN academy.classes c ON c.id = o.class_id
        JOIN academy.boards b ON b.id = c.board_id
        JOIN academy.subjects sub ON sub.id = o.subject_id
        WHERE e.student_id = ? AND e.status = 'enrolled'
        ORDER BY CASE sub.code WHEN 'ai_cs' THEN 0 WHEN 'science' THEN 1 ELSE 2 END, b.code, c.grade
        """,
        (student_id,),
    )


def boards() -> list[dict]:
    return rows("SELECT code, name FROM academy.boards ORDER BY code")


def grades() -> list[int]:
    return [7, 8, 9, 10, 11, 12]


def modules_for(offering_id: str, enrollment_id: str) -> list[dict]:
    found = rows(
        """
        SELECT m.sequence_no, m.title, m.summary,
               COALESCE(p.status, 'locked') AS progress,
               l.title AS lesson_title,
               (SELECT COUNT(*) FROM academy.lesson_files f
                 JOIN academy.lessons lesson ON lesson.id = f.lesson_id
                 WHERE lesson.module_id = m.id AND f.kind = 'video') AS videos,
               (SELECT COUNT(*) FROM academy.lesson_files f
                 JOIN academy.lessons lesson ON lesson.id = f.lesson_id
                 WHERE lesson.module_id = m.id AND f.kind = 'ppt') AS ppts,
               (SELECT COUNT(*) FROM academy.lesson_files f
                 JOIN academy.lessons lesson ON lesson.id = f.lesson_id
                 WHERE lesson.module_id = m.id AND f.kind = 'file') AS files
        FROM academy.modules m
        LEFT JOIN academy.module_progress p
          ON p.module_id = m.id AND p.enrollment_id = ?
        LEFT JOIN LATERAL (
            SELECT title FROM academy.lessons
            WHERE module_id = m.id
            ORDER BY sequence_no
            LIMIT 1
        ) l ON true
        WHERE m.offering_id = ?
        ORDER BY m.sequence_no
        """,
        (enrollment_id, offering_id),
    )
    cards = []
    for item in found:
        progress = item["progress"]
        if progress == "completed":
            status, action, percent = "Completed", "", "100%"
        elif progress == "in_progress":
            status, action, percent = "In progress", "Resume", ""
        else:
            status, action, percent = "Not started", "", ""
        number = f"{int(item['sequence_no']):02d}"
        cards.append(
            {
                "number": number,
                "title": item["title"],
                "meta": item["summary"] or item["lesson_title"] or "",
                "status": status,
                "action": action,
                "percent": percent,
                "href": "",
                "videos": item["videos"],
                "ppts": item["ppts"],
                "files": item["files"],
            }
        )
    return cards


def labs_for(board: str, grade: int) -> list[dict]:
    found = rows(
        """
        SELECT lab.id::text AS id, lab.title, lab.tool_key, lab.instructions,
               m.title AS module_title, sub.name AS subject
        FROM academy.labs lab
        JOIN academy.modules m ON m.id = lab.module_id
        JOIN academy.offerings o ON o.id = m.offering_id
        JOIN academy.classes c ON c.id = o.class_id
        JOIN academy.boards b ON b.id = c.board_id
        JOIN academy.subjects sub ON sub.id = o.subject_id
        WHERE b.code = ? AND c.grade = ?
        ORDER BY sub.name, m.sequence_no
        """,
        (board, grade),
    )
    cards = []
    for item in found:
        href, same_tab = TOOL_PAGES.get(
            item["tool_key"],
            ("/chat?q=" + quote(f"{item['title']}. {item['instructions']}"), False),
        )
        cards.append(
            {
                "id": item["id"],
                "title": item["title"],
                "body": f"{item['subject']} · {item['module_title']}",
                "icon": TOOL_ICONS.get(item["tool_key"], "screen"),
                "href": f"/lab/open/{item['id']}",
                "same_tab": same_tab,
                "destination": href,
            }
        )
    return cards


def open_lab(student_id: str | None, lab_id: str) -> str | None:
    if not _UUID.match(lab_id):
        return None
    lab = one(
        """
        SELECT lab.id::text AS id, lab.tool_key, lab.title, lab.instructions,
               o.id::text AS offering_id
        FROM academy.labs lab
        JOIN academy.modules m ON m.id = lab.module_id
        JOIN academy.offerings o ON o.id = m.offering_id
        WHERE lab.id = ?
        """,
        (lab_id,),
    )
    if lab is None:
        return None
    if student_id:
        enrollment = one(
            """
            SELECT id::text AS id FROM academy.enrollments
            WHERE student_id = ? AND offering_id = ? AND status = 'enrolled'
            """,
            (student_id, lab["offering_id"]),
        )
        if enrollment:
            _start_session(enrollment["id"], lab_id)
    destination, _same = TOOL_PAGES.get(
        lab["tool_key"],
        ("/chat?q=" + quote(f"{lab['title']}. {lab['instructions']}"), False),
    )
    return destination


def _start_session(enrollment_id: str, lab_id: str) -> None:
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO academy.lab_sessions (enrollment_id, lab_id, status, started_at)
            VALUES (%s, %s, 'in_progress', now())
            ON CONFLICT (enrollment_id, lab_id) DO UPDATE
            SET status = CASE
                    WHEN academy.lab_sessions.status = 'completed' THEN academy.lab_sessions.status
                    ELSE 'in_progress'
                END,
                started_at = COALESCE(academy.lab_sessions.started_at, now())
            """,
            (enrollment_id, lab_id),
        )
        conn.commit()
    finally:
        conn.close()


def progress_for(student_id: str) -> dict:
    totals = one(
        """
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE p.status = 'completed') AS completed
        FROM academy.module_progress p
        JOIN academy.enrollments e ON e.id = p.enrollment_id
        WHERE e.student_id = ?
        """,
        (student_id,),
    ) or {"total": 0, "completed": 0}
    assignments = rows(
        """
        SELECT a.title AS name,
               COALESCE(to_char(s.submitted_at, 'DD Mon YYYY'), '—') AS submitted,
               COALESCE(s.score::text, '—') AS score,
               s.status
        FROM academy.assignment_submissions s
        JOIN academy.assignments a ON a.id = s.assignment_id
        JOIN academy.enrollments e ON e.id = s.enrollment_id
        WHERE e.student_id = ?
        ORDER BY s.created_at
        """,
        (student_id,),
    )
    quizzes = one(
        """
        SELECT COUNT(*) AS attempts, COALESCE(ROUND(AVG(q.score)), 0) AS average
        FROM academy.quiz_attempts q
        JOIN academy.enrollments e ON e.id = q.enrollment_id
        WHERE e.student_id = ? AND q.score IS NOT NULL
        """,
        (student_id,),
    ) or {"attempts": 0, "average": 0}
    labs = one(
        """
        SELECT COUNT(*) FILTER (WHERE s.status = 'completed') AS completed,
               COUNT(*) AS total
        FROM academy.lab_sessions s
        JOIN academy.enrollments e ON e.id = s.enrollment_id
        WHERE e.student_id = ?
        """,
        (student_id,),
    ) or {"completed": 0, "total": 0}
    nxt = one(
        """
        SELECT m.title
        FROM academy.module_progress p
        JOIN academy.modules m ON m.id = p.module_id
        JOIN academy.enrollments e ON e.id = p.enrollment_id
        WHERE e.student_id = ? AND p.status = 'in_progress'
        ORDER BY m.sequence_no
        LIMIT 1
        """,
        (student_id,),
    )
    total = int(totals["total"] or 0)
    completed = int(totals["completed"] or 0)
    percent = round(completed * 100 / total) if total else 0
    return {
        "total": total,
        "completed": completed,
        "percent": percent,
        "assignments": assignments,
        "quiz_average": int(quizzes["average"] or 0),
        "quiz_count": int(quizzes["attempts"] or 0),
        "labs_completed": int(labs["completed"] or 0),
        "labs_total": int(labs["total"] or 0),
        "next_title": nxt["title"] if nxt else "",
    }
