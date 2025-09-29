import time
import csv
import os
import argparse
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import CAMERA_PVS, RESULTS_DIR
from client_utils import create_monitors, cleanup_monitors
import psutil

os.makedirs(RESULTS_DIR, exist_ok=True)

# 全局队列存储测试结果
result_queue = queue.Queue()

class ConcurrentClient:
    """并发客户端类，用于模拟多个客户端同时访问PV"""
    
    def __init__(self, client_id, pv_list, protocol):
        self.client_id = client_id
        self.pv_list = pv_list
        self.protocol = protocol
        self.monitors = []
        self.backend = None
        self.data_count = 0
        self.start_time = time.time()
        self.last_update_time = time.time()
        
    def on_update(self, pvname, value, timestamp):
        """PV更新回调函数"""
        now = time.time()
        self.data_count += 1
        self.last_update_time = now
        
        # 计算数据大小（估算）
        data_size = 0
        if hasattr(value, 'nbytes'):
            data_size = value.nbytes
        elif hasattr(value, '__len__'):
            data_size = len(value) * 4  # 假设4字节per element
        
        # 记录结果
        result_queue.put({
            'client_id': self.client_id,
            'pvname': pvname,
            'timestamp': now,
            'data_size': data_size,
            'data_count': self.data_count
        })
    
    def start_monitoring(self):
        """启动监控"""
        try:
            self.monitors, self.backend = create_monitors(
                self.pv_list, self.protocol, self.on_update
            )
            return True
        except Exception as e:
            print(f"Client {self.client_id} failed to start: {e}")
            return False
    
    def stop_monitoring(self):
        """停止监控"""
        try:
            cleanup_monitors(self.monitors, self.backend)
        except Exception as e:
            print(f"Client {self.client_id} cleanup error: {e}")
    
    def get_stats(self):
        """获取客户端统计信息"""
        elapsed = self.last_update_time - self.start_time
        return {
            'client_id': self.client_id,
            'data_count': self.data_count,
            'elapsed_time': elapsed,
            'avg_rate': self.data_count / elapsed if elapsed > 0 else 0
        }

def run_client(client_id, pv_list, protocol, duration):
    """运行单个并发客户端"""
    client = ConcurrentClient(client_id, pv_list, protocol)
    
    if not client.start_monitoring():
        return None
    
    print(f"Client {client_id} started monitoring {len(pv_list)} PVs")
    
    try:
        time.sleep(duration)
    except KeyboardInterrupt:
        pass
    finally:
        client.stop_monitoring()
    
    return client.get_stats()

def monitor_system_resources(duration, interval=1.0):
    """监控系统资源使用情况"""
    cpu_data = []
    memory_data = []
    
    start_time = time.time()
    while time.time() - start_time < duration:
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
            memory_info = psutil.virtual_memory()
            
            cpu_data.append({
                'timestamp': time.time(),
                'cpu_percent': cpu_percent,
                'memory_percent': memory_info.percent,
                'memory_used_mb': memory_info.used / 1024 / 1024
            })
            
            time.sleep(interval)
        except KeyboardInterrupt:
            break
    
    return cpu_data

def main():
    parser = argparse.ArgumentParser(description="Concurrent test for EPICS CA/PVA")
    parser.add_argument("--protocol", choices=["ca", "pva"], default="ca", 
                       help="EPICS protocol (default: ca)")
    parser.add_argument("--clients", type=int, default=5, 
                       help="Number of concurrent clients (default: 5)")
    parser.add_argument("--duration", type=int, default=60, 
                       help="Test duration in seconds (default: 60)")
    parser.add_argument("--pv-per-client", type=int, default=0,
                       help="PVs per client (0 = all PVs per client)")
    
    args = parser.parse_args()
    
    print(f"Starting concurrent test:")
    print(f"  Protocol: {args.protocol.upper()}")
    print(f"  Concurrent clients: {args.clients}")
    print(f"  Duration: {args.duration} seconds")
    print(f"  Total PVs: {len(CAMERA_PVS)}")
    
    # 分配PV给各个客户端
    if args.pv_per_client > 0:
        pv_per_client = min(args.pv_per_client, len(CAMERA_PVS))
        client_pvs = []
        for i in range(args.clients):
            start_idx = (i * pv_per_client) % len(CAMERA_PVS)
            end_idx = min(start_idx + pv_per_client, len(CAMERA_PVS))
            client_pvs.append(CAMERA_PVS[start_idx:end_idx])
    else:
        # 所有客户端监控所有PV
        client_pvs = [CAMERA_PVS] * args.clients
    
    # 启动系统资源监控线程
    resource_thread = threading.Thread(
        target=lambda: monitor_system_resources(args.duration),
        daemon=True
    )
    resource_thread.start()
    
    # 使用线程池运行并发客户端
    client_stats = []
    with ThreadPoolExecutor(max_workers=args.clients) as executor:
        # 提交所有客户端任务
        futures = {
            executor.submit(run_client, i, client_pvs[i], args.protocol, args.duration): i
            for i in range(args.clients)
        }
        
        try:
            # 等待所有任务完成
            for future in as_completed(futures):
                client_id = futures[future]
                try:
                    stats = future.result()
                    if stats:
                        client_stats.append(stats)
                        print(f"Client {client_id} completed: {stats['data_count']} updates, "
                              f"avg rate: {stats['avg_rate']:.2f} Hz")
                except Exception as e:
                    print(f"Client {client_id} failed: {e}")
        
        except KeyboardInterrupt:
            print("\nStopping concurrent test...")
            # 等待当前任务完成
            for future in futures:
                future.cancel()
    
    # 保存结果
    results_file = os.path.join(RESULTS_DIR, "concurrent_test.csv")
    
    # 保存客户端统计信息
    with open(results_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["client_id", "data_count", "elapsed_time", "avg_rate_hz"])
        for stats in client_stats:
            writer.writerow([
                stats['client_id'],
                stats['data_count'],
                stats['elapsed_time'],
                stats['avg_rate']
            ])
    
    # 保存详细数据记录
    detail_file = os.path.join(RESULTS_DIR, "concurrent_detail.csv")
    with open(detail_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["client_id", "pvname", "timestamp", "data_size", "data_count"])
        
        # 处理队列中的所有结果
        while not result_queue.empty():
            try:
                result = result_queue.get_nowait()
                writer.writerow([
                    result['client_id'],
                    result['pvname'],
                    result['timestamp'],
                    result['data_size'],
                    result['data_count']
                ])
            except queue.Empty:
                break
    
    # 打印总结
    if client_stats:
        total_updates = sum(s['data_count'] for s in client_stats)
        avg_rate_per_client = sum(s['avg_rate'] for s in client_stats) / len(client_stats)
        
        print(f"\nConcurrent Test Summary:")
        print(f"  Total updates received: {total_updates}")
        print(f"  Average rate per client: {avg_rate_per_client:.2f} Hz")
        print(f"  Results saved to: {results_file}")
        print(f"  Detailed data saved to: {detail_file}")
    
    print("Concurrent test completed.")

if __name__ == "__main__":
    main()