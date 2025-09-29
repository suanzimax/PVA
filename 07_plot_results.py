import os
import pandas as pd
import matplotlib.pyplot as plt
from config import RESULTS_DIR

os.makedirs(RESULTS_DIR, exist_ok=True)

# 延迟
try:
    df = pd.read_csv(os.path.join(RESULTS_DIR, "latency.csv"))
    plt.figure()
    for pv, g in df.groupby("pv"):
        plt.plot(g["frame_interval_sec"].values, label=pv)
    plt.title("Frame Interval (Latency Approx)")
    plt.xlabel("Frame Index")
    plt.ylabel("Interval (s)")
    plt.legend()
    plt.savefig(os.path.join(RESULTS_DIR, "latency.png"))
except Exception as e:
    print("Latency plot error:", e)

# 吞吐量
try:
    df = pd.read_csv(os.path.join(RESULTS_DIR, "throughput.csv"))
    plt.figure()
    for pv, g in df.groupby("pv"):
        plt.plot(g["mb_per_sec"].values, label=pv)
    plt.title("Throughput (MB/s)")
    plt.xlabel("Interval Index")
    plt.ylabel("MB/s")
    plt.legend()
    plt.savefig(os.path.join(RESULTS_DIR, "throughput.png"))
except Exception as e:
    print("Throughput plot error:", e)

# 丢包率
try:
    df = pd.read_csv(os.path.join(RESULTS_DIR, "packetloss.csv"))
    plt.figure()
    plt.bar(df["pv"], df["loss_rate_percent"])
    plt.title("Packet Loss Rate")
    plt.ylabel("Loss Rate (%)")
    plt.xticks(rotation=90)
    plt.savefig(os.path.join(RESULTS_DIR, "packetloss.png"))
except Exception as e:
    print("Packet loss plot error:", e)

# CPU
try:
    df = pd.read_csv(os.path.join(RESULTS_DIR, "cpu.csv"))
    plt.figure()
    plt.plot(df["cpu_percent"], label="CPU %")
    plt.plot(df["memory_percent"], label="Memory %")
    plt.title("CPU and Memory Usage")
    plt.xlabel("Time Index")
    plt.ylabel("Usage (%)")
    plt.legend()
    plt.savefig(os.path.join(RESULTS_DIR, "cpu.png"))
except Exception as e:
    print("CPU plot error:", e)

print("Plots saved in results/ folder.")
