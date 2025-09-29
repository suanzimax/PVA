#!/bin/bash
mkdir -p results
PROTO=${1:-ca}
echo "Running latency monitor (protocol=$PROTO)..."
python3 01_latency_monitor.py --protocol "$PROTO" &
LAT_PID=$!

echo "Running throughput monitor (protocol=$PROTO)..."
python3 02_throughput.py --protocol "$PROTO" &
THR_PID=$!

echo "Running packet loss monitor (protocol=$PROTO)..."
python3 03_packetloss.py --protocol "$PROTO" &
LOSS_PID=$!

echo "Running CPU monitor..."
python3 04_cpu.py &
CPU_PID=$!

echo "Press Ctrl+C to stop all tests."
trap "kill $LAT_PID $THR_PID $LOSS_PID $CPU_PID" SIGINT
wait
