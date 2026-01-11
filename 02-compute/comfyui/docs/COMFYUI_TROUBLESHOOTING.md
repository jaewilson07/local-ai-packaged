# ComfyUI Troubleshooting Guide

This guide provides comprehensive troubleshooting steps for ComfyUI issues.

## Quick Diagnostic Scripts

### 1. Comprehensive Diagnostics
Run the full diagnostic script to check all aspects of your ComfyUI installation:

```bash
./comfyui_diagnostics.sh
```

This checks:
- ✅ Python environment & dependencies
- ✅ PyTorch & CUDA status
- ✅ ComfyUI version & status
- ✅ Resource usage (CPU/GPU/RAM)
- ✅ Custom nodes analysis
- ✅ Models availability
- ✅ Logs analysis
- ✅ Network connectivity

### 2. PyTorch & CUDA Verification
Verify PyTorch and CUDA are working correctly:

```bash
./verify_pytorch_cuda.sh
```

### 3. Update ComfyUI
Update ComfyUI to the latest version:

```bash
./update_comfyui.sh
```

### 4. Custom Nodes Troubleshooting
Diagnose and fix custom node issues:

```bash
# List all nodes and their status
./fix_custom_nodes.sh

# Disable a problematic node
./fix_custom_nodes.sh disable <node_name>

# Enable a disabled node
./fix_custom_nodes.sh enable <node_name>

# Disable all nodes (for testing)
./fix_custom_nodes.sh disable-all
```

## Common Issues & Solutions

### 1. ComfyUI/Environment Problems

#### Update ComfyUI
```bash
# Method 1: Use the update script
./update_comfyui.sh

# Method 2: Manual update
docker exec comfyui-supervisor-1 /opt/ai-dock/bin/update-comfyui.sh

# Method 3: Manual git update
docker exec comfyui-supervisor-1 bash -c "cd /opt/ComfyUI && git pull"
docker exec comfyui-supervisor-1 /opt/environments/python/comfyui/bin/python -m pip install -r /opt/ComfyUI/requirements.txt --upgrade
```

#### Check Logs
```bash
# Recent errors
docker logs comfyui-supervisor-1 | grep -i error | tail -20

# ComfyUI specific logs
docker exec comfyui-supervisor-1 tail -50 /var/log/supervisor/comfyui.log

# All logs
docker logs comfyui-supervisor-1
```

#### Resource Exhaustion
Monitor resources:
```bash
# GPU usage
docker exec comfyui-supervisor-1 nvidia-smi

# Container stats
docker stats comfyui-supervisor-1

# System memory
docker exec comfyui-supervisor-1 free -h
```

#### Python Environment Issues
```bash
# Check Python version
docker exec comfyui-supervisor-1 /opt/environments/python/comfyui/bin/python --version

# Check installed packages
docker exec comfyui-supervisor-1 /opt/environments/python/comfyui/bin/python -m pip list

# Check for package conflicts
docker exec comfyui-supervisor-1 /opt/environments/python/comfyui/bin/python -m pip check

# Reinstall dependencies
docker exec comfyui-supervisor-1 /opt/environments/python/comfyui/bin/python -m pip install -r /opt/ComfyUI/requirements.txt --upgrade
```

### 2. Custom Nodes/Models

#### Missing Nodes
Some custom nodes require additional installation:

```bash
# Check if node has requirements.txt
docker exec comfyui-supervisor-1 ls /opt/ComfyUI/custom_nodes/<node_name>/requirements.txt

# Install node dependencies
docker exec comfyui-supervisor-1 /opt/environments/python/comfyui/bin/python -m pip install -r /opt/ComfyUI/custom_nodes/<node_name>/requirements.txt

# Check if node has install.py
docker exec comfyui-supervisor-1 ls /opt/ComfyUI/custom_nodes/<node_name>/install.py

# Run install script
docker exec comfyui-supervisor-1 /opt/environments/python/comfyui/bin/python /opt/ComfyUI/custom_nodes/<node_name>/install.py
```

#### Missing Models
```bash
# Check model directories
docker exec comfyui-supervisor-1 ls -lh /opt/ComfyUI/models/checkpoints/
docker exec comfyui-supervisor-1 ls -lh /opt/ComfyUI/models/controlnet/
docker exec comfyui-supervisor-1 ls -lh /opt/ComfyUI/models/vae/

# Refresh ComfyUI (restart service)
docker exec comfyui-supervisor-1 supervisorctl restart comfyui
```

#### Node Conflicts
```bash
# Disable all nodes to test
./fix_custom_nodes.sh disable-all

# Then enable one by one to find the problematic node
./fix_custom_nodes.sh enable <node_name>
docker exec comfyui-supervisor-1 supervisorctl restart comfyui
```

### 3. GPU Issues

#### Check GPU Availability
```bash
# In Python
docker exec comfyui-supervisor-1 /opt/environments/python/comfyui/bin/python -c "import torch; print(torch.cuda.is_available())"

# Using nvidia-smi
docker exec comfyui-supervisor-1 nvidia-smi

# Full verification
./verify_pytorch_cuda.sh
```

#### Update Drivers
On the host system (not in container):
```bash
# Check current driver
nvidia-smi

# Update drivers (Ubuntu/Debian)
sudo apt update
sudo apt install nvidia-driver-<version>
sudo reboot
```

## Quick Fix Steps

### Step 1: Run Update Script
```bash
./update_comfyui.sh
```

### Step 2: Check GPU
```bash
./verify_pytorch_cuda.sh
```

### Step 3: Check Logs for Errors
```bash
docker logs comfyui-supervisor-1 | grep -i error | tail -30
```

### Step 4: Temporarily Disable Custom Nodes
```bash
# Disable all
./fix_custom_nodes.sh disable-all

# Restart ComfyUI
docker exec comfyui-supervisor-1 supervisorctl restart comfyui

# If ComfyUI works, enable nodes one by one
./fix_custom_nodes.sh enable <node_name>
```

### Step 5: Reinstall Dependencies
```bash
docker exec comfyui-supervisor-1 /opt/environments/python/comfyui/bin/python -m pip install -r /opt/ComfyUI/requirements.txt --upgrade --force-reinstall
```

### Step 6: Restart Services
```bash
# Restart ComfyUI
docker exec comfyui-supervisor-1 supervisorctl restart comfyui

# Restart entire container
docker restart comfyui-supervisor-1
```

## Service Management

### ComfyUI Service Commands
```bash
# Status
docker exec comfyui-supervisor-1 supervisorctl status comfyui

# Start
docker exec comfyui-supervisor-1 supervisorctl start comfyui

# Stop
docker exec comfyui-supervisor-1 supervisorctl stop comfyui

# Restart
docker exec comfyui-supervisor-1 supervisorctl restart comfyui

# View logs
docker exec comfyui-supervisor-1 tail -f /var/log/supervisor/comfyui.log
```

### Container Management
```bash
# Start container
docker-compose up -d

# Stop container
docker-compose down

# Restart container
docker restart comfyui-supervisor-1

# View logs
docker logs -f comfyui-supervisor-1
```

## Useful Commands Reference

```bash
# Enter container shell
docker exec -it comfyui-supervisor-1 bash

# Check ComfyUI version
docker exec comfyui-supervisor-1 bash -c "cd /opt/ComfyUI && git log -1 --oneline"

# Check Python packages
docker exec comfyui-supervisor-1 /opt/environments/python/comfyui/bin/python -m pip list

# Check port accessibility
curl http://localhost:8188

# Monitor resource usage
watch -n 1 'docker stats comfyui-supervisor-1 --no-stream'
```

## Getting Help

If issues persist:
1. Run `./comfyui_diagnostics.sh` and save the output
2. Check logs: `docker logs comfyui-supervisor-1 > comfyui_logs.txt`
3. Check ComfyUI logs: `docker exec comfyui-supervisor-1 cat /var/log/supervisor/comfyui.log > comfyui_service_logs.txt`
4. Include system info: `./verify_pytorch_cuda.sh > pytorch_info.txt`
