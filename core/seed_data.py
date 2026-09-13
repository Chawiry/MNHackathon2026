"""Deterministic demo organization for the skills platform.

The whole dataset is reproducible: every employee, proficiency, requirement,
skill-graph edge, criticality assessment, and projection is defined here and
loaded by ``python manage.py seed_demo``.

Design targets (phases planned from this baseline):

- 5 departments, 9 teams, ~50 employees (within the spec's 40–60 range)
- 20 skills, ~33 SkillRelationship edges (the skills graph) so the graph-driven
  rules (Rule 1, successor-via-related-skill) have data to work with
- deliberate concentration risk: skills held by 1–2 people at proficiency >= 4
- one team of <= 4 people (drives the anonymization rule)
- critical TeamSkillRequirements + people_needed (drives bottlenecks)
- expected leave dates on key holders (drives stay + depletion analytics)
- SkillFutureDemand incl. an emerging "Generative AI / LLM" skill
- approved CertificateAwards that match existing proficiencies
"""

from datetime import date

from accounts.models import Tier, User
from profiles.models import (
    DevelopmentActivity,
    ExperienceEntry,
    PerformanceReview,
)
from projects.models import Project
from skills.models import (
    Certificate,
    CertificateAward,
    Skill,
    SkillFutureDemand,
    SkillProficiency,
    SkillRelationship,
)
from teams.models import Department, Team, TeamMembership, TeamSkillRequirement


DEFAULT_PASSWORD = "Testpass123!"


def d(year, month, day=1):
    return date(year, month, day)


DEPARTMENTS = [
    ("Engineering", "Software platforms, data, and AI products"),
    ("Technology Operations", "Cloud platforms, reliability, and security"),
    ("Product & Design", "Product strategy, UX, and delivery practices"),
    ("Sales & Marketing", "Demand generation, enablement, and growth"),
    ("People & Culture", "Learning, development, and talent"),
]

PROJECTS = [
    ("Core Platform Modernization", "active", d(2025, 3), d(2027, 6),
     "Re-architect the core platform on modern infrastructure."),
    ("Analytics Data Hub", "active", d(2025, 7), d(2027, 3),
     "Central data warehouse and reporting layer."),
    ("Cloud Migration Wave 2", "active", d(2026, 1), d(2027, 12),
     "Move remaining workloads to AWS."),
    ("Product Portfolio 2026", "active", d(2026, 2), d(2026, 12),
     "This year's product roadmap across the portfolio."),
    ("Demand Generation Wave", "active", d(2026, 3), d(2026, 11),
     "Funnel growth and campaign wave."),
    ("Sales Enablement Program", "active", d(2026, 4), d(2027, 4),
     "Standardize onboarding and enablement for sales."),
    ("GenAI Assistant Pilot", "planned", d(2026, 10), d(2027, 9),
     "Pilot a generative-AI assistant for internal workflows."),
    ("Workforce Upskilling Program", "planned", d(2026, 9), d(2028, 6),
     "Future-skills training aligned to the workforce plan."),
]

# (team name, department, project it spawns under, description)
TEAMS = [
    ("Platform Engineering", "Engineering", "Core Platform Modernization",
     "Backend services, APIs, and shared platform tooling."),
    ("Data & AI Engineering", "Engineering", "Analytics Data Hub",
     "Data pipelines, analytics, and ML/AI products."),
    ("Cloud Platform", "Technology Operations", "Cloud Migration Wave 2",
     "AWS platform, containers, and cloud landing zones."),
    ("Delivery & SRE", "Technology Operations", "Cloud Migration Wave 2",
     "Reliability, delivery, and security operations."),
    ("Product", "Product & Design", "Product Portfolio 2026",
     "Product management and discovery."),
    ("Design", "Product & Design", "Product Portfolio 2026",
     "UX/UI design and research."),
    ("Growth Marketing", "Sales & Marketing", "Demand Generation Wave",
     "Campaigns, content, and marketing analytics."),
    ("Sales Enablement", "Sales & Marketing", "Sales Enablement Program",
     "Sales onboarding, training, and enablement assets."),
    ("Learning & Development", "People & Culture", "Workforce Upskilling Program",
     "Learning programs, competency development, and upskilling."),
]

# (from_skill, to_skill, kind, weight)
SKILL_RELATIONSHIPS = [
    # Prerequisites
    ("Python", "Machine Learning", "prerequisite", 4),
    ("Python", "Data Analysis", "prerequisite", 3),
    ("SQL & Databases", "Data Analysis", "prerequisite", 3),
    ("Python", "Data Engineering", "prerequisite", 3),
    ("SQL & Databases", "Data Engineering", "prerequisite", 3),
    ("Machine Learning", "Generative AI / LLM", "prerequisite", 3),
    ("Prompt Engineering", "Generative AI / LLM", "prerequisite", 3),
    ("JavaScript / TypeScript", "UI/UX Design", "prerequisite", 2),
    ("Docker & Containers", "CI/CD", "prerequisite", 3),
    ("Agile Methodologies", "Product Management", "prerequisite", 3),
    # Transfers
    ("Data Analysis", "Machine Learning", "transfers", 4),
    ("Data Engineering", "Machine Learning", "transfers", 3),
    ("Data Analysis", "Data Engineering", "transfers", 3),
    ("Prompt Engineering", "Data Analysis", "transfers", 3),
    ("JavaScript / TypeScript", "Testing & QA", "transfers", 3),
    ("Testing & QA", "CI/CD", "transfers", 3),
    ("AWS", "Cyber Security", "transfers", 3),
    ("Data Analysis", "Prompt Engineering", "transfers", 3),
    ("Product Management", "Team Leadership", "transfers", 3),
    ("Team Leadership", "Presentation Skills", "transfers", 4),
    # Related
    ("Python", "Testing & QA", "related", 3),
    ("AWS", "Docker & Containers", "related", 3),
    ("CI/CD", "Docker & Containers", "related", 2),
    ("Docker & Containers", "AWS", "related", 3),
    ("UI/UX Design", "Product Management", "related", 3),
    ("Product Management", "Presentation Skills", "related", 3),
    ("Technical Writing", "Presentation Skills", "related", 3),
    ("Presentation Skills", "Change Management", "related", 4),
    ("Data Analysis", "Technical Writing", "related", 2),
    ("Change Management", "Team Leadership", "related", 3),
    ("Team Leadership", "Technical Writing", "related", 2),
    ("Data Analysis", "Generative AI / LLM", "related", 3),
    ("Machine Learning", "Data Engineering", "related", 3),
]

# --- Demo accounts (known passwords, tier-diverse) ---------------------------
DEMO_USERS = [
    {
        "username": "alex.rivera",
        "first": "Alexandra",
        "last": "Rivera",
        "job_title": "Chief Operating Officer",
        "tier": Tier.LEADERSHIP,
        "hire": d(2018, 1),
        "leave": None,
        "staff": True,
    },
    {
        "username": "sam.lee",
        "first": "Sam",
        "last": "Lee",
        "job_title": "Engineering Manager",
        "tier": Tier.TEAM_MANAGER,
        "team": "Platform Engineering",
        "role": "manager",
        "hire": d(2019, 6),
        "leave": None,
        "staff": True,
        "skills": {"Python": 5, "SQL & Databases": 4, "Docker & Containers": 4, "CI/CD": 4, "Team Leadership": 4},
    },
    {
        "username": "jordan.mendez",
        "first": "Jordan",
        "last": "Mendez",
        "job_title": "Software Engineer",
        "tier": Tier.EMPLOYEE,
        "team": "Platform Engineering",
        "role": "member",
        "hire": d(2022, 3),
        "leave": None,
        "staff": True,
        "skills": {"Python": 3, "SQL & Databases": 2, "Testing & QA": 3},
    },
]

# username, team, role (tier derived from role), job_title, hire, leave, skills
PEOPLE = [
    # --- Engineering / Platform Engineering (manager is demo sam.lee) ------
    {"username": "nina.kowalski", "first": "Nina", "last": "Kowalski",
     "job_title": "Senior Software Engineer", "team": "Platform Engineering", "role": "member",
     "hire": d(2018, 2), "leave": None,
     "skills": {"Python": 5, "SQL & Databases": 4, "Docker & Containers": 4, "CI/CD": 4, "Testing & QA": 3}},
    {"username": "lena.fischer", "first": "Lena", "last": "Fischer",
     "job_title": "Software Engineer", "team": "Platform Engineering", "role": "member",
     "hire": d(2021, 4), "leave": None,
     "skills": {"JavaScript / TypeScript": 4, "Python": 3, "Testing & QA": 3, "SQL & Databases": 2}},
    {"username": "marcus.webb", "first": "Marcus", "last": "Webb",
     "job_title": "Staff Engineer", "team": "Platform Engineering", "role": "member",
     "hire": d(2016, 9), "leave": None,
     "skills": {"Python": 5, "SQL & Databases": 5, "AWS": 4, "Docker & Containers": 4, "Testing & QA": 4}},
    {"username": "priya.nair", "first": "Priya", "last": "Nair",
     "job_title": "Software Engineer", "team": "Platform Engineering", "role": "member",
     "hire": d(2020, 8), "leave": d(2026, 12, 15),
     "skills": {"Python": 4, "AWS": 5, "CI/CD": 4, "Docker & Containers": 4}},
    {"username": "omar.farouk", "first": "Omar", "last": "Farouk",
     "job_title": "Software Engineer", "team": "Platform Engineering", "role": "member",
     "hire": d(2022, 1), "leave": None,
     "skills": {"Python": 3, "Testing & QA": 4, "CI/CD": 3, "JavaScript / TypeScript": 2}},
    {"username": "emily.park", "first": "Emily", "last": "Park",
     "job_title": "QA Lead", "team": "Platform Engineering", "role": "member",
     "hire": d(2019, 11), "leave": None,
     "skills": {"Testing & QA": 5, "Python": 3, "SQL & Databases": 2, "Agile Methodologies": 4,
                "Technical Writing": 3}},
    {"username": "diego.rodriguez", "first": "Diego", "last": "Rodriguez",
     "job_title": "Software Engineer", "team": "Platform Engineering", "role": "member",
     "hire": d(2023, 3), "leave": None,
     "skills": {"Python": 4, "Docker & Containers": 3, "CI/CD": 3, "AWS": 2}},
    # --- Engineering / Data & AI Engineering --------------------------------
    {"username": "ravi.patel", "first": "Ravi", "last": "Patel",
     "job_title": "Data Science Manager", "team": "Data & AI Engineering", "role": "manager",
     "hire": d(2017, 5), "leave": d(2027, 3, 1),
     "skills": {"Machine Learning": 5, "Python": 5, "SQL & Databases": 4, "Data Engineering": 4,
                "Team Leadership": 3, "Generative AI / LLM": 2}},
    {"username": "sana.iqbal", "first": "Sana", "last": "Iqbal",
     "job_title": "Machine Learning Engineer", "team": "Data & AI Engineering", "role": "member",
     "hire": d(2020, 5), "leave": None,
     "skills": {"Machine Learning": 5, "Python": 5, "Data Analysis": 4, "Prompt Engineering": 4,
                "Generative AI / LLM": 4, "Data Engineering": 3}},
    {"username": "chen.yu", "first": "Chen", "last": "Yu",
     "job_title": "Machine Learning Engineer", "team": "Data & AI Engineering", "role": "member",
     "hire": d(2021, 9), "leave": None,
     "skills": {"Machine Learning": 4, "Data Engineering": 4, "Python": 4, "Data Analysis": 3,
                "Generative AI / LLM": 3}},
    {"username": "fatima.al-rashid", "first": "Fatima", "last": "Al-Rashid",
     "job_title": "Data Engineer", "team": "Data & AI Engineering", "role": "member",
     "hire": d(2021, 2), "leave": None,
     "skills": {"Data Engineering": 4, "SQL & Databases": 4, "Python": 3, "Machine Learning": 3,
                "Generative AI / LLM": 2}},
    {"username": "grace.osei", "first": "Grace", "last": "Osei",
     "job_title": "Data Analyst", "team": "Data & AI Engineering", "role": "member",
     "hire": d(2022, 6), "leave": None,
     "skills": {"Data Analysis": 5, "SQL & Databases": 4, "Python": 2, "Machine Learning": 2}},
    {"username": "viktor.petrov", "first": "Viktor", "last": "Petrov",
     "job_title": "Data Engineer", "team": "Data & AI Engineering", "role": "member",
     "hire": d(2020, 3), "leave": None,
     "skills": {"Data Engineering": 3, "Python": 4, "SQL & Databases": 3, "Generative AI / LLM": 2,
                "Prompt Engineering": 2}},
    {"username": "liam.byrne", "first": "Liam", "last": "Byrne",
     "job_title": "Data Scientist", "team": "Data & AI Engineering", "role": "member",
     "hire": d(2021, 11), "leave": None,
     "skills": {"Machine Learning": 3, "Data Analysis": 4, "Python": 3, "Prompt Engineering": 2,
                "SQL & Databases": 2}},
    {"username": "zoe.martin", "first": "Zoe", "last": "Martin",
     "job_title": "Machine Learning Engineer", "team": "Data & AI Engineering", "role": "member",
     "hire": d(2023, 7), "leave": None,
     "skills": {"Machine Learning": 3, "Python": 3, "Data Analysis": 2, "Generative AI / LLM": 1}},
    # --- Technology Operations / Cloud Platform -----------------------------
    {"username": "daniel.okafor", "first": "Daniel", "last": "Okafor",
     "job_title": "Cloud Architect", "team": "Cloud Platform", "role": "manager",
     "hire": d(2017, 8), "leave": None,
     "skills": {"AWS": 5, "Docker & Containers": 5, "CI/CD": 4, "Python": 3}},
    {"username": "sara.dupont", "first": "Sara", "last": "Dupont",
     "job_title": "Cloud Engineer", "team": "Cloud Platform", "role": "member",
     "hire": d(2020, 10), "leave": d(2027, 5, 1),
     "skills": {"AWS": 4, "Docker & Containers": 4, "CI/CD": 4}},
    {"username": "ivan.melnikov", "first": "Ivan", "last": "Melnikov",
     "job_title": "Cloud Engineer", "team": "Cloud Platform", "role": "member",
     "hire": d(2021, 6), "leave": None,
     "skills": {"AWS": 5, "Cyber Security": 2, "Docker & Containers": 3, "Python": 3}},
    {"username": "chloe.nguyen", "first": "Chloe", "last": "Nguyen",
     "job_title": "Solution Architect", "team": "Cloud Platform", "role": "member",
     "hire": d(2019, 3), "leave": None,
     "skills": {"AWS": 5, "Data Analysis": 3, "Technical Writing": 3, "Presentation Skills": 4}},
    {"username": "riley.anderson", "first": "Riley", "last": "Anderson",
     "job_title": "Cloud Engineer", "team": "Cloud Platform", "role": "member",
     "hire": d(2022, 4), "leave": None,
     "skills": {"AWS": 4, "Docker & Containers": 4, "CI/CD": 3}},
    {"username": "hana.suzuki", "first": "Hana", "last": "Suzuki",
     "job_title": "Platform Engineer", "team": "Cloud Platform", "role": "member",
     "hire": d(2023, 5), "leave": None,
     "skills": {"AWS": 3, "Docker & Containers": 2, "CI/CD": 2}},
    # --- Technology Operations / Delivery & SRE -----------------------------
    {"username": "michael.torres", "first": "Michael", "last": "Torres",
     "job_title": "SRE Lead", "team": "Delivery & SRE", "role": "manager",
     "hire": d(2018, 11), "leave": None,
     "skills": {"CI/CD": 5, "Docker & Containers": 4, "AWS": 4, "Python": 3, "Team Leadership": 4}},
    {"username": "adeyemi.johnson", "first": "Adeyemi", "last": "Johnson",
     "job_title": "Security Engineer", "team": "Delivery & SRE", "role": "member",
     "hire": d(2021, 8), "leave": None,
     "skills": {"Cyber Security": 1, "AWS": 3, "Docker & Containers": 3, "Python": 3}},
    {"username": "lucia.bianchi", "first": "Lucia", "last": "Bianchi",
     "job_title": "Security Engineer", "team": "Delivery & SRE", "role": "member",
     "hire": d(2019, 7), "leave": d(2027, 7, 1),
     "skills": {"Cyber Security": 5, "AWS": 2, "Docker & Containers": 2, "Technical Writing": 3}},
    {"username": "felix.weber", "first": "Felix", "last": "Weber",
     "job_title": "Site Reliability Engineer", "team": "Delivery & SRE", "role": "member",
     "hire": d(2020, 12), "leave": None,
     "skills": {"CI/CD": 4, "Docker & Containers": 4, "Python": 4, "Testing & QA": 2}},
    {"username": "ines.costa", "first": "Ines", "last": "Costa",
     "job_title": "Release Manager", "team": "Delivery & SRE", "role": "member",
     "hire": d(2019, 1), "leave": None,
     "skills": {"CI/CD": 4, "Testing & QA": 3, "Agile Methodologies": 4, "Presentation Skills": 3}},
    # --- Product & Design / Product -----------------------------------------
    {"username": "mei.lin", "first": "Mei", "last": "Lin",
     "job_title": "Head of Product", "team": "Product", "role": "manager",
     "hire": d(2017, 2), "leave": None,
     "skills": {"Product Management": 5, "Agile Methodologies": 5, "Presentation Skills": 5,
                "Data Analysis": 4, "Team Leadership": 4}},
    {"username": "hannah.brooks", "first": "Hannah", "last": "Brooks",
     "job_title": "Product Manager", "team": "Product", "role": "member",
     "hire": d(2020, 6), "leave": None,
     "skills": {"Product Management": 4, "Agile Methodologies": 4, "Data Analysis": 3,
                "Presentation Skills": 3}},
    {"username": "elijah.carter", "first": "Elijah", "last": "Carter",
     "job_title": "Product Manager", "team": "Product", "role": "member",
     "hire": d(2021, 5), "leave": None,
     "skills": {"Product Management": 4, "Agile Methodologies": 4, "Technical Writing": 3,
                "Data Analysis": 3}},
    {"username": "ruby.walker", "first": "Ruby", "last": "Walker",
     "job_title": "Product Analyst", "team": "Product", "role": "member",
     "hire": d(2022, 8), "leave": None,
     "skills": {"Data Analysis": 4, "SQL & Databases": 3, "Product Management": 3, "Presentation Skills": 2}},
    {"username": "jack.stone", "first": "Jack", "last": "Stone",
     "job_title": "Product Manager", "team": "Product", "role": "member",
     "hire": d(2021, 3), "leave": None,
     "skills": {"Product Management": 3, "Agile Methodologies": 4, "UI/UX Design": 2,
                "Data Analysis": 2}},
    {"username": "arjun.mehta", "first": "Arjun", "last": "Mehta",
     "job_title": "Product Manager", "team": "Product", "role": "member",
     "hire": d(2023, 1), "leave": None,
     "skills": {"Product Management": 3, "Agile Methodologies": 3, "Change Management": 2,
                "Presentation Skills": 3}},
    # --- Product & Design / Design ------------------------------------------
    {"username": "aaron.smith", "first": "Aaron", "last": "Smith",
     "job_title": "Design Director", "team": "Design", "role": "manager",
     "hire": d(2016, 4), "leave": None,
     "skills": {"UI/UX Design": 5, "Product Management": 3, "Agile Methodologies": 4,
                "Presentation Skills": 4, "Team Leadership": 3}},
    {"username": "yuki.tanaka", "first": "Yuki", "last": "Tanaka",
     "job_title": "UX Designer", "team": "Design", "role": "member",
     "hire": d(2020, 9), "leave": None,
     "skills": {"UI/UX Design": 5, "Agile Methodologies": 2, "Presentation Skills": 3}},
    {"username": "rosa.delgado", "first": "Rosa", "last": "Delgado",
     "job_title": "UI Designer", "team": "Design", "role": "member",
     "hire": d(2021, 7), "leave": None,
     "skills": {"UI/UX Design": 4, "JavaScript / TypeScript": 3, "Product Management": 2,
                "Technical Writing": 2}},
    {"username": "amir.hosseini", "first": "Amir", "last": "Hosseini",
     "job_title": "Product Designer", "team": "Design", "role": "member",
     "hire": d(2022, 2), "leave": None,
     "skills": {"UI/UX Design": 4, "Product Management": 3, "Agile Methodologies": 3,
                "Presentation Skills": 2}},
    {"username": "kate.morgan", "first": "Kate", "last": "Morgan",
     "job_title": "UX Researcher", "team": "Design", "role": "member",
     "hire": d(2019, 10), "leave": None,
     "skills": {"Data Analysis": 4, "UI/UX Design": 3, "Technical Writing": 4}},
    # --- Sales & Marketing / Growth Marketing -------------------------------
    {"username": "olivia.brown", "first": "Olivia", "last": "Brown",
     "job_title": "Marketing Director", "team": "Growth Marketing", "role": "manager",
     "hire": d(2017, 10), "leave": None,
     "skills": {"Product Management": 4, "Data Analysis": 4, "Presentation Skills": 5,
                "Change Management": 3, "Team Leadership": 4}},
    {"username": "david.kim", "first": "David", "last": "Kim",
     "job_title": "Growth Marketing Lead", "team": "Growth Marketing", "role": "member",
     "hire": d(2020, 1), "leave": d(2028, 3, 1),
     "skills": {"Data Analysis": 4, "SQL & Databases": 3, "Presentation Skills": 4, "Technical Writing": 3}},
    {"username": "emma.walsh", "first": "Emma", "last": "Walsh",
     "job_title": "Content Strategist", "team": "Growth Marketing", "role": "member",
     "hire": d(2021, 10), "leave": None,
     "skills": {"Technical Writing": 5, "Presentation Skills": 4, "Data Analysis": 3,
                "Product Management": 2}},
    {"username": "lucas.silva", "first": "Lucas", "last": "Silva",
     "job_title": "Marketing Analyst", "team": "Growth Marketing", "role": "member",
     "hire": d(2023, 4), "leave": None,
     "skills": {"Data Analysis": 3, "Presentation Skills": 3, "JavaScript / TypeScript": 2}},
    {"username": "pablo.gomez", "first": "Pablo", "last": "Gomez",
     "job_title": "CRM Analyst", "team": "Growth Marketing", "role": "member",
     "hire": d(2022, 9), "leave": None,
     "skills": {"SQL & Databases": 3, "Data Analysis": 3, "Agile Methodologies": 2}},
    # --- Sales & Marketing / Sales Enablement (small team) ------------------
    {"username": "ethan.holt", "first": "Ethan", "last": "Holt",
     "job_title": "Sales Enablement Lead", "team": "Sales Enablement", "role": "manager",
     "hire": d(2018, 6), "leave": None,
     "skills": {"Presentation Skills": 5, "Change Management": 4, "Product Management": 3,
                "Team Leadership": 3, "Technical Writing": 3}},
    {"username": "grace.wu", "first": "Grace", "last": "Wu",
     "job_title": "Enablement Specialist", "team": "Sales Enablement", "role": "member",
     "hire": d(2021, 12), "leave": None,
     "skills": {"Presentation Skills": 4, "Change Management": 3, "Technical Writing": 3,
                "Product Management": 2}},
    {"username": "noah.rivera", "first": "Noah", "last": "Rivera",
     "job_title": "Enablement Specialist", "team": "Sales Enablement", "role": "member",
     "hire": d(2022, 11), "leave": None,
     "skills": {"Presentation Skills": 4, "Data Analysis": 2, "Product Management": 3,
                "Change Management": 2}},
    {"username": "maya.iyer", "first": "Maya", "last": "Iyer",
     "job_title": "Sales Trainer", "team": "Sales Enablement", "role": "member",
     "hire": d(2023, 2), "leave": None,
     "skills": {"Presentation Skills": 4, "Change Management": 3, "Team Leadership": 3,
                "Data Analysis": 2}},
    # --- People & Culture / Learning & Development --------------------------
    {"username": "julia.roth", "first": "Julia", "last": "Roth",
     "job_title": "L&D Manager", "team": "Learning & Development", "role": "manager",
     "hire": d(2018, 3), "leave": d(2027, 9, 1),
     "skills": {"Change Management": 5, "Team Leadership": 4, "Presentation Skills": 4,
                "Technical Writing": 3}},
    {"username": "peter.hall", "first": "Peter", "last": "Hall",
     "job_title": "Learning Designer", "team": "Learning & Development", "role": "member",
     "hire": d(2020, 4), "leave": None,
     "skills": {"Change Management": 4, "Presentation Skills": 3, "Team Leadership": 2,
                "Technical Writing": 4}},
    {"username": "anna.janssen", "first": "Anna", "last": "Janssen",
     "job_title": "Talent Development Partner", "team": "Learning & Development", "role": "member",
     "hire": d(2021, 1), "leave": None,
     "skills": {"Team Leadership": 4, "Presentation Skills": 3, "Change Management": 3,
                "Technical Writing": 3}},
    {"username": "sam.carter", "first": "Sam", "last": "Carter",
     "job_title": "L&D Coordinator", "team": "Learning & Development", "role": "member",
     "hire": d(2023, 8), "leave": None,
     "skills": {"Change Management": 2, "Presentation Skills": 2, "Technical Writing": 2,
                "Team Leadership": 2}},
]

# (username, second_team) — specialists shared across teams (drives availability)
EXTRA_MEMBERSHIPS = [
    ("priya.nair", "Cloud Platform"),
    ("felix.weber", "Platform Engineering"),
    ("emma.walsh", "Sales Enablement"),
]

# (team, skill, required_level, importance, people_needed)
REQUIREMENTS = [
    # Platform Engineering
    ("Platform Engineering", "Python", 3, "critical", 5),
    ("Platform Engineering", "JavaScript / TypeScript", 3, "important", 4),
    ("Platform Engineering", "SQL & Databases", 3, "important", 3),
    ("Platform Engineering", "Docker & Containers", 3, "important", 3),
    ("Platform Engineering", "CI/CD", 3, "important", 3),
    ("Platform Engineering", "Testing & QA", 2, "important", 3),
    ("Platform Engineering", "AWS", 3, "important", 2),
    # Data & AI Engineering
    ("Data & AI Engineering", "Machine Learning", 4, "critical", 3),
    ("Data & AI Engineering", "Data Engineering", 4, "critical", 3),
    ("Data & AI Engineering", "Generative AI / LLM", 3, "critical", 4),
    ("Data & AI Engineering", "Prompt Engineering", 3, "important", 4),
    ("Data & AI Engineering", "Data Analysis", 3, "important", 4),
    ("Data & AI Engineering", "Python", 3, "important", 5),
    ("Data & AI Engineering", "SQL & Databases", 3, "important", 3),
    ("Data & AI Engineering", "JavaScript / TypeScript", 3, "important", 1),
    # Cloud Platform
    ("Cloud Platform", "AWS", 4, "critical", 4),
    ("Cloud Platform", "Docker & Containers", 3, "critical", 4),
    ("Cloud Platform", "CI/CD", 3, "critical", 4),
    ("Cloud Platform", "Cyber Security", 4, "critical", 2),
    ("Cloud Platform", "Python", 3, "important", 2),
    ("Cloud Platform", "Data Analysis", 3, "important", 2),
    # Delivery & SRE
    ("Delivery & SRE", "CI/CD", 3, "critical", 4),
    ("Delivery & SRE", "AWS", 3, "important", 3),
    ("Delivery & SRE", "Docker & Containers", 3, "important", 3),
    ("Delivery & SRE", "Cyber Security", 4, "critical", 2),
    ("Delivery & SRE", "Python", 2, "important", 3),
    ("Delivery & SRE", "Testing & QA", 2, "important", 2),
    # Product
    ("Product", "Product Management", 4, "critical", 4),
    ("Product", "Agile Methodologies", 4, "critical", 5),
    ("Product", "UI/UX Design", 3, "important", 2),
    ("Product", "Data Analysis", 3, "important", 3),
    ("Product", "Presentation Skills", 3, "critical", 3),
    # Design
    ("Design", "UI/UX Design", 4, "critical", 4),
    ("Design", "Product Management", 3, "important", 2),
    ("Design", "Agile Methodologies", 3, "important", 3),
    ("Design", "Presentation Skills", 3, "important", 2),
    # Growth Marketing
    ("Growth Marketing", "Data Analysis", 4, "critical", 4),
    ("Growth Marketing", "Presentation Skills", 4, "critical", 4),
    ("Growth Marketing", "Technical Writing", 3, "important", 2),
    ("Growth Marketing", "Product Management", 3, "important", 2),
    ("Growth Marketing", "Change Management", 3, "important", 2),
    # Sales Enablement (small team)
    ("Sales Enablement", "Presentation Skills", 4, "critical", 3),
    ("Sales Enablement", "Change Management", 4, "critical", 3),
    ("Sales Enablement", "Technical Writing", 3, "important", 2),
    ("Sales Enablement", "Data Analysis", 3, "important", 2),
    ("Sales Enablement", "Product Management", 3, "important", 2),
    ("Sales Enablement", "Team Leadership", 3, "important", 1),
    # Learning & Development
    ("Learning & Development", "Change Management", 4, "critical", 3),
    ("Learning & Development", "Team Leadership", 4, "critical", 3),
    ("Learning & Development", "Presentation Skills", 3, "important", 3),
    ("Learning & Development", "Technical Writing", 3, "important", 3),
]

# (team, skill, required_level, importance) — next-position skills
PROMOTION_REQUIREMENTS = [
    ("Platform Engineering", "Team Leadership", 3, "important"),
    ("Data & AI Engineering", "Team Leadership", 3, "important"),
    ("Product", "Team Leadership", 3, "important"),
    ("Design", "Data Analysis", 3, "important"),
    ("Growth Marketing", "Team Leadership", 3, "important"),
]

# (username, type, skill, status, completed_at, note)
DEVELOPMENT_ACTIVITIES = [
    ("jordan.mendez", "course", "Python", "completed", d(2026, 8),
     "Completed an advanced Python course."),
    ("sam.lee", "mentoring", "Team Leadership", "in_progress", None,
     "Mentoring a newly appointed engineering manager."),
    ("omar.farouk", "course", "CI/CD", "completed", d(2026, 9),
     "Finished the release-engineering certification path."),
    ("nina.kowalski", "job_rotation", "CI/CD", "in_progress", None,
     "Rotation into the platform release team."),
    ("zoe.martin", "course", "Machine Learning", "planned", d(2026, 12),
     "Enrolled in an ML specialization to deepen model work."),
    ("grace.wu", "course", "Presentation Skills", "completed", d(2026, 7),
     "Presentation coaching workshop."),
]

# (username, role, organization, start_date, end_date, summary)
EXPERIENCES = [
    ("jordan.mendez", "Junior Developer", "NexaSoft", d(2019, 7), d(2022, 2),
     "Full-stack support and API maintenance."),
    ("jordan.mendez", "Software Engineer", "Team Skills Co", d(2022, 3), None,
     "Backend services and platform tooling."),
    ("sana.iqbal", "Data Scientist", "BrightLabs", d(2017, 9), d(2020, 4),
     "Predictive models for retail forecasting."),
    ("alex.rivera", "Operations Director", "Meridian Group", d(2010, 5), d(2017, 12),
     "Led a 60-person operations organization."),
    ("ravi.patel", "Analytics Lead", "Northwind Data", d(2012, 6), d(2017, 4),
     "Built the analytics practice and hiring pipeline."),
]

# (username, period, rating, reviewed_at, goals, achievements, feedback)
REVIEWS = [
    ("jordan.mendez", "2026 Q2", 3, d(2026, 6),
     "Strengthen Python and SQL depth.",
     "Delivered the billing refactor on schedule; took ownership of the API layer.",
     "Reliable and growing — next step is more design involvement."),
    ("sana.iqbal", "2026 Q1", 5, d(2026, 3),
     "Keep championing the GenAI pilot",
     "Shipped the assistant pilot backend and led the LLM evaluation.",
     "Outstanding — acts as a de-facto tech lead on AI work."),
    ("diego.rodriguez", "2025 annual", 3, d(2025, 12),
     "Grow AWS and CI/CD experience.",
     "Consistent delivery on platform tickets.",
     "Solid junior-to-mid trajectory; needs more cloud exposure."),
]

# (skill, direction, future_importance, confidence, horizon, source, note)
FUTURE_DEMAND = [
    ("Generative AI / LLM", "emerging", 5, "high", "12–24 months",
     "AI-assisted synthesis", "Board-level bet; few internal holders."),
    ("Cyber Security", "growing", 5, "high", "12–24 months",
     "Market data", "Regulatory scrutiny is rising."),
    ("Machine Learning", "growing", 4, "medium", "12–24 months",
     "AI-assisted synthesis", "Core capability for the data hub."),
    ("Data Engineering", "growing", 4, "high", "12–24 months",
     "Market data", "Warehouse consolidation drives demand."),
    ("Prompt Engineering", "emerging", 3, "medium", "12–24 months",
     "AI-assisted synthesis", "Folds into the GenAI pilot."),
    ("Data Analysis", "stable", 4, "high", "12–24 months",
     "Curated report", "Baseline analytical literacy."),
    ("Change Management", "growing", 4, "medium", "12–24 months",
     "Curated report", "Large transformation portfolio ahead."),
    ("Product Management", "stable", 4, "medium", "12–24 months",
     "Curated report", "Continued portfolio growth."),
    ("JavaScript / TypeScript", "stable", 3, "medium", "12–24 months",
     "Curated report", "Web delivery baseline."),
    ("Presentation Skills", "growing", 3, "medium", "12–24 months",
     "Curated report", "Enablement and stakeholder comms."),
]

# (name, issuer)
CERTIFICATES = [
    ("AWS Solutions Architect", "Amazon Web Services"),
    ("TensorFlow Developer Certificate", "Google"),
    ("CompTIA Security+", "CompTIA"),
    ("Certified Scrum Product Owner", "Scrum Alliance"),
    ("AWS Machine Learning Specialty", "Amazon Web Services"),
    ("Prompt Engineering Certification", "OpenAI"),
]

# (username, certificate, skill, level, obtained_on)
CERTIFICATE_AWARDS = [
    ("daniel.okafor", "AWS Solutions Architect", "AWS", 4, d(2024, 4)),
    ("ravi.patel", "TensorFlow Developer Certificate", "Machine Learning", 4, d(2025, 6)),
    ("lucia.bianchi", "CompTIA Security+", "Cyber Security", 4, d(2023, 9)),
    ("hannah.brooks", "Certified Scrum Product Owner", "Product Management", 3, d(2024, 2)),
    ("chen.yu", "AWS Machine Learning Specialty", "Machine Learning", 3, d(2024, 11)),
    ("sana.iqbal", "Prompt Engineering Certification", "Generative AI / LLM", 3, d(2026, 3)),
]

VALIDATION_SOURCES = ["manager evaluation", "self assessment", "certification", "project evidence"]
LAST_USED_BY_LEVEL = {5: d(2026, 8), 4: d(2026, 8), 3: d(2026, 6), 2: d(2026, 3), 1: d(2026, 1)}

# Business-impact factors: skill -> (business_impact 1-5, strategic_relevance 1-5,
# time_to_replace_months). Only skills that genuinely matter to operations get a
# high criticality score; routine skills stay below the critical threshold.
CRITICALITY_FACTORS = {
    "Cyber Security": (5, 5, 18),
    "Generative AI / LLM": (4, 5, 6),
    "Machine Learning": (4, 4, 12),
    "Data Engineering": (4, 4, 12),
    "Prompt Engineering": (4, 4, 3),
    "JavaScript / TypeScript": (3, 3, 9),
    "Change Management": (4, 4, 12),
    "Product Management": (4, 4, 9),
    "Team Leadership": (4, 3, 12),
    "AWS": (4, 4, 6),
}


def _skill(name):
    return Skill.objects.get(name=name)


def run(verbose=1):
    """Create the full deterministic org. Assumes a clean (flushed) database."""

    def _out(msg):
        if verbose:
            print(msg)

    # Departments
    departments = {
        name: Department.objects.create(name=name, description=desc)
        for name, desc in DEPARTMENTS
    }

    # Projects
    projects = {}
    for name, status, start, end, desc in PROJECTS:
        projects[name] = Project.objects.create(
            name=name, description=desc, status=status, start_date=start, end_date=end
        )

    # Teams
    teams = {}
    for name, dept, project, desc in TEAMS:
        teams[name] = Team.objects.create(
            name=name, description=desc, department=departments[dept], project=projects[project]
        )

    # Users (demo + generated people)
    users = {}
    for entry in DEMO_USERS:
        u = User.objects.create_user(
            username=entry["username"],
            email=f'{entry["username"]}@example.com',
            password=DEFAULT_PASSWORD,
            tier=entry["tier"],
            job_title=entry["job_title"],
            hire_date=entry["hire"],
            expected_leave_date=entry["leave"],
            first_name=entry["first"],
            last_name=entry["last"],
            is_staff=entry.get("staff", False),
        )
        users[u.username] = u

    for entry in PEOPLE:
        tier = Tier.TEAM_MANAGER if entry["role"] == "manager" else Tier.EMPLOYEE
        u = User.objects.create_user(
            username=entry["username"],
            email=f'{entry["username"]}@example.com',
            password=DEFAULT_PASSWORD,
            tier=tier,
            job_title=entry["job_title"],
            hire_date=entry["hire"],
            expected_leave_date=entry["leave"],
            first_name=entry["first"],
            last_name=entry["last"],
        )
        users[u.username] = u

    # Team membership map: username -> (team_name, role)
    team_role = {u["username"]: (u["team"], u["role"]) for u in DEMO_USERS if u.get("team")}
    for p in PEOPLE:
        team_role[p["username"]] = (p["team"], p["role"])

    managers = {}
    for username, (team_name, role) in team_role.items():
        TeamMembership.objects.create(
            team=teams[team_name],
            user=users[username],
            role=TeamMembership.Role.MANAGER if role == "manager" else TeamMembership.Role.MEMBER,
        )
        if role == "manager":
            managers[team_name] = users[username]

    for username, team_name in EXTRA_MEMBERSHIPS:
        TeamMembership.objects.create(
            team=teams[team_name], user=users[username], role=TeamMembership.Role.MEMBER
        )

    # Skill graph
    for from_name, to_name, kind, weight in SKILL_RELATIONSHIPS:
        SkillRelationship.objects.create(
            from_skill=_skill(from_name),
            to_skill=_skill(to_name),
            kind=kind,
            weight=weight,
        )

    # Proficiencies (approved, so analytics include them)
    leader = users.get("alex.rivera")
    source_index = 0
    proficiency_count = 0
    for entry in DEMO_USERS + PEOPLE:
        user = users[entry["username"]]
        team_name = team_role.get(entry["username"], (None, "member"))[0]
        approver = managers.get(team_name, leader)
        for skill_name, level in entry.get("skills", {}).items():
            SkillProficiency.objects.create(
                user=user,
                skill=_skill(skill_name),
                level=level,
                status=SkillProficiency.Status.APPROVED,
                evidence="",
                last_used=LAST_USED_BY_LEVEL[level],
                validation_source=VALIDATION_SOURCES[source_index % len(VALIDATION_SOURCES)],
                reported_by=user,
                approved_by=approver,
            )
            proficiency_count += 1
            source_index += 1

    # Requirements
    for team_name, skill_name, req_level, importance, people_needed in REQUIREMENTS:
        TeamSkillRequirement.objects.create(
            team=teams[team_name],
            skill=_skill(skill_name),
            required_level=req_level,
            importance=importance,
            people_needed=people_needed,
        )

    # Promotion-track requirements: skills for the next role up (purpose='promotion')
    for team_name, skill_name, req_level, importance in PROMOTION_REQUIREMENTS:
        TeamSkillRequirement.objects.create(
            team=teams[team_name],
            skill=_skill(skill_name),
            required_level=req_level,
            importance=importance,
            purpose=TeamSkillRequirement.Purpose.PROMOTION,
        )

    # Lightweight profile records
    for username, activity_type, skill_name, status, completed_at, note in DEVELOPMENT_ACTIVITIES:
        DevelopmentActivity.objects.create(
            user=users[username],
            activity_type=activity_type,
            skill=_skill(skill_name) if skill_name else None,
            status=status,
            completed_at=completed_at,
            note=note,
        )
    for username, role, organization, start_date, end_date, summary in EXPERIENCES:
        ExperienceEntry.objects.create(
            user=users[username],
            role=role,
            organization=organization,
            start_date=start_date,
            end_date=end_date,
            summary=summary,
        )
    for username, period, rating, reviewed_at, goals, achievements, feedback in REVIEWS:
        PerformanceReview.objects.create(
            user=users[username],
            period=period,
            rating=rating,
            reviewed_at=reviewed_at,
            goals=goals,
            achievements=achievements,
            feedback=feedback,
        )

    # Certificates + awards (approved, consistent with existing proficiencies)
    certs = {}
    for name, issuer in CERTIFICATES:
        certs[name] = Certificate.objects.create(name=name, issuer=issuer)
    for username, cert_name, skill_name, level, obtained_on in CERTIFICATE_AWARDS:
        user = users[username]
        team_name = team_role.get(username, (None, "member"))[0]
        CertificateAward.objects.create(
            user=user,
            certificate=certs[cert_name],
            skill=_skill(skill_name),
            level=level,
            obtained_on=obtained_on,
            status=CertificateAward.Status.APPROVED,
            recorded_by=user,
            approved_by=managers.get(team_name, leader),
        )

    # Future demand
    for skill_name, direction, importance, confidence, horizon, source, note in FUTURE_DEMAND:
        SkillFutureDemand.objects.create(
            skill=_skill(skill_name),
            direction=direction,
            future_importance=importance,
            confidence_level=confidence,
            horizon=horizon,
            source=source,
            note=note,
        )

    # Strategic layer: criticality assessments + readiness trend snapshots
    from insights.services import reassess_all
    from skills.models import SkillCriticalityAssessment

    reassess_all()
    for skill_name, (impact, strategic, replace) in CRITICALITY_FACTORS.items():
        SkillCriticalityAssessment.objects.filter(skill=_skill(skill_name)).update(
            business_impact=impact,
            strategic_relevance=strategic,
            time_to_replace_months=replace,
        )
    reassess_all()  # recompute with the business-impact factors applied

    from insights.services import snapshot_readiness

    snapshot_readiness()

    small_teams = [
        t.name
        for t in Team.objects.all()
        if t.memberships.count() <= 4
    ]
    _out("Seeded organization:")
    _out(f"  users: {User.objects.count()} | employees with profiles: {len(PEOPLE)}")
    _out(f"  departments: {Department.objects.count()} | teams: {Team.objects.count()}")
    _out(f"  proficiencies: {proficiency_count} | requirements: {TeamSkillRequirement.objects.count()}")
    _out(f"  promotion requirements: {TeamSkillRequirement.objects.filter(purpose='promotion').count()}")
    _out(f"  profile entries: {DevelopmentActivity.objects.count() + ExperienceEntry.objects.count() + PerformanceReview.objects.count()}")
    _out(f"  skill-graph edges: {SkillRelationship.objects.count()}")
    _out(f"  future-demand rows: {SkillFutureDemand.objects.count()}")
    _out(f"  criticality assessments: {SkillCriticalityAssessment.objects.count()}")
    _out(f"  small teams (<=4): {', '.join(small_teams) if small_teams else 'none'}")
    _out(f"  demo logins (password {DEFAULT_PASSWORD}): "
         "alex.rivera (leadership), sam.lee (manager), jordan.mendez (employee)")