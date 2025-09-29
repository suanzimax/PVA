import time
import csv
import os
import argparse
import threading
import psutil
from config import CAMERA_PVS, RESULTS_DIR
from client_utils import create_monitors, cleanup_monitors

os.makedirs(RESULTS_DIR, exist_ok=True)

class StressTestMonitor:
    def __init__(self):
        self.update_count = 0
        self.total_data_size = 0
        self.start_time = time.time()
        self.last_update_time = time.time()
        self.max_interval = 0
        self.min_interval = float('inf')
        self.intervals = []
        self.cpu_data = []
        self.memory_data = []
        
    def on_update(self, pvname, value, timestamp):
        """高强度PV更新处理"""
        now = time.time()
        
        # 计算帧间隔
        if self.last_update_time is not None:
            interval = now - self.last_update_time
            self.intervals.append(interval)
            self.max_interval = max(self.max_interval, interval)
            self.min_interval = min(self.min_interval, interval)
        
        self.last_update_time = now
        self.update_count += 1
        
        # 计算数据大小（压力测试关键指标）
        data_size = 0
        if hasattr(value, 'nbytes'):
            data_size = value.nbytes
        elif hasattr(value, '__len__'):
            data_size = len(value) * 4  # 假设4字节per element
        
        self.total_data_size += data_size
        
        # 模拟数据处理负载（增加CPU压力）
        if data_size > 0:
            # 简单的数据处理操作
            try:
                if hasattr(value, 'mean'):
                    _ = value.mean()  # 计算平均值
                elif hasattr(value, '__iter__'):
                    _ = sum(value[:100])  # 部分求和
            except Exception:
                pass
    
    def monitor_resources(self, duration, interval=0.5):
        """监控系统资源使用情况"""
        end_time = time.time() + duration
        
        while time.time() < end_time:
            try:
                cpu_percent = psutil.cpu_percent(interval=None)
                memory_info = psutil.virtual_memory()
                
                self.cpu_data.append({
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_info.percent,
                    'memory_used_mb': memory_info.used / 1024 / 1024,
                    'update_count': self.update_count,
                    'total_data_mb': self.total_data_size / 1024 / 1024
                })
                
                time.sleep(interval)
            except Exception as e:
                print(f"Resource monitoring error: {e}")
                break
    
    def get_statistics(self):
        """获取压力测试统计信息"""
        elapsed = time.time() - self.start_time
        avg_interval = sum(self.intervals) / len(self.intervals) if self.intervals else 0
        
        return {
            'total_updates': self.update_count,
            'elapsed_time': elapsed,
            'avg_update_rate': self.update_count / elapsed if elapsed > 0 else 0,
            'total_data_mb': self.total_data_size / 1024 / 1024,
            'avg_throughput_mbps': (self.total_data_size / 1024 / 1024) / elapsed if elapsed > 0 else 0,
            'avg_interval': avg_interval,
            'max_interval': self.max_interval if self.max_interval != 0 else 0,
            'min_interval': self.min_interval if self.min_interval != float('inf') else 0,
            'interval_stddev': self._calculate_stddev(self.intervals)
        }
    
    def _calculate_stddev(self, values):
        if len(values) < 2:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

def main():
    parser = argparse.ArgumentParser(description="Stress test for EPICS CA/PVA")
    parser.add_argument("--protocol", choices=["ca", "pva"], default="ca",
                       help="EPICS protocol (default: ca)")
    parser.add_argument("--duration", type=int, default=60,
                       help="Test duration in seconds (default: 60)")
    
    args = parser.parse_args()
    
    print(f"Starting stress test:")
    print(f"  Protocol: {args.protocol.upper()}")
    print(f"  Duration: {args.duration} seconds")
    print(f"  Monitoring PVs: {len(CAMERA_PVS)}")
    for pv in CAMERA_PVS:
        print(f"    - {pv}")
    
    # 创建压力测试监控器
    stress_monitor = StressTestMonitor()
    
    # 启动PV监控（高负载）
    try:
        monitors, backend = create_monitors(CAMERA_PVS, args.protocol, stress_monitor.on_update)
        print(f"Monitors created successfully using {args.protocol.upper()}")
        
        # 启动资源监控线程
        resource_thread = threading.Thread(
            target=stress_monitor.monitor_resources,
            args=(args.duration,),
            daemon=True
        )
        resource_thread.start()
        
        print("Stress test running... Press Ctrl+C to stop early")
        
        # 运行压力测试
        time.sleep(args.duration)
        
    except KeyboardInterrupt:
        print("\nStopping stress test...")
    except Exception as e:
        print(f"Error during stress test: {e}")
    finally:
        cleanup_monitors(monitors, backend)
    
    # 获取统计信息
    stats = stress_monitor.get_statistics()
    
    # 保存结果
    results_file = os.path.join(RESULTS_DIR, "stress_test.csv")
    with open(results_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for key, value in stats.items():
            writer.writerow([key, value])
    
    # 保存CPU监控数据
    cpu_file = os.path.join(RESULTS_DIR, "stress_cpu.csv")
    with open(cpu_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "cpu_percent", "memory_percent", "memory_used_mb", "update_count", "total_data_mb"])
        for data in stress_monitor.cpu_data:
            writer.writerow([
                data['timestamp'], data['cpu_percent'], data['memory_percent'],
                data['memory_used_mb'], data['update_count'], data['total_data_mb']
            ])
    
    # 打印结果
    print(f"\nStress Test Results:")
    print(f"  Total updates: {stats['total_updates']}")
    print(f"  Average update rate: {stats['avg_update_rate']:.2f} Hz")
    print(f"  Total data processed: {stats['total_data_mb']:.2f} MB")
    print(f"  Average throughput: {stats['avg_throughput_mbps']:.2f} MB/s")
    print(f"  Average interval: {stats['avg_interval']:.4f} s")
    print(f"  Max interval: {stats['max_interval']:.4f} s")
    print(f"  Min interval: {stats['min_interval']:.4f} s")
    print(f"  Interval std dev: {stats['interval_stddev']:.4f} s")
    print(f"Results saved to: {results_file}")
    print(f"CPU data saved to: {cpu_file}")

if __name__ == "__main__":
    main()