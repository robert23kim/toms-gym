#!/bin/bash
set -e

# Configuration
PROD_URL="${PROD_BACKEND_URL:-https://my-python-backend-quyiiugyoq-ue.a.run.app}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/e2e-venv"

echo "==================================================="
echo "  E2E Tests Against Production"
echo "==================================================="
echo ""
echo "Target Backend: $PROD_URL"
echo "Test Directory: $SCRIPT_DIR/e2e"
echo ""

# Health check
echo "[1/4] Checking production health..."
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$PROD_URL/health" || echo "000")

if [ "$HEALTH_RESPONSE" != "200" ]; then
    echo "ERROR: Production health check failed (HTTP $HEALTH_RESPONSE)"
    echo "       Please ensure the backend is running at $PROD_URL"
    exit 1
fi

echo "      Production is healthy!"
echo ""

# Create virtual environment if it doesn't exist
echo "[2/4] Setting up virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    echo "      Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"
echo "      Virtual environment activated!"
echo ""

# Install dependencies
echo "[3/4] Installing test dependencies..."
pip install -q -r "$SCRIPT_DIR/requirements-e2e.txt"
echo "      Dependencies installed!"
echo ""

# Run tests
echo "[4/4] Running E2E tests..."
echo ""

cd "$SCRIPT_DIR"

# Run pytest with verbose output
python -m pytest e2e/ \
    -v \
    --tb=short \
    -x \
    --durations=10 \
    "$@"

TEST_EXIT_CODE=$?

# Deactivate virtual environment
deactivate 2>/dev/null || true

echo ""
echo "==================================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "  E2E Tests PASSED"
else
    echo "  E2E Tests FAILED (exit code: $TEST_EXIT_CODE)"
    echo ""
    echo "  Debug with production logs:"
    echo "    gcloud run services logs read my-python-backend \\"
    echo "      --project=toms-gym --region=us-east1 --limit=100"
fi
echo "==================================================="

exit $TEST_EXIT_CODE
