import json, pathlib, subprocess, sys, hashlib
FE = pathlib.Path('/Users/toka/code/toms_gym-perf/frontend')
spec = json.load(open(sys.argv[1]))
out = []
for i, m in enumerate(spec):
    p = FE / m['file']
    orig = p.read_text()
    assert orig.count(m['old']) == 1, f"{m['id']}: anchor count {orig.count(m['old'])}"
    mutated = orig.replace(m['old'], m['new'])
    p.write_text(mutated)
    try:
        reread = p.read_text()
        assert reread == mutated and reread != orig and m['new'] in reread, f"{m['id']}: mutation not on disk"
        res = FE / f"../../../private/tmp/x"  # unused
        jf = f"{sys.argv[2]}/mut-{m['id']}.json"
        subprocess.run(['node', 'node_modules/jest/bin/jest.js', '--coverage=false', '--maxWorkers=4', '--json', f'--outputFile={jf}'] + m['tests'], cwd=FE, capture_output=True)
        d = json.load(open(jf))
        failed = [a['title'] for s in d['testResults'] for a in s['assertionResults'] if a['status'] == 'failed']
        suite_fail = [s['name'].split('/src/')[-1] for s in d['testResults'] if s['status'] != 'passed' and not s['assertionResults']]
        hit = any(m['expect'] in t for t in failed)
        out.append(dict(id=m['id'], file=m['file'], killed=bool(hit), failed=failed, suite_fail=suite_fail, total=d['numTotalTests']))
        print(m['id'], 'KILLED' if hit else 'SURVIVED', '| failed:', failed, suite_fail)
    finally:
        p.write_text(orig)
        assert p.read_text() == orig
        print('   restored sha', hashlib.sha1(orig.encode()).hexdigest()[:10])
json.dump(out, open(f"{sys.argv[2]}/mutation-results-{pathlib.Path(sys.argv[1]).stem}.json", 'w'), indent=1)
