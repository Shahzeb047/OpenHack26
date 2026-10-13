import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import create_app
from services.skill_analyzer import analyze
from services.roadmap_generator import order

def row(i, target, imp, pre=None): return {"skill_id": i, "name": f"S{i}", "target": target, "importance": imp, "prereq_id": pre, "why": ""}

class AnalyzerTests(unittest.TestCase):
    def test_classification(self):
        a = analyze([row(1,2,3), row(2,3,2), row(3,2,1)], {1: 2, 2: 1})
        self.assertEqual([i["status"] for i in a["items"]], ["achieved", "improve", "missing"])
    def test_weighted_score(self):  # (3*1 + 2*(1/3)) / 5 = 0.7333
        self.assertEqual(analyze([row(1,2,3), row(2,3,2)], {1: 2, 2: 1})["score"], 73)
    def test_exceeding_target_is_capped(self):
        self.assertEqual(analyze([row(1,1,1)], {1: 3})["score"], 100)
    def test_prerequisite_comes_first(self):
        items = analyze([row(1,3,3,pre=2), row(2,1,1)], {})["items"]  # skill 1 has higher priority but needs 2
        self.assertEqual([i["skill_id"] for i in order(items)], [2, 1])

class FlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "t.db")
        self.c = create_app({"TESTING": True, "DATABASE": self.db}).test_client()
    def tearDown(self): self.tmp.cleanup()

    def test_empty_state_pages_render(self):
        for p in ("/dashboard", "/profile", "/careers"): self.assertEqual(self.c.get(p).status_code, 200)
    def test_invalid_profile_rejected(self):
        self.assertEqual(self.c.post("/profile", data={"display_name": " "}).status_code, 400)
    def test_demo_flow_and_persistence(self):
        self.c.post("/demo")
        self.assertIn(b"Demo Student", self.c.get("/dashboard").data)
        self.assertIn(b"Roadmap", self.c.get("/roadmap").data)
        r = self.c.patch("/api/milestones/1", json={"status": "completed"})
        self.assertEqual(r.get_json()["completed"], 1)
        again = create_app({"TESTING": True, "DATABASE": self.db}).test_client()  # simulated restart
        self.assertIn(b"1 of", again.get("/roadmap").data)
    def test_milestone_errors(self):
        self.c.post("/demo")
        self.assertEqual(self.c.patch("/api/milestones/9999", json={"status": "completed"}).status_code, 404)
        self.assertEqual(self.c.patch("/api/milestones/1", json={"status": "bogus"}).status_code, 400)
    def test_changing_skill_recalculates(self):
        self.c.post("/demo")
        before = self.c.get("/dashboard").data
        data = {f"skill_{i}": "3" for i in range(1, 13)}
        self.c.post("/assessment", data=data)
        self.assertNotEqual(before, self.c.get("/dashboard").data)
    def test_invalid_level_rejected(self):
        self.c.post("/demo")
        self.assertEqual(self.c.post("/assessment", data={"skill_1": "9"}).status_code, 400)
    def test_career_switch_changes_analysis(self):
        self.c.post("/demo")
        self.c.post("/careers", data={"slug": "web-developer"})
        self.assertIn(b"Web Developer", self.c.get("/roadmap").data)
    def test_seed_not_duplicated(self):
        create_app({"TESTING": True, "DATABASE": self.db})
        from database import get_connection
        self.assertEqual(get_connection(self.db).execute("SELECT COUNT(*) FROM career_roles").fetchone()[0], 3)

if __name__ == "__main__": unittest.main()
