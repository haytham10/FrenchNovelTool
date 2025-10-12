#!/bin/bash
set -e

# Start frontend (Next.js) in background
cd frontend
npm i
npm run dev &
FRONTEND_PID=$!
cd ..

# Activate Python venv and start backend (Flask)
cd backend
source ../.venv/Scripts/activate
pip install -r requirements.txt

export FLASK_APP=app
export FLASK_ENV=development
flask run &

BACKEND_PID=$!
cd ..

# Wait for both processes
trap "kill $FRONTEND_PID $BACKEND_PID" SIGINT SIGTERM
wait $FRONTEND_PID $BACKEND_PID