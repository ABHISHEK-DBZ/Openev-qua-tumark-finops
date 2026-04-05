import pytest

from src.env import CloudFinOpsEnv
from src.models import (
    ReleaseElasticIPAction,
    DownsizeInstanceAction,
    TerminateInstanceAction,
    RevokeIAMKeyAction,
    NoOpAction
)

# --- TASK 1 TESTS ---

def test_task1_release_all_three_eips():
    """Verify that releasing all 3 unattached EIPs yields a perfect score."""
    env = CloudFinOpsEnv(task_id=1)
    env.step(ReleaseElasticIPAction(allocation_id="eip-001"))
    env.step(ReleaseElasticIPAction(allocation_id="eip-002"))
    result = env.step(ReleaseElasticIPAction(allocation_id="eip-003"))
    assert result.reward == 1.0
    assert result.done is True

def test_task1_partial_credit():
    """Verify that releasing 2 out of 3 EIPs yields between exactly 0.5 and 1.0 score."""
    env = CloudFinOpsEnv(task_id=1)
    env.step(ReleaseElasticIPAction(allocation_id="eip-001"))
    result = env.step(ReleaseElasticIPAction(allocation_id="eip-002"))
    assert 0.5 < result.reward < 1.0

def test_task1_penalty_for_attached_eip():
    """Verify penalty is applied if production EIP (eip-004) is accidentally released."""
    env = CloudFinOpsEnv(task_id=1)
    # Give it some baseline positive score
    env.step(ReleaseElasticIPAction(allocation_id="eip-001"))
    # Release the restricted IP causing penalty
    result = env.step(ReleaseElasticIPAction(allocation_id="eip-004"))
    # 0.33 baseline minus 0.3 penalty
    assert result.reward < 0.33


# --- TASK 2 TESTS ---

def test_task2_correct_downsize():
    """Verify downsizing the correct instance to the exact target size yields perfect score."""
    env = CloudFinOpsEnv(task_id=2)
    result = env.step(DownsizeInstanceAction(instance_id="i-db-prod", new_instance_type="t3.medium"))
    assert result.reward == 1.0
    assert result.done is True

def test_task2_partial_downsize():
    """Verify downsizing but specifying a non-optimal target size yields partial credit."""
    env = CloudFinOpsEnv(task_id=2)
    result = env.step(DownsizeInstanceAction(instance_id="i-db-prod", new_instance_type="t3.large"))
    assert result.reward == 0.5

def test_task2_wrong_instance():
    """Verify downsizing the wrong instance protects Database-Prod and gives flat partial credit."""
    env = CloudFinOpsEnv(task_id=2)
    result = env.step(DownsizeInstanceAction(instance_id="i-webapp-prod", new_instance_type="t3.medium"))
    
    # Check Database-Prod remained untouched
    db_inst = next((i for i in result.observation.instances if i.instance_id == "i-db-prod"))
    assert db_inst.instance_type == "t3.xlarge"
    assert result.reward == 0.5


# --- TASK 3 TESTS ---

def test_task3_full_solve():
    """Verify terminating 2 rogues + revoking the IAM key yields perfect score."""
    env = CloudFinOpsEnv(task_id=3)
    env.step(TerminateInstanceAction(instance_id="i-rogue-1"))
    env.step(TerminateInstanceAction(instance_id="i-rogue-2"))
    result = env.step(RevokeIAMKeyAction(user_name="dev-john", access_key_id="dummy-key-id"))
    assert result.reward == 1.0
    assert result.done is True

def test_task3_partial_no_revoke():
    """Verify terminating rogues without revoking John's key yields partial credit (0.5)."""
    env = CloudFinOpsEnv(task_id=3)
    env.step(TerminateInstanceAction(instance_id="i-rogue-1"))
    result = env.step(TerminateInstanceAction(instance_id="i-rogue-2"))
    assert result.reward == 0.5

def test_task3_production_penalty():
    """Verify applying termination rules on production assets heavily penalizes output."""
    env = CloudFinOpsEnv(task_id=3)
    env.step(TerminateInstanceAction(instance_id="i-rogue-1"))
    env.step(TerminateInstanceAction(instance_id="i-rogue-2"))
    env.step(TerminateInstanceAction(instance_id="i-webapp-prod"))
    result = env.step(RevokeIAMKeyAction(user_name="dev-john", access_key_id="dummy-key"))
    
    # Theoretical score: 1.0 - 0.5 penalty = 0.5
    assert result.reward < 1.0
    assert result.reward == 0.5

def test_task3_no_false_positives():
    """Verify production instances are left running upon perfect security task resolutions."""
    env = CloudFinOpsEnv(task_id=3)
    env.step(TerminateInstanceAction(instance_id="i-rogue-1"))
    env.step(TerminateInstanceAction(instance_id="i-rogue-2"))
    result = env.step(RevokeIAMKeyAction(user_name="dev-john", access_key_id="dummy"))
    
    db_inst = next((i for i in result.observation.instances if i.instance_id == "i-db-prod"))
    web_inst = next((i for i in result.observation.instances if i.instance_id == "i-webapp-prod"))
    
    assert db_inst.state == "running"
    assert web_inst.state == "running"


# --- GENERAL LIFECYCLE TESTS ---

def test_reset_restores_state():
    """Verify completing actions naturally reset upon calling reset()."""
    env = CloudFinOpsEnv(task_id=1)
    env.step(ReleaseElasticIPAction(allocation_id="eip-001"))
    env.step(ReleaseElasticIPAction(allocation_id="eip-002"))
    env.step(ReleaseElasticIPAction(allocation_id="eip-003"))
    
    # State reset
    env.reset()
    result = env.step(NoOpAction())
    
    assert result.reward == 0.0
    assert len(result.observation.elastic_ips) == 4

def test_step_limit():
    """Verify taking sequential no-op actions natively trips the MAX_STEPS timeout feature."""
    env = CloudFinOpsEnv(task_id=1)
    
    # Run exact iterations needed to match max limit
    for _ in range(env.max_steps):
        result = env.step(NoOpAction())
        
    assert result.done is True
    assert result.info.get("message") == "Max steps reached"

def test_billing_spend_decreases():
    """Verify that terminating an expensive instance decreases the total monthly spend."""
    env = CloudFinOpsEnv(task_id=3)
    initial_spend = env.current_state.billing_summary.total_monthly_spend
    
    # Terminate i-rogue-1 ($2000/mo)
    env.step(TerminateInstanceAction(instance_id="i-rogue-1"))
    
    new_spend = env.current_state.billing_summary.total_monthly_spend
    assert new_spend < initial_spend
    assert new_spend == round(initial_spend - 2000.0, 2)

def test_billing_downsize_decreases():
    """Verify that downsizing an instance decreases the total monthly spend."""
    env = CloudFinOpsEnv(task_id=2)
    initial_spend = env.current_state.billing_summary.total_monthly_spend
    
    # Downsize i-db-prod from xlarge to medium
    # xlarge: 120.0
    # medium: 20.0
    env.step(DownsizeInstanceAction(instance_id="i-db-prod", new_instance_type="t3.medium"))
    
    new_spend = env.current_state.billing_summary.total_monthly_spend
    assert new_spend < initial_spend
    assert new_spend == round(initial_spend - 100.0, 2)
