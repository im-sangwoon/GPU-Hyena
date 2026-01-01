#!/bin/bash
nohup python -u monitor.py > monitor.log 2>&1 &
echo "GPU Hyena started in background. Logs are in monitor.log"
echo "PID: $!"
