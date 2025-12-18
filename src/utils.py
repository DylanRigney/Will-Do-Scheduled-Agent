import os
import logging
import datetime
from dateutil import parser
from dateutil.relativedelta import relativedelta

def setup_logging(name: str, log_dir: str = "logs") -> logging.Logger:
    """Configures and returns a logger."""
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Check if handlers already exist to avoid duplicate logs
    if not logger.handlers:
        file_handler = logging.FileHandler(os.path.join(log_dir, f"{name}.log"))
        console_handler = logging.StreamHandler()
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
    return logger

def calculate_next_run(current_run_iso: str, frequency: str) -> str:
    """
    Calculates the next run time based on frequency.
    Supported frequencies: 'daily', 'weekly', 'monthly', 'X days', 'X weeks'.
    """
    current_run = parser.isoparse(current_run_iso)
    now = datetime.datetime.now(current_run.tzinfo)
    
    # If the current run time is in the future, we still calculate relative to it 
    # to maintain the schedule (e.g. every Monday), 
    # UNLESS it's way in the past, in which case we might want to catch up used 'now'.
    # For this strict scheduler, we increment from the *scheduled* time to keep cadence.
    
    base_time = current_run
    
    freq_lower = frequency.lower()
    
    if freq_lower == 'daily':
        next_time = base_time + relativedelta(days=1)
    elif freq_lower == 'weekly':
        next_time = base_time + relativedelta(weeks=1)
    elif freq_lower == 'monthly':
        next_time = base_time + relativedelta(months=1)
    elif 'day' in freq_lower:
        # naive parsing for "2 days", "3 days"
        try:
            parts = freq_lower.split()
            amount = int(parts[0])
            next_time = base_time + relativedelta(days=amount)
        except (ValueError, IndexError):
            # Fallback
            next_time = base_time + relativedelta(days=1)
    elif 'week' in freq_lower:
         try:
            parts = freq_lower.split()
            amount = int(parts[0])
            next_time = base_time + relativedelta(weeks=amount)
         except (ValueError, IndexError):
            next_time = base_time + relativedelta(weeks=1)
    else:
        # Default fallback
        next_time = base_time + relativedelta(days=1)

    return next_time.isoformat()

def save_task_result(task_name: str, result_content: str, base_dir: str = "task_results"):
    """Saves the task result to a structured folder."""
    task_dir = os.path.join(base_dir, task_name)
    if not os.path.exists(task_dir):
        os.makedirs(task_dir)
        
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{timestamp}.txt"
    file_path = os.path.join(task_dir, filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(result_content)
    
    return file_path
