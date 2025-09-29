import time
import csv
import os
import argparse
import numpy as np
from config import CAMERA_PVS, RESULTS_DIR
from client_utils import create_monitors, cleanup_monitors

os.makedirs(RESULTS_DIR, exist_ok=True)
results_file = os.path.join(RESULTS_DIR, "throughput.csv")

with open(results_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["pv", "bytes_per_sec", "mb_per_sec"])

interval = 5  # 统计窗口 (秒)
counters = {pv: {"bytes": 0, "last": time.time()} for pv in CAMERA_PVS}


def on_update(pvname, value, timestamp):
    if hasattr(value, 'nbytes'):
        try:
            counters[pvname]["bytes"] += int(value.nbytes)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Throughput monitor for EPICS CA/PVA")
    parser.add_argument("--protocol", choices=["ca", "pva"], default="ca")
    parser.add_argument("--interval", type=int, default=interval, help="统计窗口秒数 (default 5)")
    args = parser.parse_args()

    global interval
    interval = args.interval

    monitors, backend = create_monitors(CAMERA_PVS, args.protocol, on_update)
    print(f"Throughput monitor started using protocol: {args.protocol.upper()}. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(interval)
            now = time.time()
            for pv in CAMERA_PVS:
                elapsed = now - counters[pv]["last"]
                if elapsed > 0:
                    bps = counters[pv]["bytes"] / elapsed
                    mbps = bps / (1024 * 1024)
                    with open(results_file, "a", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow([pv, bps, mbps])
                    counters[pv] = {"bytes": 0, "last": now}
    except KeyboardInterrupt:
        print("Stopped throughput monitor.")
    finally:
        cleanup_monitors(monitors, backend)


if __name__ == "__main__":
    main()
