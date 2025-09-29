import time
import csv
import os
import argparse
from config import CAMERA_PVS, RESULTS_DIR
from client_utils import create_monitors, cleanup_monitors

os.makedirs(RESULTS_DIR, exist_ok=True)

results_file = os.path.join(RESULTS_DIR, "latency.csv")
with open(results_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["pv", "frame_interval_sec"])

last_time = {pv: None for pv in CAMERA_PVS}


def on_update(pvname, value, timestamp):  # unified signature from helper
    now = time.time()
    prev = last_time[pvname]
    last_time[pvname] = now
    if prev is not None:
        dt = now - prev
        with open(results_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([pvname, dt])


def main():
    parser = argparse.ArgumentParser(description="Latency monitor for EPICS CA/PVA")
    parser.add_argument("--protocol", choices=["ca", "pva"], default="ca", help="EPICS protocol (default: ca)")
    args = parser.parse_args()

    monitors, backend = create_monitors(CAMERA_PVS, args.protocol, on_update)
    print(f"Latency monitor started using protocol: {args.protocol.upper()}. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopped latency monitor.")
    finally:
        cleanup_monitors(monitors, backend)


if __name__ == "__main__":
    main()
