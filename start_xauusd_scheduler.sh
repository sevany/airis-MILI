#!/bin/bash
# Start XAUUSD Daily Scheduler
# Runs data update at 7 AM every day

cd "$(dirname "$0")"

echo "🔄 Starting XAUUSD Daily Scheduler..."
echo "📅 Updates scheduled for 7:00 AM daily"
echo ""

python3 -m backend.tools.xauusd_scheduler