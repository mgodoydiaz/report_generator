#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "  Report Generator - Starting services"
echo "============================================"

# --- 1. PostgreSQL ---
echo ""
echo "[1/3] Checking PostgreSQL..."
if sudo service postgresql start 2>/dev/null; then
    echo "[OK]   PostgreSQL started."
else
    echo "[OK]   PostgreSQL already running or not managed by service."
fi

# --- 2. Backend ---
echo ""
echo "[2/3] Starting Backend on http://127.0.0.1:8000 ..."
conda activate rgenerator 2>/dev/null || source "$(conda info --base)/etc/profile.d/conda.sh" && conda activate rgenerator
python -m backend.api &
BACKEND_PID=$!
echo "[OK]   Backend PID=$BACKEND_PID"

# --- 3. Frontend ---
echo ""
echo "[3/3] Starting Frontend on http://localhost:5173 ..."
cd frontend && npm run dev &
FRONTEND_PID=$!
echo "[OK]   Frontend PID=$FRONTEND_PID"

echo ""
echo "============================================"
echo "  All services launched."
echo "  - Backend  : http://127.0.0.1:8000"
echo "  - Frontend : http://localhost:5173"
echo "  Press Ctrl+C to stop all services."
echo "============================================"

trap "echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" SIGINT SIGTERM
wait
