# astraeus GPU Cluster Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Workstation                        │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ OpenCode CLI (astraeus)                                  │  │
│  │                                                          │  │
│  │  Sisyphus (Orchestrator)                                │  │
│  │       │                                                  │  │
│  │       ├─> TDD Guide ──────────> anthropic/claude-sonnet │  │
│  │       ├─> Code Reviewer ──────> anthropic/claude-sonnet │  │
│  │       ├─> Oracle ──────────────> openai/gpt-5.2         │  │
│  │       ├─> Explore ──────────────> ollama (local/remote) │  │
│  │       ├─> Build Resolver ──────> ollama (local/remote)  │  │
│  │       └─> Document Writer ─────> ollama (local/remote)  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                      │
└──────────────────────────┼──────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│ Anthropic    │  │ OpenAI       │  │ GPU Cluster      │
│ Claude API   │  │ GPT API      │  │                  │
│              │  │              │  │ Ollama Server    │
│ Opus/Sonnet  │  │ GPT-5.2/4o   │  │ :11434           │
│ (Quality)    │  │ (Reasoning)  │  │   ↓              │
└──────────────┘  └──────────────┘  │ GPU Pool (CUDA)  │
                                    │   ↓              │
                                    │ 3 Models:        │
                                    │ - ministral-3    │
                                    │ - qwen3-coder    │
                                    │ - lfm2.5         │
                                    └──────────────────┘
```

## Agent Routing Matrix

### Hybrid-Cloud-Ollama Profile

| Agent | Model | Location | Use Case | Cost |
|-------|-------|----------|----------|------|
| **sisyphus** | openai/gpt-5.2 | Cloud | Orchestration | $$$ |
| **oracle** | openai/gpt-5.2 | Cloud | Deep reasoning | $$$ |
| **tdd-guide** | openai/gpt-4o | Cloud | Quality code | $$ |
| **code-reviewer** | openai/gpt-4o | Cloud | Code review | $$ |
| **security** | openai/gpt-5.2 | Cloud | Security audit | $$$ |
| **explore** | ollama/ministral-3 | **GPU** | Codebase search | **FREE** |
| **build-error-resolver** | ollama/qwen3-coder | **GPU** | Type/lint errors | **FREE** |
| **document-writer** | ollama/lfm2.5 | **GPU** | Doc generation | **FREE** |
| **doc-updater** | ollama/lfm2.5 | **GPU** | Doc sync | **FREE** |
| **refactor-cleaner** | ollama/qwen3-coder | **GPU** | Dead code removal | **FREE** |
| **journalist** | ollama/lfm2.5 | **GPU** | Journal keeping | **FREE** |
| **librarian** | google/gemini-flash | Cloud | External docs | $ |

**Cost Breakdown**:
- Cloud-only: $30-50/month
- With GPU: $10-20/month (60-80% savings)

### Hybrid-Claude-Ollama Profile

| Agent | Model | Location | Use Case | Cost |
|-------|-------|----------|----------|------|
| **sisyphus** | anthropic/claude-sonnet | Cloud | Orchestration | Unlimited* |
| **oracle** | anthropic/claude-opus | Cloud | Deep reasoning | Unlimited* |
| **tdd-guide** | anthropic/claude-sonnet | Cloud | Quality code | Unlimited* |
| **code-reviewer** | anthropic/claude-sonnet | Cloud | Code review | Unlimited* |
| **security** | anthropic/claude-opus | Cloud | Security audit | Unlimited* |
| **explore** | ollama/ministral-3 | **GPU** | Codebase search | **FREE** |
| **build-error-resolver** | ollama/qwen3-coder | **GPU** | Type/lint errors | **FREE** |
| **document-writer** | ollama/lfm2.5 | **GPU** | Doc generation | **FREE** |
| **doc-updater** | ollama/lfm2.5 | **GPU** | Doc sync | **FREE** |
| **refactor-cleaner** | ollama/qwen3-coder | **GPU** | Dead code removal | **FREE** |
| **journalist** | ollama/lfm2.5 | **GPU** | Journal keeping | **FREE** |
| **librarian** | google/gemini-flash | Cloud | External docs | $ |

*Unlimited with Claude MAX subscription ($20/month)

**Token Savings**: 60% of volume tasks offloaded → Effective capacity 2.5x higher

---

## Request Flow

### Example: User asks "Refactor the auth module"

```
1. User → Sisyphus (openai/gpt-5.2, cloud)
   ├─> Analyzes request
   └─> Delegates to specialized agents

2. Sisyphus → Explore (ollama/ministral-3, GPU)
   ├─> Searches codebase for auth files
   ├─> Finds patterns, dependencies
   └─> Returns file list + context

3. Sisyphus → Oracle (openai/gpt-5.2, cloud)
   ├─> Analyzes architecture
   ├─> Proposes refactoring plan
   └─> Returns detailed plan

4. Sisyphus → TDD Guide (openai/gpt-4o, cloud)
   ├─> Writes tests first
   ├─> Implements refactoring
   └─> Verifies with LSP

5. Sisyphus → Build Resolver (ollama/qwen3-coder, GPU)
   ├─> Fixes any type errors
   └─> Runs diagnostics

6. Sisyphus → Code Reviewer (openai/gpt-4o, cloud)
   ├─> Reviews changes
   ├─> Checks security
   └─> Approves or requests fixes

7. Sisyphus → Doc Updater (ollama/lfm2.5, GPU)
   ├─> Updates README, docs
   └─> Syncs with code changes

8. Sisyphus → User
   └─> Refactoring complete, all checks passed
```

**Cost Analysis**:
- **Cloud-only**: 7 agents × cloud models = $$$
- **With GPU**: 3 GPU agents (explore, build, doc) = FREE → 43% cost reduction

---

## Deployment Patterns

### Pattern 1: Developer Workstation (Local GPU)

```
┌────────────────────────────────┐
│ Developer Laptop/Desktop       │
│                                │
│ ┌────────────────────────────┐ │
│ │ OpenCode CLI               │ │
│ │   ↓                        │ │
│ │ Ollama (localhost:11434)   │ │
│ │   ↓                        │ │
│ │ NVIDIA RTX 4060 Ti (16GB)  │ │
│ └────────────────────────────┘ │
└────────────────────────────────┘
```

**Pros**: Zero latency, full control, no network dependency  
**Cons**: GPU tied to one machine, no sharing  
**Best for**: Individual developers with gaming/workstation GPU

---

### Pattern 2: Shared GPU Server (Team)

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Dev Workstation  │     │ Dev Workstation  │     │ Dev Workstation  │
│                  │     │                  │     │                  │
│ OpenCode CLI     │     │ OpenCode CLI     │     │ OpenCode CLI     │
└────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │ LAN (1-5ms latency)
                                  ▼
                    ┌──────────────────────────┐
                    │ GPU Server (24/7)        │
                    │                          │
                    │ Ollama (0.0.0.0:11434)   │
                    │   ↓                      │
                    │ NVIDIA A4000 (16GB)      │
                    │ or RTX 4090 (24GB)       │
                    └──────────────────────────┘
```

**Pros**: Shared GPU resources, 24/7 availability, cost-effective  
**Cons**: Network latency (~1-5ms), single point of failure  
**Best for**: Small teams (3-10 devs), budget-conscious

**Setup**:
```bash
# On GPU server
OLLAMA_HOST=0.0.0.0:11434 ollama serve

# On dev workstations
export OLLAMA_HOST=http://gpu-server.local:11434
```

---

### Pattern 3: Kubernetes GPU Pool (Enterprise)

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Dev Workstation  │     │ Dev Workstation  │     │ Dev Workstation  │
└────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │ K8s LoadBalancer         │
                    │ ollama-service.svc       │
                    └────────────┬─────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
┌────────────────┐      ┌────────────────┐      ┌────────────────┐
│ Ollama Pod 1   │      │ Ollama Pod 2   │      │ Ollama Pod 3   │
│                │      │                │      │                │
│ GPU: A100 (1)  │      │ GPU: A100 (1)  │      │ GPU: A100 (1)  │
└────────────────┘      └────────────────┘      └────────────────┘
```

**Pros**: Auto-scaling, high availability, GPU pooling, multi-tenant  
**Cons**: Complex setup, requires K8s + GPU operator  
**Best for**: Large teams (50+ devs), enterprise environments

**Setup**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama-server
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: ollama
        image: ollama/ollama:latest
        resources:
          limits:
            nvidia.com/gpu: 1
```

---

## Fallback Strategy

### Automatic Cloud Fallback

```
┌─────────────────────────────────────────────────────────────┐
│ Request: "Explore codebase for auth patterns"              │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │ Try: ollama/ministral │
            └───────┬───────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
    SUCCESS                 FAILURE
        │                   (timeout/OOM/unreachable)
        │                       │
        ▼                       ▼
    Return result       ┌───────────────────────┐
                        │ Fallback: gemini-flash│
                        └───────┬───────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
                SUCCESS                 FAILURE
                    │                   (rate limit)
                    │                       │
                    ▼                       ▼
                Return result       ┌───────────────────────┐
                                    │ Fallback: gemini-pro  │
                                    └───────────────────────┘
```

**Fallback Chains**:

| Agent | Primary | Fallback 1 | Fallback 2 |
|-------|---------|------------|------------|
| explore | ollama/ministral | gemini-flash | gemini-pro |
| build-error-resolver | ollama/qwen3-coder | gemini-flash | gpt-4o-mini |
| document-writer | ollama/lfm2.5 | gemini-flash | gpt-4o-mini |

**User Experience**: Transparent — no manual intervention required.

---

## Performance Characteristics

### Latency Comparison

| Setup | Typical Latency | Use Case |
|-------|----------------|----------|
| **Local GPU** | 50-200ms | Developer workstation |
| **LAN GPU Server** | 100-300ms | Team server (1-5ms network) |
| **Remote GPU (WAN)** | 200-500ms | Remote cluster (50-100ms network) |
| **Cloud API** | 500-2000ms | OpenAI/Anthropic/Google |

**Recommendation**: Local or LAN setup for best experience.

### Throughput

| GPU | Concurrent Requests | Tokens/sec |
|-----|---------------------|------------|
| RTX 4060 Ti (16GB) | 2-4 | ~50-100 |
| RTX 4090 (24GB) | 4-8 | ~100-200 |
| A4000 (16GB) | 4-6 | ~80-150 |
| A100 (40GB) | 8-12 | ~200-400 |

**Tuning**: Adjust `provider_limits.ollama` in profile based on GPU capacity.

---

## Cost Savings Analysis

### Scenario: 100 hours of coding per month

**Cloud-Only Profile**:
```
Sisyphus:        20 hours × $15/1M tokens = $10
Oracle:          10 hours × $15/1M tokens = $5
TDD Guide:       30 hours × $5/1M tokens  = $8
Explore:         15 hours × $0.075/1M     = $0.60
Build Resolver:  10 hours × $0.075/1M     = $0.40
Doc Writer:      15 hours × $0.075/1M     = $0.60
─────────────────────────────────────────────
Total: ~$25/month
```

**Hybrid-Cloud-Ollama Profile**:
```
Sisyphus:        20 hours × $15/1M tokens = $10
Oracle:          10 hours × $15/1M tokens = $5
TDD Guide:       30 hours × $5/1M tokens  = $8
Explore:         15 hours × FREE          = $0  ✓
Build Resolver:  10 hours × FREE          = $0  ✓
Doc Writer:      15 hours × FREE          = $0  ✓
─────────────────────────────────────────────
Total: ~$23/month + GPU electricity (~$2)
Savings: 60% on volume tasks
```

**Break-Even Analysis**:
- GPU power consumption: ~200W × 100 hours = 20 kWh/month
- Electricity cost: 20 kWh × $0.12/kWh = $2.40/month
- Cloud savings: $1.60/month (from volume tasks)
- **Net savings**: Minimal on cost, but **2.5x capacity increase**

**Real Value**: Not cost savings, but **capacity multiplier** — same budget, more work done.

---

## Security Considerations

### Network Isolation

```
┌──────────────────────────────────────────────────────────┐
│ Ollama Agents (Local GPU)                                │
│                                                          │
│ Permissions:                                             │
│   ✓ Read: codebase, docs                                │
│   ✗ Write: filesystem (read-only)                       │
│   ✗ Webfetch: denied (no external API calls)            │
│   ✗ Edit: denied (no code modifications)                │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ Cloud Agents (Anthropic/OpenAI)                          │
│                                                          │
│ Permissions:                                             │
│   ✓ Read: codebase, docs, web                           │
│   ✓ Write: filesystem (controlled)                      │
│   ✓ Webfetch: allowed (research, docs)                  │
│   ✓ Edit: allowed (code modifications)                  │
└──────────────────────────────────────────────────────────┘
```

**Rationale**: Local models are less trusted → restricted permissions.

### Data Privacy

| Data Type | Local GPU | Cloud API |
|-----------|-----------|-----------|
| **Codebase** | Stays local | Sent to API |
| **Credentials** | Never sent | Never sent |
| **User prompts** | Stays local | Sent to API |
| **Model outputs** | Stays local | Returned from API |

**Best Practice**: Use ollama for sensitive codebases, cloud for open-source work.

---

## Monitoring & Observability

### GPU Monitoring

```bash
# Real-time GPU usage
watch -n 1 nvidia-smi

# Ollama-specific processes
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv

# Model memory usage
ollama ps
```

### Ollama Logs

```bash
# Systemd logs
journalctl -u ollama -f

# Request logs
tail -f /var/log/ollama/requests.log
```

### astraeus Metrics

```bash
# Session cost analysis
opencode /analyze-bottleneck

# Model routing health
opencode /routing-smoke

# Local environment check
opencode /local-smoke
```

---

## Next Steps

1. **Read**: [GPU_CLUSTER_SETUP.md](GPU_CLUSTER_SETUP.md) for detailed setup guide
2. **Run**: `./setup-ollama-cluster.sh` for automated installation
3. **Test**: `opencode /local-smoke` to verify setup
4. **Monitor**: `watch nvidia-smi` to observe GPU usage
5. **Optimize**: Adjust `provider_limits.ollama` based on GPU capacity

---

**Questions?** See [GPU_CLUSTER_SETUP.md](GPU_CLUSTER_SETUP.md) troubleshooting section.
