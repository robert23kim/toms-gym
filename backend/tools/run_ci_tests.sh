#!/usr/bin/env bash
# DB-free backend test gate, used by .github/workflows/ci-cd.yml and runnable
# locally: cd backend && tools/run_ci_tests.sh
#
# tests/conftest.py has an autouse session fixture (init_db) that connects to
# the real Cloud SQL instance, so CI runs with --noconftest and selects only
# the suites that are pure or mock the DB themselves. Tests that need the
# conftest's live-DB fixtures are deselected below; run those locally with
# DB credentials.
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python}"

exec "$PYTHON" -m pytest \
  tests/test_handicap.py \
  tests/test_scorecard_grid.py \
  tests/test_challenge_leaderboard.py \
  tests/test_guest_round_classify.py \
  tests/test_golf_parser.py \
  tests/test_competition_routes.py \
  --noconftest -q \
  --deselect tests/test_golf_parser.py::test_rate_limit_bypass_is_wired \
  --deselect tests/test_golf_parser.py::test_upload_resolves_existing_course_by_name \
  --deselect tests/test_golf_parser.py::test_upload_creates_pending_course_on_miss \
  --deselect tests/test_golf_parser.py::test_upload_marks_needs_tee_when_no_tee_on_course \
  --deselect tests/test_competition_routes.py::test_get_competitions \
  --deselect tests/test_competition_routes.py::test_get_nonexistent_competition \
  --deselect tests/test_competition_routes.py::test_create_competition \
  --deselect tests/test_competition_routes.py::test_get_competition_by_id
