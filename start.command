#!/bin/bash
# Double-click this file to start Jev Art.
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "⚠️  No secret key found."
  echo "Please do Step 1 in the README: copy .env.example to .env and paste your key."
  echo ""
  echo "Press any key to close this window."
  read -n 1
  exit 1
fi

echo "🎨 Starting Jev Art..."
python3 serve.py &
SERVER=$!
sleep 2
open "http://localhost:8000"
echo ""
echo "✅ Jev Art is running. Keep this window open."
echo "   To stop, close this window (or press Control + C)."
wait $SERVER
