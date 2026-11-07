"""Class 7 portal content taken from the TechLearn Academy Figma frames."""

PROMPTS = [
    {
        "topic": "ai",
        "topic_label": "AI & Robotics",
        "title": "Meet your AI study buddy",
        "body": "Explain how an AI assistant learns, using a story about teaching a robot a new skill.",
        "level": "Beginner · 5 min",
        "saved": True,
    },
    {
        "topic": "python",
        "topic_label": "Python",
        "title": "Build a number guessing game",
        "body": "Guide me through creating a Python game. Give me hints before showing the answer.",
        "level": "Beginner · 15 min",
        "saved": True,
    },
    {
        "topic": "maths",
        "topic_label": "Maths",
        "title": "Make fractions make sense",
        "body": "Explain fractions using a pizza example, then quiz me with three practice questions.",
        "level": "Class 7 · 10 min",
        "saved": True,
    },
    {
        "topic": "science",
        "topic_label": "Science",
        "title": "Explore our solar system",
        "body": "Plan a mission to Mars. Help me understand the planets, gravity, and what astronauts need.",
        "level": "Class 7 · 10 min",
        "saved": True,
    },
    {
        "topic": "writing",
        "topic_label": "Creative writing",
        "title": "A robot with a secret",
        "body": "Help me outline a short story about a friendly robot who discovers a hidden talent.",
        "level": "All levels · 15 min",
        "saved": False,
    },
    {
        "topic": "study",
        "topic_label": "Study skills",
        "title": "Turn notes into a quick quiz",
        "body": "Create five practice questions from my notes. Ask one at a time and explain each answer.",
        "level": "All subjects · 10 min",
        "saved": False,
    },
]

PLUGINS = [
    ("Study Notes", "Turn lesson notes into summaries and revision cards.", "SN", 1),
    ("Python Playground", "Try small Python programs in a guided workspace.", "PY", 1),
    ("Quiz Builder", "Make a practice quiz from any topic you are studying.", "QZ", 0),
    ("Mind Map", "Connect ideas and plan your next project visually.", "MM", 0),
    ("Reading Buddy", "Break complex passages into clear, simple explanations.", "RB", 0),
    ("Maths Helper", "Work through problems one step at a time with hints.", "MH", 0),
]

MODULES = [
    {"number": "01", "title": "Digital foundations", "meta": "4 lessons · 1 quiz", "status": "Completed", "percent": "100%", "action": ""},
    {"number": "02", "title": "Meet artificial intelligence", "meta": "5 lessons · 1 quiz", "status": "Completed", "percent": "100%", "action": ""},
    {"number": "03", "title": "Robots around us", "meta": "4 lessons · 1 project", "status": "Completed", "percent": "100%", "action": ""},
    {"number": "04", "title": "Thinking like a programmer", "meta": "5 lessons · 1 quiz", "status": "Completed", "percent": "100%", "action": ""},
    {"number": "05", "title": "Python basics", "meta": "6 lessons · 1 project", "status": "In progress", "percent": "", "action": "Resume"},
    {"number": "06", "title": "Creative problem solving", "meta": "4 lessons · 1 activity", "status": "Ready to start", "percent": "", "action": "Start"},
    {"number": "07", "title": "Build your first chatbot", "meta": "5 lessons · 1 project", "status": "Unlock after Module 05", "percent": "", "action": ""},
    {"number": "08", "title": "Your capstone adventure", "meta": "3 lessons · 1 final project", "status": "Unlock after Module 07", "percent": "", "action": ""},
]

ACTIVITY = [
    ("Thu", 45),
    ("Fri", 60),
    ("Sat", 30),
    ("Sun", 75),
    ("Mon", 90),
    ("Tue", 50),
    ("Wed", 40),
]

SKILLS = [
    ("Digital foundations", 100),
    ("AI & robotics", 100),
    ("Computational thinking", 100),
    ("Python basics", 33),
]

ASSIGNMENTS = [
    ("Digital safety quiz", "26 Oct 2026", "92 / 100", "Graded"),
    ("Robot discovery project", "29 Oct 2026", "86 / 100", "Graded"),
    ("Logic challenge", "02 Nov 2026", "86 / 100", "Graded"),
]

LAB_BOARDS = ["CBSE", "ICSE"]
LAB_CLASSES = ["9", "10"]
LAB_TOOLS = [
    {
        "icon": "code",
        "title": "AI & Python",
        "body": "Explore Python and AI concepts.",
        "href": "/static/pages/python-lab.html",
        "prompt": "Help me explore Python and AI concepts for class.",
    },
    {
        "icon": "chart",
        "title": "Data & Statistics",
        "body": "Explore data, charts, and statistics.",
        "href": "/static/pages/data-lab.html",
        "prompt": "Help me explore data, charts, and statistics.",
    },
    {
        "icon": "spark",
        "title": "Generative AI",
        "body": "Create and explore with AI.",
        "prompt": "Help me create and explore with generative AI.",
    },
    {
        "icon": "grid",
        "title": "IT Office Lab",
        "body": "Practise everyday office skills.",
        "href": "/static/pages/office-lab.html",
        "same_tab": True,
        "prompt": "Help me practise everyday office skills.",
    },
    {
        "icon": "screen",
        "title": "Computer Applications",
        "body": "Build essential computer skills.",
        "prompt": "Help me build essential computer skills.",
    },
    {
        "icon": "java",
        "title": "Java",
        "body": "Write and run Java programs.",
        "href": "/lab/java",
        "prompt": "Help me write and run Java programs for class.",
    },
]
