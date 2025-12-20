import os
import json
import datetime
import asyncio
import shutil
import tempfile
import sys

# Add src to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dateutil import parser
from src.scheduler import TaskScheduler

async def mock_run_task(task_config):
    print(f"MOCK running task: {task_config['name']}")
    return {
        "report": "Mock Result Content",
        "new_context": {"last_run": "success", "data": 123}
    }

def test_scheduler_logic_safe():
    print("Setting up safe test environment...")
    
    # Create a temporary directory for tasks
    temp_dir = tempfile.mkdtemp()
    tasks_dir = os.path.join(temp_dir, "tasks")
    os.makedirs(tasks_dir)
    
    # Create a dummy task in the temp dir
    test_task_path = os.path.join(tasks_dir, "test_task.json")
    now_iso = datetime.datetime.now().isoformat()
    past_iso = (datetime.datetime.now() - datetime.timedelta(hours=1)).isoformat()
    
    task_data = {
        "name": "Test Task",
        "frequency": "1 day",
        "next_run": past_iso,
        "prompt": "Do nothing",
        "tools": [],
        "context": {}
    }
    
    with open(test_task_path, "w") as f:
        json.dump(task_data, f)

    try:
        # Initialize scheduler with the TEMP directory
        scheduler = TaskScheduler(tasks_dir=tasks_dir, check_interval=1)
        # Monkey patch runner
        scheduler.runner.run_task = mock_run_task
        
        print(f"Running scheduler process_tasks() in {tasks_dir}...")
        asyncio.run(scheduler.process_tasks())
        
        # Verify Next Run Update
        with open(test_task_path, "r") as f:
            updated_task = json.load(f)
            
        old_run = parser.isoparse(past_iso)
        new_run = parser.isoparse(updated_task["next_run"])
        
        if new_run > old_run:
             print(f"PASS: next_run updated to {new_run}")
        else:
             print(f"FAIL: next_run not updated properly. Got {new_run}")

        # Verify Context Update
        expected_context = {"last_run": "success", "data": 123}
        if updated_task.get("context") == expected_context:
             print("PASS: Context updated successfully.")
        else:
             print(f"FAIL: Context not updated. Got {updated_task.get('context')}")

    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir)
        print("Safe test complete. Temp files removed.")

if __name__ == "__main__":
    test_scheduler_logic_safe()
