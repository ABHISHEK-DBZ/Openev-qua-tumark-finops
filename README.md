---
title: OpenEnv QuantumArk FinOps
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
tags:
- openenv
- finops
- cloud-optimization
- autonomous-agent
---

# ☁️ Cloud FinOps & Security Simulator

> **An interactive OpenEnv simulation for autonomous agents to optimize cloud infrastructure costs and resolve critical security incidents.**

[![HF Space](https://img.shields.io/badge/🤗-HuggingFace%20Space-blue)](https://huggingface.co/spaces/abhibro936/openenv-quantumark-finops)
[![GitHub](https://img.shields.io/badge/GitHub-Openev--qua--tumark--finops-black)](https://github.com/ABHISHEK-DBZ/Openev-qua-tumark-finops)
[![OpenEnv](https://img.shields.io/badge/OpenEnv-0.1-green)](https://github.com/allenai/openenv)

---

## 📋 Overview

This simulator models a **realistic cloud environment** with EC2 instances, Elastic IPs, IAM users, and security alerts. Autonomous agents must act as **Cloud FinOps and Security engineers** to:
- ✅ Detect and eliminate cost waste
- ✅ Resolve critical security breaches
- ✅ Maintain production stability

**Perfect for:** Training and evaluating LLM-based agents on real-world cloud operations scenarios.

---

## 🎮 Three Escalating Tasks

| Task | Difficulty | Objective | Max Score |
|------|-----------|-----------|-----------|
| **1. EIP Cleanup** | 🟢 Easy | Release 3 orphaned Elastic IPs without disrupting `eip-004` | 1.0 |
| **2. Database Rightsizing** | 🟡 Medium | Downsize idle Database-Prod from `t3.xlarge` → `t3.medium` | 1.0 |
| **3. Security Incident** | 🔴 Hard | Terminate 2 rogue GPU instances + revoke compromised IAM keys | 1.0 |

---

## 🏗️ Architecture

### Environment State (Observation)
```json
{
  "ec2_instances": [
    {
      "instance_id": "i-webapp-prod",
      "instance_type": "t3.large",
      "state": "running",
      "cpu_utilization_percent": 65.0,
      "monthly_cost": 60.0
    }
  ],
  "elastic_ips": [
    {
      "allocation_id": "eip-001",
      "public_ip": "203.0.113.1",
      "associated_instance_id": null,
      "monthly_cost": 3.65
    }
  ],
  "iam_users": [
    {
      "user_name": "dev-john",
      "has_mfa_enabled": false,
      "active_access_keys_count": 2
    }
  ],
  "security_alerts": [
    {
      "alert_id": "sec-alert-001",
      "severity": "critical",
      "description": "Compromised credentials suspected for dev-john"
    }
  ],
  "billing_summary": {
    "total_monthly_spend": 4194.60,
    "projected_monthly_spend": 5000.0,
    "budget_limit": 1000.0
  }
}
```

### Available Actions
```python
terminate_instance(instance_id)         # Stop running instances
downsize_instance(instance_id, new_type) # Right-size to cheaper types
release_elastic_ip(allocation_id)       # Remove unattached EIPs
revoke_iam_key(user_name, access_key_id) # Disable compromised keys
no_op()                                 # Valid no-operation action
```

---

## 🚀 Quick Start

### Option 1: Try Live (Hugging Face Space)
Visit: **[https://huggingface.co/spaces/abhibro936/openenv-quantumark-finops](https://huggingface.co/spaces/abhibro936/openenv-quantumark-finops)**

All tasks are instantly accessible via REST API. No setup required.

### Option 2: Run Locally

#### Prerequisites
- Python 3.10+
- Docker (optional, for containerized deployment)

#### Installation
```bash
# Clone the repository
git clone https://github.com/ABHISHEK-DBZ/Openev-qua-tumark-finops.git
cd Openev-qua-tumark-finops

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### Start the Server
```bash
# Terminal 1: Start FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 7860

# Now accessible at: http://localhost:7860
```

#### Run an Agent
```bash
# Terminal 2: Execute agent inference
export API_BASE_URL="http://localhost:11434/v1"  # Ollama or OpenAI endpoint
export MODEL_NAME="llama3.2"
export HF_TOKEN="your-token-or-ollama"
export ENV_BASE_URL="http://localhost:7860"

python inference.py
```

---

## 📡 API Reference

### Initialize Task
```bash
POST /reset?task_id=1
```
**Response:** Initial observation JSON for the specified task.

### Get Current State
```bash
GET /state?task_id=1
```
**Response:** Current environment state.

### Execute Action
```bash
POST /step?task_id=1
Content-Type: application/json

{
  "action_type": "release_elastic_ip",
  "allocation_id": "eip-001"
}
```
**Response:** 
```json
{
  "observation": {...},
  "reward": 0.33,
  "done": false,
  "info": {}
}
```

### View Dashboard
```
GET /
```
**Response:** HTML dashboard with task stats and live metrics.

---

## 🐳 Docker Deployment

### Build Image
```bash
docker build -t cloud-finops-sim:latest .
```

### Run Container
```bash
docker run -it -p 7860:7860 \
  -e API_BASE_URL="http://host.docker.internal:11434/v1" \
  -e MODEL_NAME="llama3.2" \
  -e HF_TOKEN="ollama" \
  cloud-finops-sim:latest
```

---

## 📊 Scoring & Grading

Each task has **independent scoring** (0.0–1.0 range):

### Task 1: EIP Cleanup
- Release each orphaned EIP: **+0.33**
- Release attached EIP (`eip-004`): **-0.30 penalty**
- Max Score: **1.0**

### Task 2: Database Rightsizing
- Exact target (`t3.medium`): **1.0**
- Any downsize attempt: **0.5**
- No action: **0.0**

### Task 3: Security Incident
- Each rogue terminated: **0.25**
- Revoke compromised keys: **0.5**
- Terminate production instance: **-0.5 penalty**
- Max Score: **1.0**

---

## 📝 Inference Script Format

Your agent must emit **strict stdout format** for evaluation:

```python
[START] task=Task Name env=Cloud FinOps & Security Simulator model=llama3.2
[STEP] step=1 action={'action_type': 'no_op'} reward=0.00 done=false error=null
[STEP] step=2 action={'action_type': 'release_elastic_ip', 'allocation_id': 'eip-001'} reward=0.33 done=false error=null
[END] success=true steps=2 score=1.00 rewards=0.00,0.33
```

**Critical Format Rules:**
- `[START]` must appear once per task
- `[STEP]` emitted after each action
- `[END]` must close the task
- Rewards formatted to 2 decimal places
- No newlines in action dict strings

---

## 🏗️ Project Structure
```
.
├── main.py              # FastAPI server & endpoints
├── inference.py         # LLM agent loop (entrypoint)
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container definition
├── openenv.yaml        # OpenEnv spec (3 tasks)
├── src/
│   ├── env.py         # CloudFinOpsEnv class
│   └── models.py      # Pydantic request/response models
└── tests/
    └── test_env.py    # Unit tests
```

---

## 🔧 Configuration

Set environment variables before running:

| Variable | Default | Purpose |
|----------|---------|---------|
| `API_BASE_URL` | `http://localhost:11434/v1` | LLM endpoint (Ollama/OpenAI) |
| `MODEL_NAME` | `llama3.2` | LLM model identifier |
| `HF_TOKEN` | `ollama` | API key or model access token |
| `ENV_BASE_URL` | `http://localhost:7860` | Environment server URL |

---

## 📚 OpenEnv Compliance

✅ **Full OpenEnv 0.1 Specification Compliance:**
- 3 independent tasks with graders
- Deterministic step/reset/state interface
- JSON observation & action schemas
- Reward in `[0.0, 1.0]` range
- `done` flag for episode termination

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -m "Add improvement"`)
4. Push to GitHub (`git push origin feature/improvement`)
5. Open a Pull Request

---

## 📄 License

MIT License — See LICENSE file for details.

---

## 🎯 Use Cases

- **LLM Fine-tuning:** Train agents on realistic cloud operations
- **Agentic Benchmarking:** Evaluate autonomy & decision-making
- **FinOps Training:** Educational sandbox for cost optimization
- **Security Response Drills:** Practice incident response at scale

---

## 🔗 Resources

- [OpenEnv GitHub](https://github.com/allenai/openenv)
- [CloudFinOps Best Practices](https://www.finops.org/)
- [AWS Cost Optimization](https://aws.amazon.com/aws-cost-management/)

---

**Made with ❤️ by [@ABHISHEK-DBZ](https://github.com/ABHISHEK-DBZ) [@Paritosh2681](https://github.com/Paritosh2681)**
