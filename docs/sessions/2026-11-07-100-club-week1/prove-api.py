import json, subprocess, urllib.request, urllib.error, sys
D="/Users/toka/code/toms_gym/docs/sessions/2026-11-07-100-club-week1"
B="https://my-python-backend-quyiiugyoq-ue.a.run.app"
C="32ca7bad-a970-4a09-acec-02b768793063"
def get(url, hdr=None):
    r=urllib.request.Request(url, headers=hdr or {})
    try:
        with urllib.request.urlopen(r, timeout=60) as f: return f.status, f.read()
    except urllib.error.HTTPError as e: return e.code, e.read()
def key(row): return (row["rank"], row["score"], row["streak"], row["this_week"]["lifts"], row["attempt_count"])
def cmp(label, cur, ref):
    rc={r["user_id"]:r for r in cur["rows"]}; rf={r["user_id"]:r for r in ref["rows"]}
    print(label, "user_ids equal:", set(rc)==set(rf), "n=", len(rc))
    ok=True
    for u,r in rf.items():
        c=rc.get(u)
        print(" ", r["name"], "ref", key(r), "now", key(c) if c else None, "EQ" if c and key(c)==key(r) else "DIFF")
        ok = ok and bool(c) and key(c)==key(r)
    return ok
s,b=get(f"{B}/competitions/{C}/leaderboard"); print("public", s, len(b))
cur=json.loads(b); open(f"{D}/prove-live.json","wb").write(b)
ok1=cmp("LIVE", cur, json.load(open(f"{D}/live-before.json")))
print(" consistency now: week_index", cur["consistency"]["week_index"], "days_left", cur["consistency"]["days_left"], "leaders", {k:[x["name"] for x in v] for k,v in cur["consistency"]["type_leaders"].items()})
tok=subprocess.run(["gcloud","secrets","versions","access","latest","--secret=admin-token","--project=toms-gym"],capture_output=True,text=True).stdout.strip()
print("token len", len(tok))
asof="2026-11-09T12:00:00-05:00".replace("+","%2B")
s,b=get(f"{B}/competitions/{C}/leaderboard?as_of={asof}", {"X-Admin-Token":tok}); print("admin as_of", s, len(b))
mon=json.loads(b); open(f"{D}/prove-monday.json","wb").write(b)
ok2=cmp("MONDAY", mon, json.load(open(f"{D}/monday-before.json")))
print(" monday: week_index", mon["consistency"]["week_index"], "leaders", mon["consistency"]["type_leaders"], "quotas", [r["this_week"]["quota"] for r in mon["rows"]], "scores", [(r["name"],r["score"]) for r in mon["rows"]])
s,b=get(f"{B}/competitions/{C}/leaderboard?as_of={asof}"); print("as_of no header", s, b[:120])
s,b=get(f"{B}/competitions/{C}/leaderboard?as_of={asof}", {"X-Admin-Token":"wrong"}); print("as_of wrong token", s, b[:120])
print("ALL", ok1, ok2)
