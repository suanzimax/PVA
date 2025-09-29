<!-- # EPICS CA/PVA 相机协议性能测试（基于 IMAGE PV）

## 简介
本测试方案用于对多台 Mindvision 相机在 EPICS 环境下（CA/PVA 协议）进行性能评估。
假设每台相机 IOC 只提供 `CAM:XX:IMAGE` PV（数组），没有单独的时间戳和帧号 PV。

测试内容：
- 延迟（帧间隔近似）
- 吞吐量（MB/s）
- 丢包率（基于帧间隔异常）
- CPU 占用

## 环境依赖
基础依赖（均需要）：
```bash
pip install pyepics p4p numpy pandas matplotlib psutil
```

如果暂时只做 CA 测试，可不安装 `p4p`。在 Windows 上安装 `p4p` 可能需要 EPICS Base 支持；若安装失败，可先进行 CA 测试，或在 Linux 环境执行 PVA 测试。

## 使用方法
1. 修改 `config.py`（或 `05_config.py`，二选一保持一致），将 `CAMERA_PVS` 替换为现场的 20+ 相机 PV 名称。
2. 运行单独脚本（默认 CA）：
   ```bash
   python3 01_latency_monitor.py
   ```
   指定 PVA：
   ```bash
   python3 01_latency_monitor.py --protocol pva
   ```
3. 或运行一键脚本（传入协议 `ca` 或 `pva`）：
   ```bash
   bash 06_run_all.sh pva   # 或省略参数默认 ca
   ```
   Windows PowerShell:
   ```powershell
   ./06_run_all.ps1 -Protocol pva
   ```
4. 停止测试后运行：
   ```bash
   python3 07_plot_results.py
   ```
   在 `results/` 文件夹下生成图表。

## 输出结果
- `results/latency.csv` + `latency.png`
- `results/throughput.csv` + `throughput.png`
- `results/packetloss.csv` + `packetloss.png`
- `results/cpu.csv` + `cpu.png`

## 注意事项
- 延迟计算基于客户端帧间隔，不是严格的端到端延迟。
- 丢包率通过帧间隔 > 2×设定平均帧间隔判断（默认 20FPS => 0.05s）。
- 通过 `03_packetloss.py --avg-dt 0.0333` 可调整为 30FPS 等其他帧率。
- PVA 回调中已尝试提取 timeStamp，如未成功则使用本地 `time.time()`。
- 相机 PV 数量较多时，建议分批测试，避免单机过载；PVA 与 CA 同时大量监视时需评估网络与 IOC 负载。
- 若使用 PVA 且 PV 名称需要前缀（如 `pva://`），请在 `05_config.py` 中直接写完整名称。 -->






# EPICS CA/PVA 相机协议性能测试（基于 IMAGE PV）

## 简介
本测试方案用于对多台 Mindvision 相机在 EPICS 环境下（CA/PVA 协议）进行性能评估。
假设每台相机 IOC 只提供 `CAM:XX:IMAGE` PV（数组），没有单独的时间戳和帧号 PV。

测试内容：
- 延迟（帧间隔近似）
- 吞吐量（MB/s）
- 丢包率（基于帧间隔异常）
- 压力测试
- 并发测试
- CPU 占用

## 环境依赖
基础依赖（均需要）：
```bash
pip install pyepics p4p numpy pandas matplotlib psutil
```

如果暂时只做 CA 测试，可不安装 `p4p`。在 Windows 上安装 `p4p` 可能需要 EPICS Base 支持；若安装失败，可先进行 CA 测试，或在 Linux 环境执行 PVA 测试。

## 配置文件
- `config.py` - 相机PV列表和结果目录配置
- `client_utils.py` - 通用客户端工具函数，支持CA/PVA协议切换

## 测试脚本详细说明

### 01_latency_monitor.py - 延迟监控测试
**作用**: 监控相机帧间隔，计算延迟性能
**执行方法**:
```bash
# CA协议延迟测试（默认）
python 01_latency_monitor.py

# CA协议延迟测试（显式指定）
python 01_latency_monitor.py --protocol ca

# PVA协议延迟测试
python 01_latency_monitor.py --protocol pva
```
**输出**: `results/latency.csv` - 包含每个PV的帧间隔数据

### 02_throughput.py - 吞吐量测试
**作用**: 测量数据传输吞吐量（MB/s）
**执行方法**:
```bash
# CA协议吞吐量测试
python 02_throughput.py --protocol ca

# PVA协议吞吐量测试
python 02_throughput.py --protocol pva
```
**输出**: `results/throughput.csv` - 包含吞吐量统计数据

### 03_packetloss.py - 丢包率测试
**作用**: 基于帧间隔异常检测丢包情况
**执行方法**:
```bash
# CA协议丢包测试（默认20FPS，帧间隔0.05s）
python 03_packetloss.py --protocol ca

# PVA协议丢包测试
python 03_packetloss.py --protocol pva

# 自定义帧率（30FPS示例）
python 03_packetloss.py --protocol ca --avg-dt 0.0333
```
**输出**: `results/packetloss.csv` - 包含丢包统计数据

### 04_stress_test.py - 压力测试
**作用**: 在高负载条件下测试系统稳定性和性能
**执行方法**:
```bash
# CA协议压力测试（默认60秒）
python 04_stress_test.py --protocol ca

# PVA协议压力测试
python 04_stress_test.py --protocol pva

# 指定测试持续时间（120秒）
python 04_stress_test.py --protocol ca --duration 120
```
**输出**: `results/stress_test.csv` - 包含压力测试期间的性能数据

### 05_concurrent_test.py - 并发测试
**作用**: 测试多个并发客户端同时访问相机PV的性能
**执行方法**:
```bash
# CA协议并发测试（默认5个客户端）
python 05_concurrent_test.py --protocol ca

# PVA协议并发测试
python 05_concurrent_test.py --protocol pva

# 指定并发客户端数量（10个）
python 05_concurrent_test.py --protocol ca --clients 10
```
**输出**: `results/concurrent_test.csv` - 包含并发测试性能数据

### 06_run_all - 一键运行所有测试
**作用**: 自动运行完整的测试套件，包括所有测试项目

**Windows PowerShell**:
```powershell
# 运行所有CA协议测试（默认）
./06_run_all.ps1

# 运行所有PVA协议测试
./06_run_all.ps1 -Protocol pva

# 如果权限不足，先执行：
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Linux/macOS Bash**:
```bash
# 给脚本执行权限
chmod +x 06_run_all.sh

# 运行所有CA协议测试（默认）
./06_run_all.sh

# 运行所有PVA协议测试
./06_run_all.sh pva
```

### 07_plot_results.py - 结果可视化
**作用**: 生成测试结果的图表和统计报告
**执行方法**:
```bash
# 生成所有测试结果的图表
python 07_plot_results.py
```
**输出**: 在 `results/` 目录生成以下图表文件：
- `latency.png` - 延迟分析图
- `throughput.png` - 吞吐量分析图
- `packetloss.png` - 丢包率分析图
- `stress_test.png` - 压力测试结果图
- `concurrent_test.png` - 并发测试结果图
- `cpu.png` - CPU占用分析图

## 使用流程

### 快速开始
1. **配置相机PV**：修改 `config.py` 中的 `CAMERA_PVS` 列表
2. **运行完整测试**：
   ```powershell
   # Windows
   ./06_run_all.ps1 -Protocol ca

   # Linux/macOS  
   ./06_run_all.sh ca
   ```
3. **生成报告**：
   ```bash
   python 07_plot_results.py
   ```

### 单独测试
```bash
# 1. 先测试延迟
python 01_latency_monitor.py --protocol ca

# 2. 测试吞吐量  
python 02_throughput.py --protocol ca

# 3. 测试丢包率
python 03_packetloss.py --protocol ca

# 4. 压力测试
python 04_stress_test.py --protocol ca

# 5. 并发测试
python 05_concurrent_test.py --protocol ca

# 6. 生成图表
python 07_plot_results.py
```

## 输出结果
所有测试结果保存在 `results/` 目录：

**CSV数据文件**:
- `latency.csv` - 延迟测试数据
- `throughput.csv` - 吞吐量测试数据  
- `packetloss.csv` - 丢包率测试数据
- `stress_test.csv` - 压力测试数据
- `concurrent_test.csv` - 并发测试数据
- `cpu.csv` - CPU占用数据

**图表文件**:
- `latency.png` - 延迟分析图表
- `throughput.png` - 吞吐量分析图表
- `packetloss.png` - 丢包率分析图表
- `stress_test.png` - 压力测试图表
- `concurrent_test.png` - 并发测试图表
- `cpu.png` - CPU占用图表

## 注意事项
- **延迟计算**: 基于客户端帧间隔，不是严格的端到端延迟
- **丢包判断**: 通过帧间隔 > 2×设定平均帧间隔判断（默认 20FPS => 0.05s）
- **帧率调整**: 通过 `--avg-dt` 参数可调整期望帧间隔时间
- **PVA时间戳**: 回调中已尝试提取 timeStamp，如未成功则使用本地 `time.time()`
- **负载考虑**: 相机PV数量较多时，建议分批测试，避免单机过载
- **网络评估**: PVA与CA同时大量监视时需评估网络与IOC负载
- **PV命名**: 若使用PVA且PV名称需要前缀（如 `pva://`），请在配置文件中写完整名称

## 协议对比
- **CA (Channel Access)**: EPICS传统协议，适用于标量数据和小型数组
- **PVA (Process Variable Access)**: EPICS v4协议，针对大型数据传输优化，更适合图像数据
