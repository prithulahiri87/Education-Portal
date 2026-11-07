"""Fill academy rows the portal flow needs. Runs after the schema seed.

Lesson files stay lake:// pointers. No passwords or file bytes are written here.
"""

from __future__ import annotations

_SUBJECT_MODULES = {
    "science": {
        "title": "Observe and record",
        "summary": "2 lessons · 1 quiz",
        "tool_key": "data",
        "lessons": ("Look closely", "Record what changed"),
        "question": "What belongs in a science observation?",
        "choices": (
            ("What you saw and when you saw it", True),
            ("A guess with no notes", False),
        ),
        "task": "Write one observation from a class experiment.",
    },
    "math": {
        "title": "Numbers and patterns",
        "summary": "2 lessons · 1 quiz",
        "tool_key": "computer",
        "lessons": ("Find the pattern", "Check the next number"),
        "question": "Which step checks a number pattern?",
        "choices": (
            ("Test the rule on the next number", True),
            ("Stop after the first number", False),
        ),
        "task": "Describe one number pattern and the next two terms.",
    },
}


def repair_academy(conn) -> None:
    _missing_files(conn)
    _office_lab(conn)
    _subject_modules(conn)
    _portal_student(conn)


def _missing_files(conn) -> None:
    conn.execute(
        """
        INSERT INTO academy.lesson_files (lesson_id, kind, file_name, content_type, storage_uri)
        SELECT lesson.id, 'file', 'lesson-notes.pdf', 'application/pdf',
               regexp_replace(video.storage_uri, '\\.[^/]+$', '') || '-notes.pdf'
        FROM academy.lessons AS lesson
        JOIN academy.lesson_files AS video
          ON video.lesson_id = lesson.id AND video.kind = 'video'
        WHERE video.storage_uri LIKE 'lake://%'
          AND NOT EXISTS (
            SELECT 1 FROM academy.lesson_files AS existing
            WHERE existing.lesson_id = lesson.id AND existing.kind = 'file'
          )
        """
    )


def _office_lab(conn) -> None:
    exists = conn.execute(
        "SELECT 1 FROM academy.labs WHERE tool_key = 'office' LIMIT 1"
    ).fetchone()
    if exists:
        return
    conn.execute(
        """
        UPDATE academy.labs AS lab
        SET tool_key = 'office',
            title = 'Digital documentation lab',
            instructions = 'Practise a class document in the office lab.'
        FROM academy.modules AS module
        WHERE lab.module_id = module.id
          AND module.title = 'Thinking like a programmer'
          AND lab.tool_key = 'python'
        """
    )


def _subject_modules(conn) -> None:
    offerings = conn.execute(
        """
        SELECT offering.id, board.code AS board, school_class.grade, subject.code AS subject
        FROM academy.offerings AS offering
        JOIN academy.classes AS school_class ON school_class.id = offering.class_id
        JOIN academy.boards AS board ON board.id = school_class.board_id
        JOIN academy.subjects AS subject ON subject.id = offering.subject_id
        WHERE subject.code IN ('science', 'math')
          AND NOT EXISTS (
            SELECT 1 FROM academy.modules AS module WHERE module.offering_id = offering.id
          )
        """
    ).fetchall()
    for offering in offerings:
        _insert_module(conn, offering)


def _insert_module(conn, offering) -> None:
    spec = _SUBJECT_MODULES[offering["subject"]]
    module = conn.execute(
        """
        INSERT INTO academy.modules (offering_id, sequence_no, title, summary)
        VALUES (%s, 1, %s, %s)
        RETURNING id
        """,
        (offering["id"], spec["title"], spec["summary"]),
    ).fetchone()
    board = offering["board"].lower()
    grade = offering["grade"]
    subject = offering["subject"]
    for index, title in enumerate(spec["lessons"], start=1):
        lesson = conn.execute(
            """
            INSERT INTO academy.lessons (module_id, sequence_no, title, summary)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (module["id"], index, title, spec["summary"]),
        ).fetchone()
        base = f"lake://edulake/raw/academy/{board}/class-{grade}/{subject}/01/lesson-{index}"
        for kind, name, content_type, suffix in (
            ("video", f"lesson-{index}.mp4", "video/mp4", ".mp4"),
            (
                "ppt",
                f"lesson-{index}.pptx",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                ".pptx",
            ),
            ("file", f"lesson-{index}.pdf", "application/pdf", ".pdf"),
        ):
            conn.execute(
                """
                INSERT INTO academy.lesson_files (lesson_id, kind, file_name, content_type, storage_uri)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (lesson["id"], kind, name, content_type, f"{base}{suffix}"),
            )
    assignment = conn.execute(
        """
        INSERT INTO academy.assignments (module_id, title, instructions)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (module["id"], f"{spec['title']} assignment", "This assignment opens after the module is completed."),
    ).fetchone()
    conn.execute(
        """
        INSERT INTO academy.assignment_tasks (assignment_id, sequence_no, prompt)
        VALUES (%s, 1, %s)
        """,
        (assignment["id"], spec["task"]),
    )
    quiz = conn.execute(
        """
        INSERT INTO academy.quizzes (module_id, title, pass_mark)
        VALUES (%s, %s, 40)
        RETURNING id
        """,
        (module["id"], f"{spec['title']} quiz"),
    ).fetchone()
    question = conn.execute(
        """
        INSERT INTO academy.quiz_questions (quiz_id, sequence_no, prompt, question_type)
        VALUES (%s, 1, %s, 'mcq')
        RETURNING id
        """,
        (quiz["id"], spec["question"]),
    ).fetchone()
    for label, correct in spec["choices"]:
        conn.execute(
            """
            INSERT INTO academy.quiz_choices (question_id, label, is_correct)
            VALUES (%s, %s, %s)
            """,
            (question["id"], label, correct),
        )
    conn.execute(
        """
        INSERT INTO academy.labs (module_id, title, tool_key, instructions)
        VALUES (%s, %s, %s, %s)
        """,
        (module["id"], f"{spec['title']} lab", spec["tool_key"], "Complete the lab activity for this module."),
    )


def _portal_student(conn) -> None:
    student = conn.execute(
        """
        SELECT id FROM public.students
        WHERE first_name = %s AND last_name = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        ("Prithu", "Lahiri"),
    ).fetchone()
    if student is None:
        return
    offerings = conn.execute(
        """
        SELECT offering.id, subject.code AS subject
        FROM academy.offerings AS offering
        JOIN academy.classes AS school_class ON school_class.id = offering.class_id
        JOIN academy.boards AS board ON board.id = school_class.board_id
        JOIN academy.subjects AS subject ON subject.id = offering.subject_id
        WHERE board.code = 'CBSE' AND school_class.grade = 7
          AND subject.code IN ('ai_cs', 'science', 'math')
        """
    ).fetchall()
    for offering in offerings:
        enrollment = conn.execute(
            """
            INSERT INTO academy.enrollments (student_id, offering_id, status)
            VALUES (%s, %s, 'enrolled')
            ON CONFLICT (student_id, offering_id) DO NOTHING
            RETURNING id
            """,
            (student["id"], offering["id"]),
        ).fetchone()
        if enrollment is None:
            continue
        modules = conn.execute(
            """
            SELECT id, sequence_no FROM academy.modules
            WHERE offering_id = %s
            ORDER BY sequence_no
            """,
            (offering["id"],),
        ).fetchall()
        for module in modules:
            if offering["subject"] == "ai_cs" and module["sequence_no"] <= 4:
                status = "completed"
            elif offering["subject"] == "ai_cs" and module["sequence_no"] == 5:
                status = "in_progress"
            elif offering["subject"] == "ai_cs":
                status = "locked"
            else:
                status = "in_progress"
            conn.execute(
                """
                INSERT INTO academy.module_progress (enrollment_id, module_id, status)
                VALUES (%s, %s, %s)
                ON CONFLICT (enrollment_id, module_id) DO NOTHING
                """,
                (enrollment["id"], module["id"], status),
            )
