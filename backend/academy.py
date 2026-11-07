"""Academy curriculum tables in the same Postgres database as the portal.

Connection settings come from the environment through backend.db.connect.
No password, key, or file bytes are stored in this module.
"""

from __future__ import annotations

import re
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent / "academy_schema.sql"

BOARDS = (
    ("CBSE", "Central Board of Secondary Education"),
    ("ICSE", "Indian Certificate of Secondary Education"),
    ("WBBSE", "West Bengal Board of Secondary Education"),
)

SUBJECTS = (
    ("ai_cs", "AI & Computer Science"),
    ("science", "Science"),
    ("math", "Mathematics"),
)

GRADES = (7, 8, 9, 10, 11, 12)

# Class 7 AI & Computer Science titles already shown on the modules page.
# Each row is one lesson, one video, one PPT, one assignment, one quiz, and one lab.
EXAMPLE_MODULES = (
    {
        "title": "Digital foundations",
        "summary": "4 lessons · 1 quiz",
        "tool_key": "computer",
        "lesson": "What makes a computer work",
        "question": "Which habit keeps a school account safer?",
        "choices": (
            ("Using a long unique password", True),
            ("Reusing one password everywhere", False),
            ("Sharing a password with a classmate", False),
        ),
        "task": "List three ways you keep a school account safe.",
    },
    {
        "title": "Meet artificial intelligence",
        "summary": "5 lessons · 1 quiz",
        "tool_key": "generative",
        "lesson": "Where AI shows up around you",
        "question": "Which example is an AI system?",
        "choices": (
            ("A map app that suggests a faster route", True),
            ("A paper notebook", False),
            ("A wooden ruler", False),
        ),
        "task": "Name two AI tools you have seen and what each one does.",
    },
    {
        "title": "Robots around us",
        "summary": "4 lessons · 1 project",
        "tool_key": "python",
        "lesson": "Robots at home and at school",
        "question": "What can a robot use to notice the world around it?",
        "choices": (
            ("Sensors", True),
            ("A closed book", False),
            ("A blank wall", False),
        ),
        "task": "Describe one robot and the job it does.",
    },
    {
        "title": "Thinking like a programmer",
        "summary": "5 lessons · 1 quiz",
        "tool_key": "python",
        "lesson": "Steps, choices, and repeats",
        "question": "Which list is an algorithm?",
        "choices": (
            ("Step-by-step instructions that finish a task", True),
            ("A random set of words", False),
            ("A picture with no labels", False),
        ),
        "task": "Write the steps to make a cup of tea in order.",
    },
    {
        "title": "Python basics",
        "summary": "6 lessons · 1 project",
        "tool_key": "python",
        "lesson": "Your first Python program",
        "question": "What does a variable do in Python?",
        "choices": (
            ("It stores a value you can use later", True),
            ("It turns the computer off", False),
            ("It prints the screen", False),
        ),
        "task": "Write a short Python snippet that stores your name and prints it.",
    },
    {
        "title": "Creative problem solving",
        "summary": "4 lessons · 1 activity",
        "tool_key": "data",
        "lesson": "Break a problem into smaller parts",
        "question": "What is a useful first step when a problem feels too big?",
        "choices": (
            ("Split it into smaller questions", True),
            ("Skip the problem", False),
            ("Guess once and stop", False),
        ),
        "task": "Split one school problem into three smaller questions.",
    },
    {
        "title": "Build your first chatbot",
        "summary": "5 lessons · 1 project",
        "tool_key": "generative",
        "lesson": "A chatbot that answers one question",
        "question": "What should a class chatbot do when it does not know an answer?",
        "choices": (
            ("Say it does not know and ask for help", True),
            ("Invent a fact", False),
            ("Share a private password", False),
        ),
        "task": "Write three questions your chatbot should be able to answer.",
    },
    {
        "title": "Your capstone adventure",
        "summary": "3 lessons · 1 final project",
        "tool_key": "java",
        "lesson": "Plan the final project",
        "question": "What belongs in a project plan?",
        "choices": (
            ("The goal, the steps, and how you will check it", True),
            ("Only a title", False),
            ("Someone else's password", False),
        ),
        "task": "Write the goal of your final project in one sentence.",
    },
)

_DOLLAR = re.compile(r"\$[A-Za-z0-9_]*\$")
_STUDENT_FK = "student_id uuid NOT NULL REFERENCES public.students (id) ON DELETE CASCADE,"


def _statements(sql: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    index = 0
    dollar = None
    while index < len(sql):
        if dollar is not None:
            if sql.startswith(dollar, index):
                buf.append(dollar)
                index += len(dollar)
                dollar = None
                continue
            buf.append(sql[index])
            index += 1
            continue
        marker = _DOLLAR.match(sql, index)
        if marker and sql[index] == "$":
            dollar = marker.group(0)
            buf.append(dollar)
            index += len(dollar)
            continue
        if sql[index] == ";":
            statement = "".join(buf).strip()
            if statement:
                parts.append(statement)
            buf = []
            index += 1
            continue
        buf.append(sql[index])
        index += 1
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def _apply_schema(conn) -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    students = conn.execute("SELECT to_regclass('public.students') AS name").fetchone()["name"]
    if students is None:
        sql = sql.replace(_STUDENT_FK, "student_id uuid NOT NULL,")
    for statement in _statements(sql):
        conn.execute(statement)
    if students is None:
        return
    conn.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'enrollments_student_id_fkey'
              AND connamespace = 'academy'::regnamespace
          ) THEN
            ALTER TABLE academy.enrollments
              ADD CONSTRAINT enrollments_student_id_fkey
              FOREIGN KEY (student_id) REFERENCES public.students (id) ON DELETE CASCADE;
          END IF;
        END $$
        """
    )


def _seed(conn) -> None:
    existing = conn.execute("SELECT COUNT(*) AS n FROM academy.boards").fetchone()["n"]
    if existing:
        return

    board_ids: dict[str, str] = {}
    for code, name in BOARDS:
        row = conn.execute(
            "INSERT INTO academy.boards (code, name) VALUES (%s, %s) RETURNING id",
            (code, name),
        ).fetchone()
        board_ids[code] = row["id"]

    subject_ids: dict[str, str] = {}
    for code, name in SUBJECTS:
        row = conn.execute(
            "INSERT INTO academy.subjects (code, name) VALUES (%s, %s) RETURNING id",
            (code, name),
        ).fetchone()
        subject_ids[code] = row["id"]

    class_ids: dict[tuple[str, int], str] = {}
    for code in board_ids:
        for grade in GRADES:
            row = conn.execute(
                """
                INSERT INTO academy.classes (board_id, grade, name)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (board_ids[code], grade, f"Class {grade}"),
            ).fetchone()
            class_ids[(code, grade)] = row["id"]

    offering_ids: dict[tuple[str, int, str], str] = {}
    for (board_code, grade), class_id in class_ids.items():
        for subject_code in subject_ids:
            row = conn.execute(
                """
                INSERT INTO academy.offerings (class_id, subject_id)
                VALUES (%s, %s)
                RETURNING id
                """,
                (class_id, subject_ids[subject_code]),
            ).fetchone()
            offering_ids[(board_code, grade, subject_code)] = row["id"]

    _seed_example(conn, offering_ids[("CBSE", 7, "ai_cs")])


def _seed_example(conn, offering_id: str) -> None:
    for index, item in enumerate(EXAMPLE_MODULES, start=1):
        module = conn.execute(
            """
            INSERT INTO academy.modules (offering_id, sequence_no, title, summary)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (offering_id, index, item["title"], item["summary"]),
        ).fetchone()
        lesson = conn.execute(
            """
            INSERT INTO academy.lessons (module_id, sequence_no, title, summary)
            VALUES (%s, 1, %s, %s)
            RETURNING id
            """,
            (module["id"], item["lesson"], item["summary"]),
        ).fetchone()
        slug = f"{index:02d}"
        base = f"lake://edulake/raw/academy/cbse/class-7/ai-cs/{slug}"
        conn.execute(
            """
            INSERT INTO academy.lesson_files (lesson_id, kind, file_name, content_type, storage_uri)
            VALUES (%s, 'video', %s, 'video/mp4', %s)
            """,
            (lesson["id"], "lesson-1.mp4", f"{base}/lesson-1.mp4"),
        )
        conn.execute(
            """
            INSERT INTO academy.lesson_files (lesson_id, kind, file_name, content_type, storage_uri)
            VALUES (%s, 'ppt', %s, %s, %s)
            """,
            (
                lesson["id"],
                "lesson-1.pptx",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                f"{base}/lesson-1.pptx",
            ),
        )
        assignment = conn.execute(
            """
            INSERT INTO academy.assignments (module_id, title, instructions)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (
                module["id"],
                f"{item['title']} assignment",
                "This assignment opens after the module is completed.",
            ),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO academy.assignment_tasks (assignment_id, sequence_no, prompt)
            VALUES (%s, 1, %s)
            """,
            (assignment["id"], item["task"]),
        )
        quiz = conn.execute(
            """
            INSERT INTO academy.quizzes (module_id, title, pass_mark)
            VALUES (%s, %s, 40)
            RETURNING id
            """,
            (module["id"], f"{item['title']} quiz"),
        ).fetchone()
        question = conn.execute(
            """
            INSERT INTO academy.quiz_questions (quiz_id, sequence_no, prompt, question_type)
            VALUES (%s, 1, %s, 'mcq')
            RETURNING id
            """,
            (quiz["id"], item["question"]),
        ).fetchone()
        for label, correct in item["choices"]:
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
            (
                module["id"],
                f"{item['title']} lab",
                item["tool_key"],
                "Complete the lab activity for this module.",
            ),
        )


# Two sample students in each class. Every student enrolls in AI & Computer Science.
# Modules belong to that class and board only.
COHORTS = (
    {
        "board": "CBSE",
        "grade": 10,
        "students": (
            ("STU-ACADEMY-CBSE-10-01", "Meera", "Iyer", 88),
            ("STU-ACADEMY-CBSE-10-02", "Arun", "Bose", 76),
        ),
        "modules": (
            {
                "title": "Python for data",
                "tool_key": "python",
                "lessons": (
                    {
                        "title": "Lists and tables",
                        "task": "Write three rows of a class survey table.",
                        "question": "What does a list hold?",
                        "choices": (("Several values in order", True), ("A single password", False)),
                    },
                    {
                        "title": "Reading a table",
                        "task": "Name the columns in a two-column table.",
                        "question": "What is a row in a table?",
                        "choices": (("One record made of fields", True), ("The title of a slide", False)),
                    },
                ),
            },
            {
                "title": "AI project cycle",
                "tool_key": "generative",
                "lessons": (
                    {
                        "title": "Scope the problem",
                        "task": "Write the goal of a school AI project in one sentence.",
                        "question": "What is the first step of an AI project?",
                        "choices": (("Define the problem", True), ("Hide the data", False)),
                    },
                    {
                        "title": "Check the result",
                        "task": "List one way to tell that a prediction is wrong.",
                        "question": "Why test a model before using it?",
                        "choices": (("To see whether its answers hold up", True), ("To skip the lesson", False)),
                    },
                ),
            },
        ),
    },
    {
        "board": "ICSE",
        "grade": 9,
        "students": (
            ("STU-ACADEMY-ICSE-9-01", "Neel", "Roy", 91),
            ("STU-ACADEMY-ICSE-9-02", "Sara", "Ghosh", 84),
        ),
        "modules": (
            {
                "title": "Logic and Java",
                "tool_key": "java",
                "lessons": (
                    {
                        "title": "Conditions",
                        "task": "Write a condition that checks a passing mark.",
                        "question": "Which statement chooses between two paths?",
                        "choices": (("if / else", True), ("A folder name", False)),
                    },
                    {
                        "title": "Loops",
                        "task": "Describe a loop that prints the numbers 1 to 5.",
                        "question": "What does a loop do?",
                        "choices": (("Repeats steps until a stop condition", True), ("Stores a video", False)),
                    },
                ),
            },
            {
                "title": "Learning from examples",
                "tool_key": "python",
                "lessons": (
                    {
                        "title": "Labels and features",
                        "task": "Name two features you could use to sort books.",
                        "question": "What is a label in a training example?",
                        "choices": (("The answer the example is known to have", True), ("The computer's power cable", False)),
                    },
                    {
                        "title": "Training and testing",
                        "task": "Explain why test examples should differ from training examples.",
                        "question": "Why keep some examples back for testing?",
                        "choices": (("To check the model on examples it has not memorized", True), ("To delete the dataset", False)),
                    },
                ),
            },
        ),
    },
    {
        "board": "WBBSE",
        "grade": 8,
        "students": (
            ("STU-ACADEMY-WBBSE-8-01", "Ani", "Das", 80),
            ("STU-ACADEMY-WBBSE-8-02", "Ruhi", "Sen", 73),
        ),
        "modules": (
            {
                "title": "Computers in daily life",
                "tool_key": "computer",
                "lessons": (
                    {
                        "title": "Input and output",
                        "task": "Name one input device and one output device.",
                        "question": "Which device is an input device?",
                        "choices": (("A keyboard", True), ("A speaker", False)),
                    },
                    {
                        "title": "Files and folders",
                        "task": "Sketch a folder that holds two school files.",
                        "question": "What is a folder for?",
                        "choices": (("Grouping files so they can be found", True), ("Running a quiz", False)),
                    },
                ),
            },
            {
                "title": "Data and patterns",
                "tool_key": "data",
                "lessons": (
                    {
                        "title": "Collect a small dataset",
                        "task": "Collect five counts, such as books read this month.",
                        "question": "What belongs in a small dataset?",
                        "choices": (("Recorded values about one question", True), ("A student's password", False)),
                    },
                    {
                        "title": "Read a bar chart",
                        "task": "Say which bar is tallest in a chart you draw.",
                        "question": "What does a taller bar mean?",
                        "choices": (("A larger value", True), ("A missing lesson", False)),
                    },
                ),
            },
        ),
    },
)

_FILE_KINDS = (
    ("video", "mp4", "video/mp4"),
    ("ppt", "pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
    ("file", "pdf", "application/pdf"),
)


def _offering_id(conn, board: str, grade: int):
    row = conn.execute(
        """
        SELECT offering.id
        FROM academy.offerings AS offering
        JOIN academy.classes AS school_class ON school_class.id = offering.class_id
        JOIN academy.boards AS board ON board.id = school_class.board_id
        JOIN academy.subjects AS subject ON subject.id = offering.subject_id
        WHERE board.code = %s AND school_class.grade = %s AND subject.code = 'ai_cs'
        """,
        (board, grade),
    ).fetchone()
    return row["id"] if row else None


def _account_id(conn):
    row = conn.execute(
        """
        SELECT id FROM public.accounts
        WHERE account_type = 'School'
        ORDER BY created_at
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        row = conn.execute("SELECT id FROM public.accounts ORDER BY created_at LIMIT 1").fetchone()
    if row is not None:
        return row["id"]
    created = conn.execute(
        """
        INSERT INTO public.accounts (name, account_type, status)
        VALUES ('TechLearn Academy', 'School', 'Active')
        RETURNING id
        """
    ).fetchone()
    return created["id"]


def _ensure_lesson_files(conn, lesson_id, board: str, grade: int, module_no: int, lesson_no: int) -> None:
    base = f"lake://edulake/raw/academy/{board.lower()}/class-{grade}/ai-cs/{module_no:02d}"
    for kind, extension, content_type in _FILE_KINDS:
        file_name = f"lesson-{lesson_no}.{extension}"
        exists = conn.execute(
            """
            SELECT id FROM academy.lesson_files
            WHERE lesson_id = %s AND kind = %s AND file_name = %s
            """,
            (lesson_id, kind, file_name),
        ).fetchone()
        if exists:
            continue
        conn.execute(
            """
            INSERT INTO academy.lesson_files (lesson_id, kind, file_name, content_type, storage_uri)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (lesson_id, kind, file_name, content_type, f"{base}/{file_name}"),
        )


def _ensure_module(conn, offering_id, board: str, grade: int, module_no: int, item: dict) -> dict:
    module = conn.execute(
        """
        SELECT id FROM academy.modules
        WHERE offering_id = %s AND sequence_no = %s
        """,
        (offering_id, module_no),
    ).fetchone()
    if module is None:
        module = conn.execute(
            """
            INSERT INTO academy.modules (offering_id, sequence_no, title, summary)
            VALUES (%s, %s, %s, '2 lessons · 1 quiz')
            RETURNING id
            """,
            (offering_id, module_no, item["title"]),
        ).fetchone()
    lesson_ids = []
    for lesson_no, lesson in enumerate(item["lessons"], start=1):
        found = conn.execute(
            """
            SELECT id FROM academy.lessons
            WHERE module_id = %s AND sequence_no = %s
            """,
            (module["id"], lesson_no),
        ).fetchone()
        if found is None:
            found = conn.execute(
                """
                INSERT INTO academy.lessons (module_id, sequence_no, title, summary)
                VALUES (%s, %s, %s, 'Video, PPT, and file')
                RETURNING id
                """,
                (module["id"], lesson_no, lesson["title"]),
            ).fetchone()
        lesson_ids.append(found["id"])
        _ensure_lesson_files(conn, found["id"], board, grade, module_no, lesson_no)

    assignment = conn.execute(
        "SELECT id FROM academy.assignments WHERE module_id = %s",
        (module["id"],),
    ).fetchone()
    if assignment is None:
        assignment = conn.execute(
            """
            INSERT INTO academy.assignments (module_id, title, instructions)
            VALUES (%s, %s, 'This assignment opens after the module is completed.')
            RETURNING id
            """,
            (module["id"], f"{item['title']} assignment"),
        ).fetchone()
    for task_no, lesson in enumerate(item["lessons"], start=1):
        exists = conn.execute(
            """
            SELECT id FROM academy.assignment_tasks
            WHERE assignment_id = %s AND sequence_no = %s
            """,
            (assignment["id"], task_no),
        ).fetchone()
        if exists is None:
            conn.execute(
                """
                INSERT INTO academy.assignment_tasks (assignment_id, sequence_no, prompt)
                VALUES (%s, %s, %s)
                """,
                (assignment["id"], task_no, lesson["task"]),
            )

    quiz = conn.execute(
        "SELECT id FROM academy.quizzes WHERE module_id = %s",
        (module["id"],),
    ).fetchone()
    if quiz is None:
        quiz = conn.execute(
            """
            INSERT INTO academy.quizzes (module_id, title, pass_mark)
            VALUES (%s, %s, 40)
            RETURNING id
            """,
            (module["id"], f"{item['title']} quiz"),
        ).fetchone()
    questions = []
    for question_no, lesson in enumerate(item["lessons"], start=1):
        question = conn.execute(
            """
            SELECT id FROM academy.quiz_questions
            WHERE quiz_id = %s AND sequence_no = %s
            """,
            (quiz["id"], question_no),
        ).fetchone()
        if question is None:
            question = conn.execute(
                """
                INSERT INTO academy.quiz_questions (quiz_id, sequence_no, prompt, question_type)
                VALUES (%s, %s, %s, 'mcq')
                RETURNING id
                """,
                (quiz["id"], question_no, lesson["question"]),
            ).fetchone()
        correct_choice = None
        for label, correct in lesson["choices"]:
            choice = conn.execute(
                """
                SELECT id FROM academy.quiz_choices
                WHERE question_id = %s AND label = %s
                """,
                (question["id"], label),
            ).fetchone()
            if choice is None:
                choice = conn.execute(
                    """
                    INSERT INTO academy.quiz_choices (question_id, label, is_correct)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (question["id"], label, correct),
                ).fetchone()
            if correct:
                correct_choice = choice["id"]
        questions.append({"id": question["id"], "choice_id": correct_choice})

    lab = conn.execute(
        "SELECT id FROM academy.labs WHERE module_id = %s",
        (module["id"],),
    ).fetchone()
    if lab is None:
        lab = conn.execute(
            """
            INSERT INTO academy.labs (module_id, title, tool_key, instructions)
            VALUES (%s, %s, %s, 'Complete the lab activity for this module.')
            RETURNING id
            """,
            (module["id"], f"{item['title']} lab", item["tool_key"]),
        ).fetchone()
    return {
        "module_id": module["id"],
        "assignment_id": assignment["id"],
        "quiz_id": quiz["id"],
        "questions": questions,
        "lab_id": lab["id"],
        "lesson_ids": lesson_ids,
    }


def _ensure_student(conn, account_id, number: str, first_name: str, last_name: str, board: str, grade: int):
    found = conn.execute(
        "SELECT id FROM public.students WHERE student_number = %s",
        (number,),
    ).fetchone()
    if found:
        return found["id"]
    created = conn.execute(
        """
        INSERT INTO public.students
            (account_id, first_name, last_name, program_name, grade_level, enrollment_status, student_number, start_date)
        VALUES (%s, %s, %s, %s, %s, 'Enrolled', %s, DATE '2026-04-01')
        RETURNING id
        """,
        (account_id, first_name, last_name, f"{board} Class {grade} AI & Computer Science", str(grade), number),
    ).fetchone()
    return created["id"]


def _seed_cohort_examples(conn) -> None:
    """Add the class 10 CBSE, class 9 ICSE, and class 8 West Bengal examples."""
    students = conn.execute("SELECT to_regclass('public.students') AS name").fetchone()["name"]
    accounts = conn.execute("SELECT to_regclass('public.accounts') AS name").fetchone()["name"]
    if students is None or accounts is None:
        return
    account_id = _account_id(conn)
    for cohort in COHORTS:
        offering_id = _offering_id(conn, cohort["board"], cohort["grade"])
        if offering_id is None:
            continue
        modules = [
            _ensure_module(conn, offering_id, cohort["board"], cohort["grade"], index, item)
            for index, item in enumerate(cohort["modules"], start=1)
        ]
        first_module = modules[0]
        second_module = modules[1]
        for number, first_name, last_name, score in cohort["students"]:
            student_id = _ensure_student(
                conn, account_id, number, first_name, last_name, cohort["board"], cohort["grade"]
            )
            enrollment = conn.execute(
                """
                SELECT id FROM academy.enrollments
                WHERE student_id = %s AND offering_id = %s
                """,
                (student_id, offering_id),
            ).fetchone()
            if enrollment is None:
                enrollment = conn.execute(
                    """
                    INSERT INTO academy.enrollments (student_id, offering_id, status)
                    VALUES (%s, %s, 'enrolled')
                    RETURNING id
                    """,
                    (student_id, offering_id),
                ).fetchone()
            for module, status in ((first_module, "completed"), (second_module, "in_progress")):
                conn.execute(
                    """
                    INSERT INTO academy.module_progress (enrollment_id, module_id, status)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (enrollment_id, module_id) DO NOTHING
                    """,
                    (enrollment["id"], module["module_id"], status),
                )
            conn.execute(
                """
                UPDATE academy.assignment_submissions
                SET status = 'submitted', submitted_at = now(), score = %s
                WHERE enrollment_id = %s AND assignment_id = %s AND status = 'assigned'
                """,
                (score, enrollment["id"], first_module["assignment_id"]),
            )
            attempt = conn.execute(
                """
                SELECT id FROM academy.quiz_attempts
                WHERE enrollment_id = %s AND quiz_id = %s
                ORDER BY created_at
                LIMIT 1
                """,
                (enrollment["id"], first_module["quiz_id"]),
            ).fetchone()
            if attempt is None:
                attempt = conn.execute(
                    """
                    INSERT INTO academy.quiz_attempts (enrollment_id, quiz_id, score, submitted_at)
                    VALUES (%s, %s, %s, now())
                    RETURNING id
                    """,
                    (enrollment["id"], first_module["quiz_id"], score),
                ).fetchone()
            for question in first_module["questions"]:
                answered = conn.execute(
                    """
                    SELECT id FROM academy.quiz_answers
                    WHERE attempt_id = %s AND question_id = %s
                    """,
                    (attempt["id"], question["id"]),
                ).fetchone()
                if answered is None:
                    conn.execute(
                        """
                        INSERT INTO academy.quiz_answers (attempt_id, question_id, choice_id, answer_text)
                        VALUES (%s, %s, %s, '')
                        """,
                        (attempt["id"], question["id"], question["choice_id"]),
                    )
            conn.execute(
                """
                INSERT INTO academy.lab_sessions (enrollment_id, lab_id, status, started_at, completed_at)
                VALUES (%s, %s, 'completed', now(), now())
                ON CONFLICT (enrollment_id, lab_id) DO NOTHING
                """,
                (enrollment["id"], first_module["lab_id"]),
            )


def init_academy(conn) -> None:
    """Create academy tables and seed them once. The caller commits."""
    _apply_schema(conn)
    _seed(conn)
    _seed_cohort_examples(conn)
    from backend.academy_repair import repair_academy

    repair_academy(conn)


def ensure_academy() -> None:
    """Open a connection with the shared helper, then apply the academy schema."""
    from backend.db import connect

    conn = connect()
    try:
        init_academy(conn)
        conn.commit()
    finally:
        conn.close()
