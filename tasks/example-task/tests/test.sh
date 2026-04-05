#!/bin/bash
set -e

cd /task

# Run the test
if python test_app.py; then
    echo "1.0" > /logs/reward.txt
    echo "PASS" >> /logs/reward.txt
else
    echo "0.0" > /logs/reward.txt
    echo "FAIL" >> /logs/reward.txt
fi
