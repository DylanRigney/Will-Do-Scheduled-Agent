import os
import json
import time
import datetime
from dateutil import parser
import asyncio

from .agent import TaskRunner
from .utils import setup_logging, calculate_next_run, save_task_result, normalize_next_run

# We will initialize logger inside the class or after we know the root dir, 
# BUT for module level logging, we might default to standard behavior.
# Better practice: Initialize logger in __init__ or use a default that works.
# For now, we keep module level but maybe we re-configure it in __init__?
# A simple way is to lazily setup logging or just let the first call win.
# Let's modify setup_logging usage.

class TaskScheduler:
    def __init__(self, tasks_dir: str = "tasks", check_interval: int = 3600, task_delay: int = 10, root_dir: str = None):
        self.root_dir = root_dir
        
        # If root_dir is provided and tasks_dir is relative, join them
        if self.root_dir and not os.path.isabs(tasks_dir):
            self.tasks_dir = os.path.join(self.root_dir, tasks_dir)
        else:
            self.tasks_dir = tasks_dir

        self.check_interval = check_interval
        self.task_delay = task_delay # Delay in seconds between sequential tasks
        self.runner = TaskRunner()
        self.running = False
        
        # Re-setup logging with correct path if root_dir is known
        global logger
        logger = setup_logging("Scheduler", root_dir=self.root_dir)

    def load_tasks(self):
        """Yields (filename, task_data) for all valid JSON tasks."""
        if not os.path.exists(self.tasks_dir):
            logger.warning(f"Tasks directory {self.tasks_dir} does not exist.")
            return

        for filename in os.listdir(self.tasks_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.tasks_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        task_data = json.load(f)
                        yield filepath, task_data, filename
                except Exception as e:
                    logger.error(f"Failed to load task {filename}: {e}")

    async def process_tasks(self):
        """Checks all tasks and runs them if due."""
        logger.info("Checking for due tasks...")
        now = datetime.datetime.now().astimezone() # Aware datetime

        tasks_run_count = 0

        for filepath, task, filename in self.load_tasks():
            name = task.get("name", filename)
            raw_next_run = task.get("next_run")
            frequency = task.get("frequency", "daily")
            
            # Normalize next_run (handles "Now", None, Date-only, etc.)
            try:
                normalized_next_run = normalize_next_run(raw_next_run, frequency)
            except Exception as e:
                logger.error(f"Failed to normalize next_run for {name}: {e}")
                continue
            
            # If normalization changed the value (e.g. "Now" -> timestamp, or None -> future date), 
            # save it back to the file immediately.
            if normalized_next_run != raw_next_run:
                logger.info(f"Normalizing 'next_run' for task '{name}': '{raw_next_run}' -> '{normalized_next_run}'")
                task["next_run"] = normalized_next_run
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(task, f, indent=4)
                except Exception as e:
                    logger.error(f"Failed to save normalized task {name}: {e}")
                    # Continue using the normalized value in memory
            
            # Now proceed with standard checking
            next_run_str = task["next_run"]
            
            try:
                next_run = parser.isoparse(next_run_str)
                # Ensure next_run is aware if possible, or assume local
                if next_run.tzinfo is None:
                    next_run = next_run.replace(tzinfo=now.tzinfo)

                if now >= next_run:
                    # If we have already run a task in this cycle, pause before the next one
                    if tasks_run_count > 0:
                        logger.info(f"Pausing for {self.task_delay} seconds before next task to reduce system load...")
                        await asyncio.sleep(self.task_delay)

                    logger.info(f"Task '{name}' is due (Next run: {next_run_str}). Executing...")
                    
                    # Execute Task
                    result_data = await self.runner.run_task(task)
                    tasks_run_count += 1
                    
                    report = result_data.get("report", "")
                    new_context = result_data.get("new_context", {})
                    
                    # Save Result (Report)
                    output_path = task.get("output")
                    saved_path = save_task_result(name, report, output_path=output_path, root_dir=self.root_dir)
                    
                    # Logging raw result for debug purpose
                    logger.info(f"Task result saved to: {saved_path}")
                    
                    if "Error" in report and len(report) < 200: 
                        # intense error check, but be careful not to flag generic text. 
                        # If the report is JUST an error message, we might want to retry?
                        # For now, let's assume if we got a report, we succeeded, unless it's the specific "Error executing..." fallback
                        if report.startswith("Error executing task:"):
                             logger.warning(f"Task '{name}' failed with system error. Schedule will NOT be updated. Will retry next cycle.")
                             continue

                    # Update Context with the result (learning/research loop)
                    task["context"] = new_context
                    
                    # If we have a delta history, we might want to append? 
                    # The prompt says "NEW_MEMORY: ... updates the context field". 
                    # So we assume the agent returns the FULL new context state, OR we merge?
                    # The prompt says: "A structured JSON object that updates the context field".
                    # Usually means "replace". Let's assume replace or the agent includes previous info if needed.
                    # Given the "State Awareness" prompt, the agent sees old context. 
                    # Use replace to allow agent to curate memory.

                    # Update Schedule ONLY on success
                    new_next_run = calculate_next_run(next_run_str, frequency)
                    task["next_run"] = new_next_run
                    
                    # Save Updated Task File
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(task, f, indent=4)
                        
                    logger.info(f"Task '{name}' completed successfully. Next run updated to {new_next_run}.")
                else:
                    # Debug log - usually too verbose for production but good for verifying loaded tasks
                    # logger.debug(f"Task '{name}' not due yet. Next run: {next_run_str}")
                    pass

            except Exception as e:
                logger.error(f"Error processing task {name}: {e}", exc_info=True)

    def start(self):
        """Starts the scheduling loop."""
        self.running = True
        logger.info(f"Scheduler started. Polling every {self.check_interval} seconds.")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            while self.running:
                loop.run_until_complete(self.process_tasks())
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user.")
        except Exception as e:
            logger.critical(f"Scheduler crashed: {e}", exc_info=True)
            
if __name__ == "__main__":
    # For testing, run with a shorter interval
    scheduler = TaskScheduler(check_interval=60)
    scheduler.start()
