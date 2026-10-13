"""Maintainable example career catalogue.

Profiles are educational examples, not verified employer requirements. New
roles can be added to ``ROLE_SPECS`` without changing templates or routes.
"""

LEVELS = ["None", "Beginner", "Intermediate", "Advanced"]


def _r(title, url, kind):
    return {"title": title, "url": url, "type": kind, "cost": "free"}


_RESOURCES = {
    "Python": _r("The Python Tutorial", "https://docs.python.org/3/tutorial/", "Documentation"),
    "SQL": _r("SQLite SQL language reference", "https://www.sqlite.org/lang.html", "Documentation"),
    "Git": _r("Pro Git book", "https://git-scm.com/book/en/v2", "Book"),
    "JavaScript": _r("MDN JavaScript Guide", "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", "Documentation"),
    "HTML & CSS": _r("MDN Learn web development", "https://developer.mozilla.org/en-US/docs/Learn_web_development", "Tutorial"),
    "Statistics": _r("Statistics and probability", "https://www.khanacademy.org/math/statistics-probability", "Course"),
    "Cloud fundamentals": _r("AWS Cloud Practitioner learning", "https://aws.amazon.com/training/learn-about/cloud-practitioner/", "Course"),
    "Linux": _r("Linux Journey", "https://linuxjourney.com/", "Course"),
    "Networking": _r("Cisco Networking Basics", "https://www.netacad.com/courses/networking", "Course"),
}

_WHY = {
    "Python": "A versatile language for automation, data and backend systems.",
    "SQL": "A core skill for querying and understanding structured data.",
    "Git": "Version control enables safe collaboration and a professional portfolio.",
    "JavaScript": "The language of interactive browser experiences and many services.",
    "HTML & CSS": "The accessible, visual foundation of web products.",
    "Statistics": "Helps separate meaningful patterns from noise.",
    "Cloud fundamentals": "Cloud concepts support modern deployment and architecture.",
    "Linux": "Many production, security and developer tools run on Linux.",
    "Networking": "Understanding how systems communicate improves reliability and security.",
}

_BASE_SKILLS = [
    "Python", "SQL", "Git", "JavaScript", "HTML & CSS", "Statistics",
    "Cloud fundamentals", "Linux", "Networking", "Data structures",
    "Testing", "APIs", "Data modeling", "Data visualization", "Data cleaning",
    "Machine learning", "Deep learning", "Cybersecurity fundamentals",
    "Threat modeling", "Containers", "CI/CD", "Terraform", "Java", "C++",
    "React", "Mobile development", "UX research", "Wireframing", "Communication",
    "Agile delivery", "Technical writing", "Product strategy", "SEO",
    "Embedded systems", "IoT", "Robotics", "Blockchain", "Customer support",
]

_CATEGORIES = {
    "software-development": ("Software Development", [
        "Python Developer", "Java Developer", "C++ Developer", "Frontend Developer",
        "Backend Developer", "Full-Stack Developer", "Mobile App Developer",
        "Game Developer", "Software Engineer", "QA / Software Test Engineer",
    ]),
    "data-ai": ("Data and Artificial Intelligence", [
        "Data Analyst", "Data Scientist", "Data Engineer", "Machine Learning Engineer",
        "AI Engineer", "Business Intelligence Analyst", "Data Visualization Specialist", "NLP Engineer",
    ]),
    "cybersecurity-networking": ("Cybersecurity and Networking", [
        "Cybersecurity Analyst", "Penetration Tester", "Security Engineer",
        "Network Engineer", "Cloud Security Engineer",
    ]),
    "cloud-devops": ("Cloud and DevOps", [
        "Cloud Engineer", "AWS Cloud Practitioner / Cloud Engineer",
        "Microsoft Azure Cloud Engineer", "DevOps Engineer", "Site Reliability Engineer", "Platform Engineer",
    ]),
    "database-enterprise": ("Database and Enterprise Systems", [
        "SQL Developer", "Database Administrator", "Database Engineer",
        "Oracle Database Developer", "ERP Technical Consultant",
    ]),
    "web-design": ("Web, UI/UX, and Design", [
        "UI/UX Designer", "Web Designer", "Product Designer", "Graphic Designer",
    ]),
    "business-digital": ("Business and Digital Careers", [
        "Business Analyst", "Product Manager", "Digital Marketing Specialist",
        "SEO Specialist", "Project Coordinator",
    ]),
    "other-technology": ("Other Technology Careers", [
        "Embedded Systems Developer", "IoT Developer", "Robotics Engineer",
        "Blockchain Developer", "Technical Support Engineer",
    ]),
}

_SPECIAL = {
    "Data Analyst": ["SQL", "Python", "Data cleaning", "Statistics", "Data visualization"],
    "Python Developer": ["Python", "APIs", "Testing", "Git", "SQL"],
    "Frontend Developer": ["HTML & CSS", "JavaScript", "React", "Testing", "Git"],
    "Backend Developer": ["Python", "APIs", "SQL", "Testing", "Git"],
    "Data Scientist": ["Python", "SQL", "Statistics", "Machine learning", "Data visualization"],
    "Machine Learning Engineer": ["Python", "Machine learning", "Data structures", "APIs", "Git"],
    "Cybersecurity Analyst": ["Linux", "Networking", "Cybersecurity fundamentals", "Threat modeling", "Technical writing"],
    "DevOps Engineer": ["Linux", "Cloud fundamentals", "Containers", "CI/CD", "Terraform"],
    "UI/UX Designer": ["UX research", "Wireframing", "Communication", "Technical writing", "Agile delivery"],
    "SQL Developer": ["SQL", "Data modeling", "Testing", "Git", "Technical writing"],
}


def _slug(title):
    return "".join(c.lower() if c.isalnum() else "-" for c in title).strip("-")


def _spec(title, category):
    skills = _SPECIAL.get(title)
    if not skills:
        skills = {
            "software-development": ["Programming", "Data structures", "Git", "Testing", "APIs"],
            "data-ai": ["Python", "SQL", "Statistics", "Data visualization", "Data modeling"],
            "cybersecurity-networking": ["Linux", "Networking", "Cybersecurity fundamentals", "Threat modeling", "Technical writing"],
            "cloud-devops": ["Linux", "Cloud fundamentals", "Containers", "CI/CD", "Terraform"],
            "database-enterprise": ["SQL", "Data modeling", "Testing", "Linux", "Technical writing"],
            "web-design": ["HTML & CSS", "UX research", "Wireframing", "Communication", "Agile delivery"],
            "business-digital": ["Communication", "Statistics", "Agile delivery", "Technical writing", "Product strategy"],
            "other-technology": ["Programming", "Technical writing", "Testing", "Communication", "Git"],
        }[category]
    return {
        "title": title, "category": category, "overview": f"A practical pathway for building capability as a {title}.",
        "responsibilities": [f"Apply {skills[0]} to solve real user or business problems.",
                            "Collaborate with teammates and communicate decisions clearly.",
                            "Build, test and improve work through feedback."],
        "soft_skills": ["Communication", "Problem solving", "Curiosity", "Collaboration"],
        "skills": [(name, 2 if i else 3, 3 if i < 2 else 2, skills[i - 1] if i else None)
                   for i, name in enumerate(skills)],
        "tools": skills[:3], "project": {
            "title": f"{title} portfolio starter", "problem": f"Create a small, useful project that demonstrates {skills[0]} and {skills[1]}.",
            "features": ["Document the problem and approach", "Test the important workflow", "Publish a clear README and demo"],
            "deliverables": "Repository, demo or screenshots, and a short reflection.",
        },
    }


ROLES = {}
for _category, (_label, _titles) in _CATEGORIES.items():
    for _title in _titles:
        ROLES[_slug(_title)] = _spec(_title, _category)

# Preserve the original demo slugs and richer examples.
ROLES["web-developer"] = _spec("Web Developer", "web-design")
ROLES["web-developer"]["skills"] = [("HTML & CSS", 3, 3, None), ("JavaScript", 2, 3, "HTML & CSS"),
                                    ("Responsive design", 2, 2, "HTML & CSS"), ("Accessibility", 2, 2, "HTML & CSS"), ("Git", 2, 1, None)]
ROLES["python-developer"] = _spec("Python Developer", "software-development")

SKILLS = {}
for _name in _BASE_SKILLS:
    SKILLS[_name] = {"why": _WHY.get(_name, f"{_name} supports effective work in this career."),
                     "hours": 10, "task": f"Complete a focused practice project using {_name}.",
                     "res": [_RESOURCES[_name]] if _name in _RESOURCES else []}
for _role in ROLES.values():
    for _name, _, _, _ in _role["skills"]:
        SKILLS.setdefault(_name, {"why": f"{_name} supports effective work in this career.", "hours": 10,
                                   "task": f"Complete a focused practice project using {_name}.", "res": []})


def role_info(slug, title=None):
    """Return display metadata for a catalog or user-created role."""
    return ROLES.get(slug) or _spec(title or slug.replace("-", " ").title(), "other-technology")


def categories():
    return [(slug, label) for slug, (label, _) in _CATEGORIES.items()]


def seed(conn):
    for name, skill in SKILLS.items():
        conn.execute("INSERT OR IGNORE INTO skills (name, description) VALUES (?, ?)", (name, skill["why"]))
        sid = conn.execute("SELECT id FROM skills WHERE name=?", (name,)).fetchone()["id"]
        for resource in skill["res"]:
            conn.execute("INSERT OR IGNORE INTO learning_resources (skill_id,title,description,resource_type,url,cost) VALUES (?,?,?,?,?,?)",
                         (sid, resource["title"], "", resource["type"], resource["url"], resource["cost"]))
    for slug, role in ROLES.items():
        conn.execute("INSERT OR IGNORE INTO career_roles (slug,title,overview,category) VALUES (?,?,?,?)",
                     (slug, role["title"], role["overview"], role["category"]))
        conn.execute("UPDATE career_roles SET title=?, overview=?, category=? WHERE slug=?",
                     (role["title"], role["overview"], role["category"], slug))
        rid = conn.execute("SELECT id FROM career_roles WHERE slug=?", (slug,)).fetchone()["id"]
        for name, target, importance, prereq in role["skills"]:
            sid = conn.execute("SELECT id FROM skills WHERE name=?", (name,)).fetchone()["id"]
            pre_id = conn.execute("SELECT id FROM skills WHERE name=?", (prereq,)).fetchone()["id"] if prereq else None
            conn.execute("INSERT OR IGNORE INTO career_role_skills VALUES (?,?,?,?,?)", (rid, sid, target, importance, pre_id))
    conn.commit()
