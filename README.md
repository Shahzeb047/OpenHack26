# CareerPath AI - Career & Skill-Gap Navigator

Explore many career paths, rate your skills, see transparent gaps, and follow a roadmap built from those gaps.
Flask + SQLite. Core career exploration works locally; account verification requires SMTP configuration.

## Run on Windows (VS Code terminal, inside this folder)
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Copy `.env.example` to `.env` and set a real SMTP provider plus a strong secret key before registering users.
Open http://127.0.0.1:5000. The database (`instance/skillora.db`) is created automatically and existing data is preserved.

Email verification is currently disabled. Account creation and login use only the email address and
password, so SMTP configuration is not required for authentication.

For real email delivery, configure all SMTP variables and set `CAREERPATH_DEV_EMAIL=0`. If SMTP
credentials are incomplete or invalid, the application will report that configuration error rather than
pretending that an email was sent.

## Run tests
```
python -m unittest discover -s tests -v
```

## 3-minute demo
1. Configure SMTP, create an account, and verify the email.
2. Complete your profile, then choose a career path.
3. **Dashboard**: skill match, met / improve / missing skills.
4. **Roadmap**: open a resource, set a milestone to In progress, then Completed.
5. Back on the **Dashboard**: roadmap completion updated and saved.
6. **Skills**: raise a level, save, watch the score change.
7. **Careers**: search and filter the expanded catalogue, then switch to another role and compare.

## How the score works
`score = 100 x sum(importance x min(current, target) / target) / sum(importance)`
Levels: 0 Not yet learned, 1 Beginner, 2 Intermediate, 3 Advanced. It is a progress indicator
against a sample profile, not a hiring probability. Self-reported levels are not proof of skill.

## Add a career
Edit `services/career_catalog.py` and add a title to `_CATEGORIES` or a skill mapping to
`_SPECIAL`. The catalogue is seeded into SQLite on next start. Users can also add custom targets
from the Careers page; these are clearly marked as user-entered and unverified.

## Structure
`app.py` routes | `database.py` schema and migration | `services/` catalogue, scoring, roadmap | `templates/` | `static/` | `tests/`

## Known limitations
Verified email accounts now own isolated profiles, skills and roadmaps. Role requirements are predefined
examples unless a custom target is explicitly added. Resource availability and pricing are not checked.
SMTP credentials and secret keys must never be committed; `.env` is ignored and `.env.example` documents the required variables.

## Git
`git init`, `git add .`, `git commit -m "CareerPath AI MVP"`, then push to your GitHub repo.
