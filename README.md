---
title: OpenEnv QuantumArk FinOps
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
tags:
- openenv
---

# Cloud FinOps & Security Simulator

An interactive OpenEnv simulation challenging autonomous agents to optimize cloud infrastructure costs and resolve critical IAM security leaks.

## Environment Description
This simulator models a simplified cloud environment (EC2, EIP, IAM, S3) where an agent acts as a Cloud FinOps and Security engineer. The goal is to maximize cost savings and security posture without disrupting production workloads.

## Action & Observation Space

### Observation Schema
The agent receives a JSON object containing:
- `instances`: List of EC2 instances with `instance_id`, `state`, `cpu_utilization_percent`, `monthly_cost`, and `tags`.
- `elastic_ips`: List of EIPs with `allocation_id` and `associated_instance_id`.
- `iam_users`: List of IAM users with `user_name` and `access_keys` status.
- `security_alerts`: Active alerts (e.g., Rogue GPU instance detected).
- `billing_summary`: Current and projected monthly spend.

### Action Schema
The agent can perform the following actions:
- `terminate_instance(instance_id)`
- `downsize_instance(instance_id, new_instance_type)`
- `release_elastic_ip(allocation_id)`
- `revoke_iam_key(user_name, access_key_id)`
- `no_op()`

## Tasks

### 1. Cost Optimization: EIP Cleanup (Easy)
Identify and release orphaned Elastic IP allocations not attached to any instances.
**Success Criteria:** Release `eip-001`, `eip-002`, and `eip-003`. Do NOT touch `eip-004`.

### 2. Rightsizing Database (Medium)
Downsize the idle `Database-Prod` instance (`t3.xlarge`) to `t3.medium` to save costs while maintaining stability.
**Success Criteria:** Instance type becomes `t3.medium`.

### 3. Security Incident Response (Hard)
Neutralize a breach: Terminate rogue GPU instances (`i-rogue-1`, `i-rogue-2`) and revoke the compromised keys for `dev-john`.
**Success Criteria:** Both rogue instances terminated and IAM key revoked.

## Setup Instructions

### Prerequisites
- Docker
- Python 3.10+

### Running with Docker
1. Build the image:
   ```bash
   docker build -t cloud-finops-sim .
   ```
2. Run the container:
   ```bash
   docker run -p 7860:7860 cloud-finops-sim
   ```
3. The dashboard will be available at `http://localhost:7860`.

### Running Locally
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the simulator:
   ```bash
   python main.py
   ```
3. Run the inference agent:
   ```bash
   python inference.py
   ```
