import json
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from src.env import CloudFinOpsEnv
from src.models import (
    Observation, StepResult,
    TerminateInstanceAction, DownsizeInstanceAction, ReleaseElasticIPAction,
    RevokeIAMKeyAction, ApplyTagAction, BlockIPAction, NoOpAction
)

app = FastAPI(title="Cloud FinOps & Security Simulator API")

# Store one CloudFinOpsEnv instance per task_id completely in memory
# No external state or lifespan events used.
envs_dict: Dict[int, CloudFinOpsEnv] = {}

ACTION_MODELS = {
    "terminate_instance": TerminateInstanceAction,
    "downsize_instance": DownsizeInstanceAction,
    "release_elastic_ip": ReleaseElasticIPAction,
    "revoke_iam_key": RevokeIAMKeyAction,
    "apply_tag": ApplyTagAction,
    "block_ip": BlockIPAction,
    "no_op": NoOpAction
}

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Returns an HTTP 200 HTML dashboard displaying live task stats (CRITICAL for uptime bots)."""
    stats_html = "<h2>Active tasks</h2><ul>"
    if not envs_dict:
        stats_html += "<li><p>No tasks initialized yet. Use <code>POST /reset?task_id=1</code> to begin.</p></li>"
    else:
        for tid, env in envs_dict.items():
            state = env.state()
            score = env._grade()
            steps = env.current_step
            max_steps = env.max_steps
            spend = state.billing_summary.total_monthly_spend
            
            stats_html += f"""
            <li class="task-card">
                <h3>Task ID: {tid}</h3>
                <p><strong>Score:</strong> {score:.2f} / 1.00</p>
                <p><strong>Steps:</strong> {steps} / {max_steps}</p>
                <p><strong>Current Spend:</strong> ${spend:.2f}</p>
            </li>
            """
    stats_html += "</ul>"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Cloud FinOps & Security Simulator</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #1e293b; padding: 2rem; max-width: 800px; margin: 0 auto; }}
            h1 {{ color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 1rem; margin-bottom: 2rem; }}
            h2 {{ color: #334155; }}
            ul {{ list-style-type: none; padding: 0; }}
            .task-card {{ background: white; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); padding: 1.5rem; margin-bottom: 1.5rem; border-left: 5px solid #3b82f6; }}
            .task-card h3 {{ margin-top: 0; color: #1d4ed8; }}
            .task-card p {{ margin: 0.5rem 0; font-size: 1.1rem; }}
        </style>
    </head>
    <body>
        <h1>Cloud FinOps & Security Simulator</h1>
        {stats_html}
    </body>
    </html>
    """
    return html_content

@app.post("/reset", response_model=Observation)
async def reset_env(task_id: int):
    """Resets the environment for a specific task_id and returns the observation."""
    if task_id not in envs_dict:
        envs_dict[task_id] = CloudFinOpsEnv(task_id=task_id)
    return envs_dict[task_id].reset()

@app.get("/state", response_model=Observation)
async def get_state(task_id: int):
    """Gets the current environment state for a specific task_id."""
    if task_id not in envs_dict:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not initialized")
    return envs_dict[task_id].state()

@app.post("/step", response_model=StepResult)
async def step_env(task_id: int, request: Request):
    """Applies an action and advances the environment by one step for a given task_id."""
    if task_id not in envs_dict:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not initialized")
        
    try:
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8')
        print(f"[SERVER DEBUG] Raw body received: {body_str}")
        body = json.loads(body_str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {str(e)}")
        
    action_type = body.get("action_type")
    print(f"[SERVER DEBUG] Parsed action_type: {action_type}")
    
    if not action_type:
        raise HTTPException(status_code=400, detail="Missing 'action_type' field in JSON body")
        
    if action_type not in ACTION_MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown action_type: {action_type}. Supported actions are: {list(ACTION_MODELS.keys())}")
        
    model_cls = ACTION_MODELS[action_type]
    try:
        # Validate action dict into its corresponding Pydantic Action model
        action = model_cls(**body)
    except ValidationError as e:
        # Return cleanly parsed 422 standard validation errors from Pydantic
        raise HTTPException(status_code=422, detail=e.errors())
        
    return envs_dict[task_id].step(action)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
