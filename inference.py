#!/usr/bin/env python3
"""
OpenEnv Inference Script for Cloud FinOps & Security Simulator
Directly uses CloudFinOpsEnv per OpenEnv spec.
"""

import os
import sys
import time
import json
from typing import Dict, Any, List, Optional

# Environment variables
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api-inference.huggingface.co/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "mistralai/Mistral-7B-Instruct-v0.3")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
ENV_NAME = "Cloud FinOps & Security Simulator"

# Validate HF_TOKEN is provided
if not HF_TOKEN:
    print("Error: HF_TOKEN environment variable is required", file=sys.stderr)
    sys.exit(1)

# Import environment and models
try:
    from src.env import CloudFinOpsEnv
    from src.models import (
        TerminateInstanceAction,
        DownsizeInstanceAction,
        ReleaseElasticIPAction,
        RevokeIAMKeyAction,
        NoOpAction,
    )
except ImportError as e:
    print(f"Error: Failed to import environment modules: {e}", file=sys.stderr)
    sys.exit(1)

# Import OpenAI client
try:
    from openai import OpenAI
except ImportError:
    print("Error: 'openai' library not found. Run 'pip install openai'", file=sys.stderr)
    sys.exit(1)

# Initialize OpenAI Client
try:
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
except Exception as e:
    print(f"Error: Failed to initialize OpenAI client: {e}", file=sys.stderr)
    sys.exit(1)

START_TIME = time.time()
MAX_ELAPSED_SECONDS = 1100


def print_start(task_name: str, env_name: str = ENV_NAME, model_name: str = MODEL_NAME):
    print(f"[START] task={task_name} env={env_name} model={model_name}", flush=True)


def print_step(step_num: int, action_dict: Dict[str, Any], reward: float, done: bool, error: Optional[str] = None):
    done_str = str(done).lower()
    error_str = str(error) if error else "null"
    action_str = str(action_dict).replace('\n', '').replace("'", '"')
    print(
        f"[STEP] step={step_num} action={action_str} reward={reward:.2f} done={done_str} error={error_str}",
        flush=True,
    )


def print_end(success: bool, steps: int, score: float, rewards_list: List[float]):
    success_str = str(success).lower()
    rewards_str = ",".join([f"{r:.2f}" for r in rewards_list])
    print(
        f"[END] success={success_str} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


def condense_observation(obs) -> str:
    """Shrink observation to critical fields for small LLMs."""
    lines = []
    
    # EC2 instances
    if obs.instances:
        lines.append("EC2 INSTANCES:")
        for i in obs.instances:
            if i.state == "terminated":
                continue
            name = i.tags.get("Name", i.instance_id)
            lines.append(
                f"  - {name} ({i.instance_id}): type={i.instance_type}, cpu={i.cpu_utilization_percent}%, cost=${i.monthly_cost}"
            )
    
    # Elastic IPs
    if obs.elastic_ips:
        lines.append("ELASTIC IPs:")
        for e in obs.elastic_ips:
            attached = e.associated_instance_id or "UNATTACHED"
            lines.append(f"  - {e.allocation_id}: associated_to={attached}")
    
    # IAM users
    if obs.iam_users:
        lines.append("IAM USERS:")
        for u in obs.iam_users:
            lines.append(f"  - {u.user_name}: keys={u.active_access_keys_count}, mfa={u.has_mfa_enabled}")
    
    # Security alerts
    if obs.security_alerts:
        lines.append("SECURITY ALERTS:")
        for a in obs.security_alerts:
            lines.append(f"  - {a.severity.upper()}: {a.description}")
    
    # Billing
    if obs.billing_summary:
        lines.append(f"BILLING: monthly_spend=${obs.billing_summary.total_monthly_spend}")
    
    return "\n".join(lines)


def build_task_prompt(task_id: int, condensed_obs: str, history: List[str] = None) -> str:
    """Build task-specific prompt."""
    history_str = ""
    if history:
        history_str = "\n\nPREVIOUS ACTIONS (Do NOT repeat if successful):\n" + "\n".join([f"- {h}" for h in history[-5:]])

    if task_id == 1:
        return (
            f"{condensed_obs}{history_str}\n\n"
            "Objective: Save money on Elastic IPs.\n"
            "ACTION: Release ONE unattached Elastic IP (look for UNATTACHED in the list).\n"
            'Reply ONLY with JSON: {"action_type": "release_elastic_ip", "allocation_id": "ID_HERE"}'
        )

    elif task_id == 2:
        return (
            f"{condensed_obs}{history_str}\n\n"
            "Objective: Right-size the database instance.\n"
            "ACTION: Downsize i-db-prod to t3.medium.\n"
            'Reply ONLY with JSON: {"action_type": "downsize_instance", "instance_id": "i-db-prod", "new_instance_type": "t3.medium"}'
        )

    elif task_id == 3:
        return (
            f"{condensed_obs}{history_str}\n\n"
            "Objective: SECURITY INCIDENT RESPONSE.\n"
            "STEP 1: Terminate rogue instances (i-rogue-1, i-rogue-2).\n"
            "STEP 2: After rogues are gone, revoke dev-john's IAM key.\n"
            'Reply ONLY with JSON: {"action_type": "terminate_instance", "instance_id": "..."}  OR  {"action_type": "revoke_iam_key", "user_name": "dev-john"}'
        )

    return f"Observation:\n{condensed_obs}\n{history_str}\n\nReturn JSON action."


def extract_json_from_response(text: str) -> Dict[str, Any]:
    """Extract and parse JSON from model response."""
    import re
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    return {}


def call_llm(observation, task_id: int, history: List[str] = None) -> Dict[str, Any]:
    """Call LLM to get next action."""
    condensed = condense_observation(observation)
    user_prompt = build_task_prompt(task_id, condensed, history)
    
    sys_prompt = (
        "You are a Cloud FinOps and Security AI Agent. "
        "Output ONLY valid JSON matching the action schema. "
        "No preamble, no conversational filler. "
        "Valid action_type values: terminate_instance, downsize_instance, release_elastic_ip, revoke_iam_key, no_op"
    )

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                max_tokens=200,
            )
            content = response.choices[0].message.content
            parsed = extract_json_from_response(content)
            if "action_type" in parsed:
                return parsed
        except Exception as e:
            if attempt < 2:
                time.sleep(1)
            continue
            
    return {"action_type": "no_op"}


def build_action_from_dict(action_dict: Dict[str, Any]):
    """Convert action dict to proper Action object."""
    action_type = action_dict.get("action_type", "no_op").lower()
    
    try:
        if action_type == "terminate_instance":
            return TerminateInstanceAction(
                instance_id=action_dict.get("instance_id", "i-unknown")
            )
        elif action_type == "downsize_instance":
            return DownsizeInstanceAction(
                instance_id=action_dict.get("instance_id", "i-unknown"),
                new_instance_type=action_dict.get("new_instance_type", "t3.medium")
            )
        elif action_type == "release_elastic_ip":
            return ReleaseElasticIPAction(
                allocation_id=action_dict.get("allocation_id", "eip-unknown")
            )
        elif action_type in ["revoke_iam_key", "revoke_user"]:
            return RevokeIAMKeyAction(
                user_name=action_dict.get("user_name", "unknown")
            )
        else:
            return NoOpAction()
    except Exception as e:
        print(f"[DEBUG] Failed to build action: {e}", file=sys.stderr)
        return NoOpAction()


def run_task(task_id: int, task_name: str) -> float:
    """Run a single task from start to finish."""
    print_start(task_name)
    
    env = None
    try:
        env = CloudFinOpsEnv(task_id=task_id)
        observation = env.reset()
    except Exception as e:
        print(f"[DEBUG] Env reset failed: {e}", file=sys.stderr)
        print_end(False, 0, 0.0, [0.0])
        return 0.0
    
    done = False
    final_score = 0.0
    steps = 0
    history = []
    rewards_list = []
    
    while not done:
        elapsed = time.time() - START_TIME
        if elapsed > MAX_ELAPSED_SECONDS:
            print(f"[DEBUG] Timeout after {elapsed:.1f}s", file=sys.stderr)
            break
        
        if steps >= 20:
            print(f"[DEBUG] Max steps (20) reached", file=sys.stderr)
            break
        
        try:
            # Call LLM to get action
            action_dict = call_llm(observation, task_id, history)
            action = build_action_from_dict(action_dict)
            
            # Record action in history
            action_type = action_dict.get("action_type", "unknown")
            history.append(f"{action_type}({json.dumps({k: v for k, v in action_dict.items() if k != 'action_type'})})")
            
            # Execute action
            result = env.step(action)
            
            observation_next = result.observation
            reward = result.reward or 0.0
            done = result.done
            steps += 1
            
            rewards_list.append(reward)
            print_step(steps, action_dict, reward, done)
            
            observation = observation_next
            final_score = reward
            
        except Exception as e:
            print(f"[DEBUG] Step execution failed: {e}", file=sys.stderr)
            print_step(steps + 1, {}, 0.0, True, error=str(e))
            break
    
    print_end(done, steps, final_score, rewards_list)
    return final_score


def main():
    """Main entry point — run all 3 tasks."""
    try:
        tasks = [
            (1, "Cost Optimization: Unattached EIP Cleanup"),
            (2, "Cost Optimization: Rightsizing Production Database"),
            (3, "Security Response: Compromised Identities & Rogue Workloads"),
        ]
        
        scores = {}
        for task_id, task_name in tasks:
            elapsed = time.time() - START_TIME
            if elapsed > MAX_ELAPSED_SECONDS:
                break
            scores[task_id] = run_task(task_id, task_name)
        
        # Calculate overall success
        if scores:
            avg_score = sum(scores.values()) / len(tasks)
            sys.exit(0 if avg_score >= 0.5 else 1)
        else:
            sys.exit(1)
            
    except Exception as e:
        import traceback
        print(f"[FATAL] {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

