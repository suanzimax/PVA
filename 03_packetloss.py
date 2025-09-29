import time
import csv
import os
import argparse
from config import CAMERA_PVS, RESULTS_DIR
from client_utils import create_monitors, cleanup_monitors

os.makedirs(RESULTS_DIR, exist_ok=True)
results_file = os.path.join(RESULTS_DIR, "packetloss.csv")

with open(results_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["pv", "total_frames", "lost_frames", "loss_rate_percent"])

last_time = {pv: None for pv in CAMERA_PVS}
frame_count = {pv: 0 for pv in CAMERA_PVS}
lost_count = {pv: 0 for pv in CAMERA_PVS}


def on_update(pvname, value, timestamp):
    now = time.time()
    frame_count[pvname] += 1
    prev = last_time[pvname]
    last_time[pvname] = now
    if prev is not None:
        dt = now - prev
        avg_dt = 0.05  # 目标平均帧间隔 (20 FPS)
        if dt > 2 * avg_dt:
            lost_count[pvname] += max(int(dt / avg_dt) - 1, 0)


def main():
    parser = argparse.ArgumentParser(description="Packet loss monitor for EPICS CA/PVA")
    parser.add_argument("--protocol", choices=["ca", "pva"], default="ca")
    parser.add_argument("--avg-dt", type=float, default=0.05, help="假设平均帧间隔 (秒)，默认 0.05 (20FPS)")
    parser.add_argument("--report-interval", type=int, default=10, help="统计写入间隔秒数 (默认10)")
    args = parser.parse_args()

    # allow dynamic avg_dt per run by closing over variable
    def update_with_avg(pvname, value, timestamp):
        global last_time, frame_count, lost_count
        now = time.time()
        frame_count[pvname] += 1
        prev = last_time[pvname]
        last_time[pvname] = now
        if prev is not None:
            dt = now - prev
            if dt > 2 * args.avg_dt:
                lost_count[pvname] += max(int(dt / args.avg_dt) - 1, 0)

    monitors, backend = create_monitors(CAMERA_PVS, args.protocol, update_with_avg)
    print(f"Packet loss monitor started using protocol: {args.protocol.upper()}. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(args.report_interval)
            with open(results_file, "a", newline="") as f:
                writer = csv.writer(f)
                for pv in CAMERA_PVS:
                    total = frame_count[pv]
                    lost = lost_count[pv]
                    loss_rate = (lost / total * 100) if total > 0 else 0
                    writer.writerow([pv, total, lost, loss_rate])
    except KeyboardInterrupt:
        print("Stopped packet loss monitor.")
    finally:
        cleanup_monitors(monitors, backend)


if __name__ == "__main__":
    main()
