"""Deterministic roadmap: every milestone comes from a real skill gap."""
from services.career_catalog import SKILLS, LEVELS

def order(items):
    """Highest priority first, but a prerequisite gap always comes before its dependants."""
    gaps = sorted((i for i in items if i["gap"]), key=lambda i: (-i["priority"], i["name"]))
    pending, out = {i["skill_id"] for i in gaps}, []
    while gaps:
        for i in gaps:
            if i["prereq_id"] not in pending:
                out.append(i); pending.discard(i["skill_id"]); gaps.remove(i); break
        else:
            out.extend(gaps); break
    return out

def sync(conn, student_id, role_id, items):
    """Create/refresh milestones; keep saved status and notes of existing ones."""
    ordered = order(items)
    keep = [i["skill_id"] for i in ordered]
    for m in conn.execute("SELECT id, skill_id, status FROM roadmap_milestones WHERE student_id=? AND role_id=?",
                          (student_id, role_id)).fetchall():
        if m["skill_id"] not in keep and m["status"] == "not_started":
            conn.execute("DELETE FROM roadmap_milestones WHERE id=?", (m["id"],))
    for pos, i in enumerate(ordered, 1):
        skill = SKILLS.get(i["name"], {"hours": 10})
        hours = skill["hours"] * i["gap"]
        title = f"Reach {LEVELS[i['target']]} level in {i['name']}"
        obj = f"Move from {LEVELS[i['current']]} to {LEVELS[i['target']]}. {i['why']}"
        conn.execute("""INSERT INTO roadmap_milestones (student_id,role_id,skill_id,position,title,objective,estimated_hours)
                        VALUES (?,?,?,?,?,?,?)
                        ON CONFLICT(student_id,role_id,skill_id) DO UPDATE SET
                        position=excluded.position, title=excluded.title,
                        objective=excluded.objective, estimated_hours=excluded.estimated_hours""",
                     (student_id, role_id, i["skill_id"], pos, title, obj, hours))
    conn.commit()
