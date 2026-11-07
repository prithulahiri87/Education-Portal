-- Academy curriculum for the student portal.
-- Student rows stay in public.students. Video and PPT bytes stay in the lake.
-- Each lesson_files.storage_uri is a lake:// pointer, never a file or a secret.

CREATE SCHEMA IF NOT EXISTS academy;

CREATE TABLE IF NOT EXISTS academy.boards (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS academy.classes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  board_id uuid NOT NULL REFERENCES academy.boards (id) ON DELETE CASCADE,
  grade integer NOT NULL CHECK (grade BETWEEN 7 AND 12),
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (board_id, grade)
);

CREATE TABLE IF NOT EXISTS academy.subjects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code text NOT NULL UNIQUE,
  name text NOT NULL UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Junction of class and subject. Parent of that board's modules.
CREATE TABLE IF NOT EXISTS academy.offerings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  class_id uuid NOT NULL REFERENCES academy.classes (id) ON DELETE CASCADE,
  subject_id uuid NOT NULL REFERENCES academy.subjects (id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (class_id, subject_id)
);

CREATE TABLE IF NOT EXISTS academy.modules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  offering_id uuid NOT NULL REFERENCES academy.offerings (id) ON DELETE CASCADE,
  sequence_no integer NOT NULL CHECK (sequence_no > 0),
  title text NOT NULL,
  summary text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (offering_id, sequence_no)
);

CREATE TABLE IF NOT EXISTS academy.lessons (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  module_id uuid NOT NULL REFERENCES academy.modules (id) ON DELETE CASCADE,
  sequence_no integer NOT NULL CHECK (sequence_no > 0),
  title text NOT NULL,
  summary text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (module_id, sequence_no)
);

CREATE TABLE IF NOT EXISTS academy.lesson_files (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  lesson_id uuid NOT NULL REFERENCES academy.lessons (id) ON DELETE CASCADE,
  kind text NOT NULL CHECK (kind IN ('video', 'ppt', 'file')),
  file_name text NOT NULL,
  content_type text NOT NULL,
  storage_uri text NOT NULL CHECK (storage_uri LIKE 'lake://%'),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS academy.assignments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  module_id uuid NOT NULL UNIQUE REFERENCES academy.modules (id) ON DELETE CASCADE,
  title text NOT NULL,
  instructions text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS academy.assignment_tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  assignment_id uuid NOT NULL REFERENCES academy.assignments (id) ON DELETE CASCADE,
  sequence_no integer NOT NULL CHECK (sequence_no > 0),
  prompt text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (assignment_id, sequence_no)
);

CREATE TABLE IF NOT EXISTS academy.quizzes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  module_id uuid NOT NULL UNIQUE REFERENCES academy.modules (id) ON DELETE CASCADE,
  title text NOT NULL,
  pass_mark integer NOT NULL DEFAULT 40 CHECK (pass_mark >= 0 AND pass_mark <= 100),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS academy.quiz_questions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  quiz_id uuid NOT NULL REFERENCES academy.quizzes (id) ON DELETE CASCADE,
  sequence_no integer NOT NULL CHECK (sequence_no > 0),
  prompt text NOT NULL,
  question_type text NOT NULL DEFAULT 'mcq' CHECK (question_type IN ('mcq', 'short')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (quiz_id, sequence_no)
);

CREATE TABLE IF NOT EXISTS academy.quiz_choices (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id uuid NOT NULL REFERENCES academy.quiz_questions (id) ON DELETE CASCADE,
  label text NOT NULL,
  is_correct boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS academy.labs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  module_id uuid NOT NULL UNIQUE REFERENCES academy.modules (id) ON DELETE CASCADE,
  title text NOT NULL,
  tool_key text NOT NULL CHECK (tool_key IN ('python', 'data', 'generative', 'office', 'computer', 'java')),
  instructions text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Junction of a student and one class-subject offering.
CREATE TABLE IF NOT EXISTS academy.enrollments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id uuid NOT NULL REFERENCES public.students (id) ON DELETE CASCADE,
  offering_id uuid NOT NULL REFERENCES academy.offerings (id) ON DELETE CASCADE,
  status text NOT NULL DEFAULT 'enrolled' CHECK (status IN ('enrolled', 'completed', 'withdrawn')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (student_id, offering_id)
);

CREATE TABLE IF NOT EXISTS academy.module_progress (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  enrollment_id uuid NOT NULL REFERENCES academy.enrollments (id) ON DELETE CASCADE,
  module_id uuid NOT NULL REFERENCES academy.modules (id) ON DELETE CASCADE,
  status text NOT NULL DEFAULT 'locked' CHECK (status IN ('locked', 'in_progress', 'completed')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (enrollment_id, module_id)
);

CREATE TABLE IF NOT EXISTS academy.assignment_submissions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  enrollment_id uuid NOT NULL REFERENCES academy.enrollments (id) ON DELETE CASCADE,
  assignment_id uuid NOT NULL REFERENCES academy.assignments (id) ON DELETE CASCADE,
  status text NOT NULL DEFAULT 'assigned' CHECK (status IN ('assigned', 'submitted')),
  submitted_at timestamptz,
  score integer CHECK (score IS NULL OR (score >= 0 AND score <= 100)),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (enrollment_id, assignment_id)
);

CREATE TABLE IF NOT EXISTS academy.quiz_attempts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  enrollment_id uuid NOT NULL REFERENCES academy.enrollments (id) ON DELETE CASCADE,
  quiz_id uuid NOT NULL REFERENCES academy.quizzes (id) ON DELETE CASCADE,
  score integer CHECK (score IS NULL OR (score >= 0 AND score <= 100)),
  submitted_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS academy.quiz_answers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  attempt_id uuid NOT NULL REFERENCES academy.quiz_attempts (id) ON DELETE CASCADE,
  question_id uuid NOT NULL REFERENCES academy.quiz_questions (id) ON DELETE CASCADE,
  choice_id uuid REFERENCES academy.quiz_choices (id) ON DELETE SET NULL,
  answer_text text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS academy.lab_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  enrollment_id uuid NOT NULL REFERENCES academy.enrollments (id) ON DELETE CASCADE,
  lab_id uuid NOT NULL REFERENCES academy.labs (id) ON DELETE CASCADE,
  status text NOT NULL DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'completed')),
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (enrollment_id, lab_id)
);

CREATE INDEX IF NOT EXISTS classes_board_idx ON academy.classes (board_id);
CREATE INDEX IF NOT EXISTS offerings_class_idx ON academy.offerings (class_id);
CREATE INDEX IF NOT EXISTS offerings_subject_idx ON academy.offerings (subject_id);
CREATE INDEX IF NOT EXISTS modules_offering_idx ON academy.modules (offering_id, sequence_no);
CREATE INDEX IF NOT EXISTS lessons_module_idx ON academy.lessons (module_id, sequence_no);
ALTER TABLE academy.lesson_files DROP CONSTRAINT IF EXISTS lesson_files_kind_check;
ALTER TABLE academy.lesson_files
  ADD CONSTRAINT lesson_files_kind_check
  CHECK (kind IN ('video', 'ppt', 'file'));

CREATE INDEX IF NOT EXISTS lesson_files_lesson_idx ON academy.lesson_files (lesson_id);
CREATE INDEX IF NOT EXISTS assignment_tasks_assignment_idx ON academy.assignment_tasks (assignment_id, sequence_no);
CREATE INDEX IF NOT EXISTS quiz_questions_quiz_idx ON academy.quiz_questions (quiz_id, sequence_no);
CREATE INDEX IF NOT EXISTS quiz_choices_question_idx ON academy.quiz_choices (question_id);
CREATE INDEX IF NOT EXISTS enrollments_student_idx ON academy.enrollments (student_id);
CREATE INDEX IF NOT EXISTS enrollments_offering_idx ON academy.enrollments (offering_id);
CREATE INDEX IF NOT EXISTS module_progress_enrollment_idx ON academy.module_progress (enrollment_id);
CREATE INDEX IF NOT EXISTS module_progress_module_idx ON academy.module_progress (module_id);
CREATE INDEX IF NOT EXISTS assignment_submissions_enrollment_idx ON academy.assignment_submissions (enrollment_id);
CREATE INDEX IF NOT EXISTS assignment_submissions_assignment_idx ON academy.assignment_submissions (assignment_id);
CREATE INDEX IF NOT EXISTS quiz_attempts_enrollment_idx ON academy.quiz_attempts (enrollment_id);
CREATE INDEX IF NOT EXISTS quiz_attempts_quiz_idx ON academy.quiz_attempts (quiz_id);
CREATE INDEX IF NOT EXISTS quiz_answers_attempt_idx ON academy.quiz_answers (attempt_id);
CREATE INDEX IF NOT EXISTS lab_sessions_enrollment_idx ON academy.lab_sessions (enrollment_id);
CREATE INDEX IF NOT EXISTS lab_sessions_lab_idx ON academy.lab_sessions (lab_id);

CREATE OR REPLACE FUNCTION academy.module_matches_enrollment()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM academy.enrollments AS enrollment
    JOIN academy.modules AS module ON module.offering_id = enrollment.offering_id
    WHERE enrollment.id = NEW.enrollment_id
      AND module.id = NEW.module_id
  ) THEN
    RAISE EXCEPTION 'module does not belong to the enrolled offering';
  END IF;
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION academy.touch_module_progress()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

-- Completing a module issues that module's assignment for the student.
CREATE OR REPLACE FUNCTION academy.issue_module_assignment()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.status = 'completed' AND (TG_OP = 'INSERT' OR OLD.status IS DISTINCT FROM 'completed') THEN
    INSERT INTO academy.assignment_submissions (enrollment_id, assignment_id, status)
    SELECT NEW.enrollment_id, assignment.id, 'assigned'
    FROM academy.assignments AS assignment
    WHERE assignment.module_id = NEW.module_id
    ON CONFLICT (enrollment_id, assignment_id) DO NOTHING;
  END IF;
  RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS module_progress_match ON academy.module_progress;
CREATE TRIGGER module_progress_match
  BEFORE INSERT OR UPDATE ON academy.module_progress
  FOR EACH ROW EXECUTE FUNCTION academy.module_matches_enrollment();

DROP TRIGGER IF EXISTS module_progress_touch ON academy.module_progress;
CREATE TRIGGER module_progress_touch
  BEFORE INSERT OR UPDATE ON academy.module_progress
  FOR EACH ROW EXECUTE FUNCTION academy.touch_module_progress();

DROP TRIGGER IF EXISTS module_progress_issue ON academy.module_progress;
CREATE TRIGGER module_progress_issue
  AFTER INSERT OR UPDATE OF status ON academy.module_progress
  FOR EACH ROW EXECUTE FUNCTION academy.issue_module_assignment();
