"""Transparent skill-gap scoring.

gap      = max(target - current, 0)
status   = achieved (gap 0) | missing (current 0) | improve (otherwise)
score    = 100 * SUM(importance * min(current, target) / target) / SUM(importance)

The score is a progress indicator against a SAMPLE profile.
It is not a hiring probability or a measure of employability."""

def analyze(rows, levels):
    items, num, den = [], 0.0, 0
    for r in rows:
        cur = levels.get(r["skill_id"], 0)
        gap = max(r["target"] - cur, 0)
        status = "achieved" if gap == 0 else ("missing" if cur == 0 else "improve")
        num += r["importance"] * min(cur, r["target"]) / r["target"]
        den += r["importance"]
        items.append({**r, "current": cur, "gap": gap, "status": status, "priority": r["importance"] * gap})
    counts = {k: sum(i["status"] == k for i in items) for k in ("achieved", "improve", "missing")}
    top = sorted((i for i in items if i["gap"]), key=lambda i: (-i["priority"], i["name"]))[:3]
    return {"items": items, "score": round(100 * num / den) if den else 0, "counts": counts, "top": top}
