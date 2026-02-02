# Linux Cluster Deployment Guide

**Date**: 2026-02-03  
**Purpose**: Step-by-step guide for deploying astraeus with ollama on a Linux GPU cluster

---

## Quick Start (TL;DR)

```bash
# 1. On GPU cluster node
./setup-ollama-cluster.sh

# 2. On your workstation
export OLLAMA_HOST=http://cluster-node:11434
cd ~/my-project
python3 /path/to/astraeus/tools/astraeus load --target . --profile hybrid-cloud-ollama
opencode /init-local
opencode /local-smoke
```

---

## Deployment Scenarios

### Scenario 1: You Have Root Access to Cluster Node

**Best for**: Personal clusters, dev environments

1. **SSH into cluster node**:
```bash
ssh user@cluster-node
```

2. **Clone galaxy-backend**:
```bash
git clone https://github.com/your-org/galaxy-backend.git
cd galaxy-backend
```

3. **Run automated setup**:
```bash
./setup-ollama-cluster.sh
```

This will:
- Check for NVIDIA GPU
- Install ollama (if missing)
- Pull required models (ministral-3, qwen3-coder, lfm2.5-thinking)
- Start ollama service
- Test inference

4. **Configure network access** (if needed):
```bash
# Allow connections from your workstation
sudo ufw allow from YOUR_WORKSTATION_IP to any port 11434

# OR allow entire subnet
sudo ufw allow from 192.168.1.0/24 to any port 11434
```

5. **On your workstation**:
```bash
# Test connection
curl http://cluster-node:11434/api/tags

# Set environment variable
export OLLAMA_HOST=http://cluster-node:11434
echo 'export OLLAMA_HOST=http://cluster-node:11434' >> ~/.bashrc

# Deploy astraeus
cd ~/my-project
python3 /path/to/astraeus/tools/astraeus load --target . --profile hybrid-cloud-ollama

# Verify
opencode /local-smoke
```

---

### Scenario 2: No Root Access (User-Space Deployment)

**Best for**: Shared clusters, HPC environments

1. **Install ollama in user space**:
```bash
# Download ollama binary
curl -L https://ollama.com/download/ollama-linux-amd64 -o ~/bin/ollama
chmod +x ~/bin/ollama

# Start ollama server (custom port)
OLLAMA_HOST=0.0.0.0:11435 ~/bin/ollama serve &

# Verify
curl http://localhost:11435/api/tags
```

2. **Pull models**:
```bash
OLLAMA_HOST=http://localhost:11435 ~/bin/ollama pull ministral-3:14b-32k
OLLAMA_HOST=http://localhost:11435 ~/bin/ollama pull qwen3-coder-32k
OLLAMA_HOST=http://localhost:11435 ~/bin/ollama pull lfm2.5-thinking:latest
```

3. **Keep ollama running** (use screen/tmux):
```bash
# Start tmux session
tmux new -s ollama

# Run ollama
OLLAMA_HOST=0.0.0.0:11435 ~/bin/ollama serve

# Detach: Ctrl+B, then D
```

4. **On your workstation**:
```bash
export OLLAMA_HOST=http://cluster-node:11435
cd ~/my-project
python3 /path/to/astraeus/tools/astraeus load --target . --profile hybrid-cloud-ollama
opencode /init-local
```

---

### Scenario 3: Kubernetes Cluster

**Best for**: Production, multi-tenant environments

1. **Create namespace**:
```bash
kubectl create namespace ai-agents
```

2. **Deploy ollama**:
```bash
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama
  namespace: ai-agents
spec:
  replicas: 2  # Scale based on GPU count
  selector:
    matchLabels:
      app: ollama
  template:
    metadata:
      labels:
        app: ollama
    spec:
      containers:
      - name: ollama
        image: ollama/ollama:latest
        ports:
        - containerPort: 11434
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: 32Gi
          requests:
            nvidia.com/gpu: 1
            memory: 16Gi
        env:
        - name: OLLAMA_HOST
          value: "0.0.0.0:11434"
        volumeMounts:
        - name: models
          mountPath: /root/.ollama
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: ollama-models-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: ollama
  namespace: ai-agents
spec:
  selector:
    app: ollama
  ports:
  - protocol: TCP
    port: 11434
    targetPort: 11434
  type: LoadBalancer
EOF
```

3. **Pull models (init job)**:
```bash
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: ollama-init
  namespace: ai-agents
spec:
  template:
    spec:
      containers:
      - name: init
        image: ollama/ollama:latest
        command:
        - /bin/sh
        - -c
        - |
          ollama pull ministral-3:14b-32k
          ollama pull qwen3-coder-32k
          ollama pull lfm2.5-thinking:latest
        volumeMounts:
        - name: models
          mountPath: /root/.ollama
      restartPolicy: OnFailure
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: ollama-models-pvc
EOF
```

4. **Get LoadBalancer IP**:
```bash
kubectl get svc ollama -n ai-agents
# Note the EXTERNAL-IP
```

5. **On your workstation**:
```bash
export OLLAMA_HOST=http://<EXTERNAL-IP>:11434
cd ~/my-project
python3 /path/to/astraeus/tools/astraeus load --target . --profile hybrid-cloud-ollama
opencode /init-local
```

---

## Network Configuration

### Firewall Rules

**Ubuntu/Debian (ufw)**:
```bash
# Allow from specific IP
sudo ufw allow from 192.168.1.100 to any port 11434

# Allow from subnet
sudo ufw allow from 192.168.1.0/24 to any port 11434

# Check status
sudo ufw status numbered
```

**CentOS/RHEL (firewalld)**:
```bash
# Allow from subnet
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.1.0/24" port protocol="tcp" port="11434" accept'
sudo firewall-cmd --reload

# Check
sudo firewall-cmd --list-all
```

### SSH Tunnel (Most Secure)

If you don't want to expose ollama to network:

```bash
# On your workstation
ssh -L 11434:localhost:11434 user@cluster-node -N -f

# Use local endpoint
export OLLAMA_HOST=http://localhost:11434

# Test
curl http://localhost:11434/api/tags
```

---

## Performance Optimization

### 1. GPU Selection (Multi-GPU Systems)

```bash
# Check available GPUs
nvidia-smi -L

# Run ollama on specific GPU
CUDA_VISIBLE_DEVICES=0 ollama serve

# OR run multiple ollama instances (one per GPU)
CUDA_VISIBLE_DEVICES=0 OLLAMA_HOST=0.0.0.0:11434 ollama serve &
CUDA_VISIBLE_DEVICES=1 OLLAMA_HOST=0.0.0.0:11435 ollama serve &
```

### 2. Concurrency Tuning

Edit `.opencode/profiles/hybrid-cloud-ollama.json`:

```json
{
  "background": {
    "provider_limits": {
      "ollama": 10  // Increase if you have multiple GPUs
    },
    "model_limits": {
      "ollama/ministral-3:14b-32k": 6,  // Adjust based on VRAM
      "ollama/qwen3-coder-32k": 4
    }
  }
}
```

**Guidelines**:
- **8GB VRAM**: `ollama: 2-4`
- **16GB VRAM**: `ollama: 4-8`
- **24GB VRAM**: `ollama: 8-12`
- **Multi-GPU**: `ollama: 10+`

### 3. Model Quantization

**Default** (Q4_K_M): Best balance of speed/quality

**Higher quality** (slower, more VRAM):
```bash
ollama pull ministral-3:14b-fp16
```

**Lower quality** (faster, less VRAM):
```bash
ollama pull ministral-3:14b-q2
```

---

## Monitoring

### GPU Utilization

```bash
# Real-time monitoring
watch -n 1 nvidia-smi

# Or with more details
watch -n 1 'nvidia-smi --query-gpu=index,name,temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.total --format=csv'
```

### Ollama Logs

**Systemd**:
```bash
journalctl -u ollama -f
```

**Manual process**:
```bash
# Find ollama PID
ps aux | grep ollama

# Check logs (if redirected)
tail -f /var/log/ollama.log
```

### astraeus Metrics

```bash
# Session-level metrics
opencode /meta-eval

# Check model distribution (cloud vs local)
grep -E "(ollama|gemini|gpt)" ~/.opencode/sessions/latest/transcript.log
```

---

## Troubleshooting

### Issue: "Connection Refused"

```bash
# Check if ollama is running
systemctl status ollama  # systemd
ps aux | grep ollama     # manual

# Check port
ss -tlnp | grep 11434

# Test locally (on cluster node)
curl http://localhost:11434/api/tags

# Test remotely (from workstation)
curl http://cluster-node:11434/api/tags
```

**Fix**:
```bash
# Restart ollama
sudo systemctl restart ollama

# OR if manual
pkill ollama
OLLAMA_HOST=0.0.0.0:11434 ollama serve &
```

---

### Issue: "CUDA Out of Memory"

```bash
# Check current VRAM usage
nvidia-smi

# Reduce concurrency in profile
# Edit .opencode/oh-my-opencode.json:
"provider_limits": { "ollama": 2 }

# Use smaller models
ollama pull ministral-3:14b  # 8K context (less VRAM)
```

---

### Issue: "Model Not Found"

```bash
# Pull missing models
ollama pull ministral-3:14b-32k
ollama pull qwen3-coder-32k
ollama pull lfm2.5-thinking:latest

# Verify
ollama list
```

---

### Issue: Slow Inference (>10s)

**Causes**:
1. CPU mode (no GPU detected)
2. Swapping to disk (insufficient RAM)
3. Network latency

**Diagnosis**:
```bash
# Check GPU is used
nvidia-smi  # Should show ollama process

# Check RAM
free -h

# Test latency
time curl http://localhost:11434/api/tags  # <100ms is good
```

**Fix**:
```bash
# Force GPU
export CUDA_VISIBLE_DEVICES=0
sudo systemctl restart ollama

# Add more RAM (if swapping)
# OR reduce concurrent requests
```

---

## Security Best Practices

### 1. Network Isolation

```bash
# Use SSH tunnel (most secure)
ssh -L 11434:localhost:11434 user@cluster-node -N -f

# OR restrict firewall
sudo ufw allow from 192.168.1.0/24 to any port 11434
sudo ufw deny 11434
```

### 2. Model Permissions

Never grant ollama agents:
- `webfetch: allow` (data exfiltration risk)
- Full filesystem write access
- Access to `.env`, credentials

**Profiles already enforce this**:
```json
{
  "explore": {
    "permission": {
      "webfetch": "deny",
      "edit": "deny",
      "write": "deny"
    }
  }
}
```

### 3. Resource Limits

**Systemd service** (recommended):
```bash
sudo systemctl edit ollama

# Add:
[Service]
MemoryMax=16G
CPUQuota=400%  # 4 cores
```

**Docker**:
```bash
docker run -d \
  --gpus all \
  --memory=16g \
  --cpus=4 \
  -p 11434:11434 \
  ollama/ollama
```

---

## Maintenance

### Model Updates

```bash
# Check for updates
ollama list

# Update specific model
ollama pull ministral-3:14b-32k

# Verify
ollama run ministral-3:14b-32k "test"
```

### Disk Cleanup

```bash
# Check model storage
du -sh ~/.ollama/models

# Remove unused models
ollama rm old-model-name

# Clear cache
rm -rf ~/.ollama/cache
```

### Backup

```bash
# Backup models (to avoid re-downloading)
tar -czf ollama-models-backup.tar.gz ~/.ollama/models

# Restore
tar -xzf ollama-models-backup.tar.gz -C ~/
```

---

## Next Steps

1. **Deploy to cluster**: Run `./setup-ollama-cluster.sh`
2. **Configure network**: Set up firewall or SSH tunnel
3. **Test connection**: `curl http://cluster-node:11434/api/tags`
4. **Deploy astraeus**: `astraeus load --profile hybrid-cloud-ollama`
5. **Verify**: `opencode /local-smoke`
6. **Start coding**: `opencode` (Sisyphus auto-routes to GPU)

---

## References

- [GPU_CLUSTER_SETUP.md](GPU_CLUSTER_SETUP.md) — Comprehensive hardware/software guide
- [ARCHITECTURE.md](ARCHITECTURE.md) — System architecture overview
- [astraeus docs](../../docs/) — Full documentation

---

**Questions?** Open an issue in the main astraeus repo.
