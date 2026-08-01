"""Champion records from ended challenges — pure and DB-free.

A champion is rank 1 of an ended challenge's leaderboard with a truthy
score. No Champion table: recomputing on read lets late re-analyses
self-correct (route layer adds a short TTL cache).
"""


def shape_champions(ended):
    """ended: [{"competition": {id,name,end_date}, "leaderboard": payload}]"""
    champions = []
    for item in ended or []:
        comp = item.get("competition") or {}
        lb = item.get("leaderboard") or {}
        rows = lb.get("rows") or []
        top = next((r for r in rows if r.get("rank") == 1 and r.get("score")), None)
        if top is None:
            continue
        champions.append({
            "user_id": top.get("user_id"),
            "name": top.get("name"),
            "competition_id": comp.get("id"),
            "competition_name": comp.get("name"),
            "metric": lb.get("metric"),
            "score": top.get("score"),
            "ended_on": comp.get("end_date"),
            "attempt_id": top.get("attempt_id"),
        })
    champions.sort(key=lambda c: str(c["ended_on"] or ""), reverse=True)
    return champions
