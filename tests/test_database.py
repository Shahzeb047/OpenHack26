import sqlite3, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import create_app
from database import init_db, get_connection

EXPECTED = {"students","skills","student_skills","courses","projects","career_roles",
            "career_role_skills","learning_resources","roadmap_milestones",
            "milestone_resources","progress_activity","assessment_attempts"}

class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "t.db")
    def tearDown(self):
        self.tmp.cleanup()

    def test_init_creates_tables(self):
        init_db(self.db)
        c = get_connection(self.db)
        names = {r["name"] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        c.close()
        self.assertTrue(EXPECTED <= names)

    def test_init_is_idempotent_and_keeps_data(self):
        init_db(self.db)
        c = get_connection(self.db)
        c.execute("INSERT INTO students (display_name) VALUES (?)", ("Ayesha",)); c.commit(); c.close()
        init_db(self.db)
        c = get_connection(self.db)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM students").fetchone()[0], 1); c.close()

    def test_foreign_keys_enforced(self):
        init_db(self.db)
        c = get_connection(self.db)
        with self.assertRaises(sqlite3.IntegrityError):
            c.execute("INSERT INTO student_skills (student_id, skill_id, level) VALUES (99, 99, 1)")
        c.close()

    def test_level_constraint(self):
        init_db(self.db)
        c = get_connection(self.db)
        c.execute("INSERT INTO students (display_name) VALUES ('A')")
        c.execute("INSERT INTO skills (name) VALUES ('SQL')")
        with self.assertRaises(sqlite3.IntegrityError):
            c.execute("INSERT INTO student_skills (student_id, skill_id, level) VALUES (1, 1, 7)")
        c.close()

class RouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.client = create_app({"TESTING": True,
            "DATABASE": str(Path(self.tmp.name) / "t.db")}).test_client()
    def tearDown(self):
        self.tmp.cleanup()
    def test_landing(self):
        r = self.client.get("/"); self.assertEqual(r.status_code, 200)
        self.assertIn(b"Turn Your Skills Into Your Next Opportunity.", r.data)
    def test_cta_targets_exist(self):
        for path in ("/profile", "/careers", "/health"):
            self.assertEqual(self.client.get(path).status_code, 200)
    def test_404(self):
        self.assertEqual(self.client.get("/nope").status_code, 404)

if __name__ == "__main__":
    unittest.main()
