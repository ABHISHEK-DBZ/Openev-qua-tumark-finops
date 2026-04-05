import copy
from typing import Any, Dict

from src.models import (
    Observation,
    Action,
    StepResult
)

# Initial State represented as a dictionary for easy parsing and deepcopy
INITIAL_STATE = {
    "instances": [
        {
            "instance_id": "i-webapp-prod",
            "instance_type": "t3.large",
            "state": "running",
            "cpu_utilization_percent": 65.0,
            "monthly_cost": 60.0,
            "tags": {"Name": "WebApp-Prod", "Environment": "production"}
        },
        {
            "instance_id": "i-db-prod",
            "instance_type": "t3.xlarge",
            "state": "running",
            "cpu_utilization_percent": 4.2,
            "monthly_cost": 120.0,
            "tags": {"Name": "Database-Prod", "Environment": "production"}
        },
        {
            "instance_id": "i-rogue-1",
            "instance_type": "p3.2xlarge",
            "state": "running",
            "cpu_utilization_percent": 100.0,
            "monthly_cost": 2000.0,
            "tags": {"Name": "RogueInstance-1", "Owner": "dev-john", "Environment": "development"}
        },
        {
            "instance_id": "i-rogue-2",
            "instance_type": "p3.2xlarge",
            "state": "running",
            "cpu_utilization_percent": 100.0,
            "monthly_cost": 2000.0,
            "tags": {"Name": "RogueInstance-2", "Owner": "dev-john", "Environment": "development"}
        }
    ],
    "elastic_ips": [
        {"allocation_id": "eip-001", "public_ip": "203.0.113.1", "associated_instance_id": None, "monthly_cost": 3.65},
        {"allocation_id": "eip-002", "public_ip": "203.0.113.2", "associated_instance_id": None, "monthly_cost": 3.65},
        {"allocation_id": "eip-003", "public_ip": "203.0.113.3", "associated_instance_id": None, "monthly_cost": 3.65},
        {"allocation_id": "eip-004", "public_ip": "203.0.113.4", "associated_instance_id": "i-webapp-prod", "monthly_cost": 3.65}
    ],
    "iam_users": [
        {"user_name": "admin", "has_mfa_enabled": True, "active_access_keys_count": 1, "days_since_key_rotation": 30},
        {"user_name": "dev-john", "has_mfa_enabled": False, "active_access_keys_count": 2, "days_since_key_rotation": 120}
    ],
    "s3_buckets": [],
    "security_alerts": [
        {
            "alert_id": "sec-alert-001",
            "severity": "critical",
            "description": "Compromised credentials suspected for dev-john. Multiple GPU instances launched.",
            "affected_resource_id": "dev-john"
        }
    ],
    "billing_summary": {
        "total_monthly_spend": 4194.60,
        "projected_monthly_spend": 5000.0,
        "budget_limit": 1000.0
    }
}

class CloudFinOpsEnv:
    def __init__(self, task_id: int):
        self.task_id = task_id
        self.max_steps = 20
        self.current_step = 0
        self.current_state: Observation = Observation(**copy.deepcopy(INITIAL_STATE))
        
        # Internal state to track actions for grading
        self.released_eips = set()
        self.downsized_instances = set()
        self.terminated_rogues = set()
        self.revoked_john_keys = False
        self.terminated_prod = set()

    def reset(self) -> Observation:
        self.current_step = 0
        self.current_state = Observation(**copy.deepcopy(INITIAL_STATE))
        self.released_eips = set()
        self.downsized_instances = set()
        self.terminated_rogues = set()
        self.revoked_john_keys = False
        self.terminated_prod = set()
        return self.state()

    def state(self) -> Observation:
        return Observation(**self.current_state.dict())

    def step(self, action: Action) -> StepResult:
        if self.current_step >= self.max_steps:
            score = self._grade()
            return StepResult(observation=self.state(), reward=score, done=True, info={"message": "Max steps exceeded"})
            
        self.current_step += 1
        
        # Apply the action
        self._apply_action(action)
        
        # Calculate Reward
        score = self._grade()
        done = (score >= 1.0) or (self.current_step >= self.max_steps)
        
        info = {}
        if self.current_step >= self.max_steps:
            info["message"] = "Max steps reached"
        if score >= 1.0:
            info["message"] = "Task goals achieved successfully"
            
        return StepResult(
            observation=self.state(),
            reward=score,
            done=done,
            info=info
        )

    def _grade(self) -> float:
        score = 0.0
        
        if self.task_id == 1:
            # Task 1: Score = (released unattached EIPs / 3) minus 0.3 penalty if attached EIP released
            valid_eips = {'eip-001', 'eip-002', 'eip-003'}
            released_valid = len(self.released_eips.intersection(valid_eips))
            score = released_valid / 3.0
            if 'eip-004' in self.released_eips:
                score -= 0.3
                
        elif self.task_id == 2:
            # Task 2: Score = 1.0 if Database-Prod is t3.medium, 0.5 if any downsize, 0.0 otherwise
            db_inst = next((i for i in self.current_state.instances if i.instance_id == 'i-db-prod'), None)
            if db_inst and db_inst.instance_type == "t3.medium":
                score = 1.0
            elif len(self.downsized_instances) > 0:
                score = 0.5
                
        elif self.task_id == 3:
            # Task 3: Score = (rogues terminated / 2 * 0.5) + (0.5 if john's key revoked) minus 0.5 if any prod instance terminated
            rogues_terminated_count = len(self.terminated_rogues.intersection({'i-rogue-1', 'i-rogue-2'}))
            score = (rogues_terminated_count / 2.0) * 0.5
            if self.revoked_john_keys:
                score += 0.5
            if len(self.terminated_prod) > 0:
                score -= 0.5
                
        # Clamp score between 0.0 and 1.0 as requested
        return max(0.0, min(1.0, float(score)))

    def _apply_action(self, action: Action):
        action_type = action.action_type
        
        if action_type == "terminate_instance":
            # Support both instance_id (pydantic) and raw dict resource_id if needed
            target_id = getattr(action, "instance_id", getattr(action, "resource_id", None))
            for i in self.current_state.instances:
                if i.instance_id == target_id and i.state != "terminated":
                    i.state = "terminated"
                    i.monthly_cost = 0.0  # Money saved!
                    if i.instance_id in ['i-rogue-1', 'i-rogue-2']:
                        self.terminated_rogues.add(i.instance_id)
                    elif i.instance_id in ['i-webapp-prod', 'i-db-prod']:
                        self.terminated_prod.add(i.instance_id)

        elif action_type == "downsize_instance":
            target_id = getattr(action, "instance_id", getattr(action, "resource_id", None))
            for i in self.current_state.instances:
                if i.instance_id == target_id:
                    # Logic: if downsizing, reduce cost significantly
                    if "xlarge" in i.instance_type:
                        i.monthly_cost = 20.0  # Was 120.0
                    else:
                        i.monthly_cost = 10.0
                    
                    i.instance_type = getattr(action, "new_instance_type", "t3.medium")
                    self.downsized_instances.add(i.instance_id)
                    
        elif action_type == "release_elastic_ip":
            target_ip_alloc = action.allocation_id
            found = False
            new_ips = []
            for eip in self.current_state.elastic_ips:
                if eip.allocation_id == target_ip_alloc:
                    self.released_eips.add(eip.allocation_id)
                    found = True
                else:
                    new_ips.append(eip)
            if found:
                self.current_state.elastic_ips = new_ips
                
        elif action_type in ["revoke_iam_key", "revoke_user"]:
            target_user = getattr(action, "user_name", getattr(action, "user_id", None))
            for u in self.current_state.iam_users:
                if u.user_name == target_user:
                    if u.active_access_keys_count > 0:
                        u.active_access_keys_count -= 1
                    if target_user == 'dev-john':
                        self.revoked_john_keys = True
                        
        elif action_type == "apply_tag":
             for i in self.current_state.instances:
                 if i.instance_id == action.resource_id:
                     i.tags[action.tag_key] = action.tag_value
                     
        # RECALCULATE BILLING SUMMARY AFTER EVERY MODIFICATION
        new_total = sum(i.monthly_cost for i in self.current_state.instances)
        new_total += sum(e.monthly_cost for e in self.current_state.elastic_ips)
        new_total += sum(s.monthly_cost for s in self.current_state.s3_buckets)
        
        self.current_state.billing_summary.total_monthly_spend = round(new_total, 2)
