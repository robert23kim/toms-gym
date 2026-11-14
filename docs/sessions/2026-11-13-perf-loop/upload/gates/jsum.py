import json, sys
d = json.load(open(sys.argv[1]))
print('suites', d['numTotalTestSuites'], 'failedSuites', d['numFailedTestSuites'], '| tests', d['numTotalTests'], 'passed', d['numPassedTests'], 'failed', d['numFailedTests'])
for s in d['testResults']:
    for a in s['assertionResults']:
        if a['status'] != 'passed': print(' ', a['status'], '|', a['title'], '\n   ', '\n'.join(a['failureMessages'])[:int(sys.argv[2]) if len(sys.argv) > 2 else 500])
    if s['status'] != 'passed' and not any(a['status'] == 'failed' for a in s['assertionResults']): print('  SUITE', s['name'].split('/src/')[-1], (s.get('message') or '')[:800])
