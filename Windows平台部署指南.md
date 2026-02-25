# 🖥️ Windows 本地语音输入部署指南

## （micromamba + 清华源 + GPU/CPU 自适应）

---

## 🎯 目标

在一台 **全新 Windows 电脑** 上完成：

- 使用 `micromamba` 管理 Python 环境（避免系统 Python 3.13 坑）
- `mamba` 永久使用 **清华源**
- `pip` 永久使用 **清华源**
- 避免 OneDrive 锁文件问题
- GPU 可用且显存 ≥ 4GB 时自动使用 CUDA 推理
- 小显存 GPU（如 T400 2GB）自动回退 CPU 推理
- 支持本地语音输入（SenseVoiceSmall）

---

# 一、安装 micromamba（不要放 OneDrive）

### 1️⃣ 下载

打开 PowerShell：

```powershell
Invoke-WebRequest -Uri https://micro.mamba.pm/api/micromamba/win-64/latest -OutFile micromamba.tar.bz2
tar xf micromamba.tar.bz2
```

### 2️⃣ 放到固定工具目录（推荐）

```powershell
New-Item -ItemType Directory -Force -Path "C:\Users\$env:USERNAME\Tools\micromamba" | Out-Null
Move-Item -Force ".\Library\bin\micromamba.exe" "C:\Users\$env:USERNAME\Tools\micromamba\micromamba.exe"
```

### 3️⃣ 加入 PATH（永久）

```powershell
$mmDir = "C:\Users\$env:USERNAME\Tools\micromamba"
$userPath = [Environment]::GetEnvironmentVariable("Path","User")
if (($userPath -split ';') -notcontains $mmDir) {
  [Environment]::SetEnvironmentVariable("Path", ($userPath.TrimEnd(';') + ";" + $mmDir), "User")
}
```

关闭 PowerShell，重新打开。验证：

```powershell
micromamba --version
```

---

# 二、初始化 micromamba

> ⚠️ root 环境不要放 OneDrive

```powershell
$Env:MAMBA_ROOT_PREFIX="$HOME\micromamba"
micromamba shell init -s powershell -r "$HOME\micromamba"
```

关闭 PowerShell，再打开。验证：

```powershell
micromamba info
```

---

# 三、设置 mamba 永久清华源

创建用户级 `.condarc`：

```powershell
notepad $HOME\.condarc
```

粘贴以下内容（UTF-8 编码，无 Tab）：

```yaml
channels:
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge

show_channel_urls: true
channel_priority: flexible
```

验证：

```powershell
micromamba config sources
micromamba config list
```

---

# 四、设置 pip 永久清华源

```powershell
mkdir $HOME\AppData\Roaming\pip -Force
notepad $HOME\AppData\Roaming\pip\pip.ini
```

粘贴以下内容：

```ini
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
timeout = 60
```

验证：

```powershell
pip config list
```

---

# 五、创建项目环境（避免 Python 3.13）

```powershell
micromamba create -n winvoice python=3.11 -y
micromamba activate winvoice
python --version
```

---

# 六、升级 pip 工具链（避免 Windows 编译炸锅）

```powershell
python -m pip install -U pip setuptools wheel
```

作用：

| 工具 | 作用 |
|------|------|
| pip | 包管理器 |
| setuptools | 编译支持 |
| wheel | 预编译安装支持 |

避免出现：

```
Failed building wheel
subprocess-exited-with-error
```

---

# 七、安装 PyTorch（根据 GPU 情况选择）

先检查 GPU：

```powershell
nvidia-smi
```

## 🟢 大显存 GPU（≥4GB，如 RTX 3060/4070）

安装 GPU 版 PyTorch：

```powershell
pip uninstall -y torch torchvision torchaudio
micromamba install pytorch pytorch-cuda=12.1 torchvision torchaudio -c pytorch -c nvidia -y
```

验证：

```python
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

## 🟡 无 GPU 或小显存 GPU（如 NVIDIA T400 2GB）

直接安装 CPU 版（pip 默认就是 CPU 版）：

```powershell
pip install torch torchvision torchaudio
```

> 💡 不需要手动改代码。`config.py` 中 `DEVICE = "auto"` 会自动检测：
> - 有 CUDA 且显存 ≥ 4GB → 使用 GPU
> - 显存 < 4GB 或无 CUDA → 自动回退 CPU
>
> 启动时会打印实际使用的设备，例如：
> ```
> [设备] 检测到 GPU: NVIDIA T400（显存 2.0GB）
> [设备] 显存 < 4GB，回退 CPU（避免 OOM）
> [模型] 正在加载 iic/SenseVoiceSmall（设备: cpu，首次需下载~400MB）...
> ```

---

# 八、安装项目依赖

```powershell
cd 项目目录
pip install -r requirements.txt
```

---

# 九、运行

```powershell
micromamba activate winvoice
python -m sensetype
```

> ⚠️ 需要以**管理员权限**运行 PowerShell（`keyboard` 库捕获全局热键需要）

---

# ⚠️ 避坑总结

| 问题 | 解决 |
|------|------|
| Python 3.13 兼容性差 | 使用 Python 3.11 |
| OneDrive 锁文件 | micromamba root 不放 OneDrive |
| GPU 小显存 OOM | `DEVICE = "auto"` 自动回退 CPU |
| mamba 下载慢 | `.condarc` 配清华源 |
| pip 下载慢 | `pip.ini` 配清华源 |
| 编译失败 | 先升级 pip + setuptools + wheel |

---

# ✅ 最终运行方式

```powershell
micromamba activate winvoice
python -m sensetype
```
