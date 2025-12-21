import os
import logging
import datetime
from dateutil import parser
from dateutil.relativedelta import relativedelta

def setup_logging(name: str, log_dir: str = "logs", root_dir: str = None) -> logging.Logger:
    """Configures and returns a logger."""
    if root_dir:
        log_dir = os.path.join(root_dir, log_dir)

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

def get_frequency_delta(frequency: str) -> relativedelta:
    """Parses a frequency string into a relativedelta."""
    freq_lower = frequency.lower()
    
    if freq_lower == 'daily':
        return relativedelta(days=1)
    elif freq_lower == 'weekly':
        return relativedelta(weeks=1)
    elif freq_lower == 'monthly':
        return relativedelta(months=1)
    elif 'day' in freq_lower:
        try:
            parts = freq_lower.split()
            amount = int(parts[0])
            return relativedelta(days=amount)
        except (ValueError, IndexError):
            return relativedelta(days=1)
    elif 'week' in freq_lower:
         try:
            parts = freq_lower.split()
            amount = int(parts[0])
            return relativedelta(weeks=amount)
         except (ValueError, IndexError):
            return relativedelta(weeks=1)
    elif 'month' in freq_lower:
         try:
            parts = freq_lower.split()
            amount = int(parts[0])
            return relativedelta(months=amount)
         except (ValueError, IndexError):
            return relativedelta(months=1)
    else:
        # Default fallback
        return relativedelta(days=1)

def calculate_next_run(current_run_iso: str, frequency: str) -> str:
    """
    Calculates the next run time based on frequency.
    Supported frequencies: 'daily', 'weekly', 'monthly', 'X days', 'X weeks'.
    """
    current_run = parser.isoparse(current_run_iso)
    # Ensure current_run is naive if we are doing simple arithmetic or aware if needed, 
    # but relativedelta handles both fine. 
    
    delta = get_frequency_delta(frequency)
    next_time = current_run + delta
    return next_time.isoformat()

def normalize_next_run(next_run_val, frequency: str) -> str:
    """
    Parses and normalizes the 'next_run' field into a standard ISO 8601 string.
    Handles:
    - "Now" -> Returns current time (effectively triggers immediate run).
    - None/Empty -> Returns (Now + Frequency) at 07:00:00.
    - "YYYY-MM-DD" -> Returns "YYYY-MM-DDT07:00:00".
    - "YYYY-MM-DDTHH:MM" -> Returns "YYYY-MM-DDTHH:MM:00".
    - ISO strings -> Returns as is.
    """
    now = datetime.datetime.now().replace(microsecond=0)
    
    # Handle None or Empty
    if not next_run_val or (isinstance(next_run_val, str) and not next_run_val.strip()):
        delta = get_frequency_delta(frequency)
        future_date = now + delta
        # Default to 07:00 AM
        future_date = future_date.replace(hour=7, minute=0, second=0, microsecond=0)
        return future_date.isoformat()

    if isinstance(next_run_val, str):
        val_lower = next_run_val.strip().lower()
        
        # Handle "Now"
        if val_lower == "now":
            return now.isoformat()
        
        # Handle Date Only (YYYY-MM-DD) - Length 10
        if len(next_run_val.strip()) == 10 and "T" not in next_run_val:
            try:
                # Validate it's a date
                dt = parser.parse(next_run_val)
                # Set to 07:00 AM
                dt = dt.replace(hour=7, minute=0, second=0, microsecond=0)
                return dt.isoformat()
            except parser.ParserError:
                pass # Fall through to standard parser
                
        # Handle HH:MM without seconds (auto-handled by parser usually, but let's be safe)
        try:
            dt = parser.parse(next_run_val)
            return dt.isoformat()
        except Exception:
            # If parsing fails, fallback to None behavior or raise
            return next_run_val # Let the caller handle the error or it will fail later

    return str(next_run_val)

def save_task_result(task_name: str, result_content: str, base_dir: str = "task_results", output_path: str = None, root_dir: str = None) -> str:
    """
    Saves the task result.
    If output_path is provided, saves to that specific file (creating dirs if needed).
    Otherwise, saves to base_dir/task_name/timestamp.txt.
    If root_dir is provided, it is prepended to base_dir (if base_dir is relative) 
    or output_path (if output_path is relative).
    """
    if root_dir:
        # Prepend root_dir if the path is not already absolute
        if output_path and not os.path.isabs(output_path):
             output_path = os.path.join(root_dir, output_path)
        if base_dir and not os.path.isabs(base_dir):
             base_dir = os.path.join(root_dir, base_dir)

    if output_path:
        # Use custom path
        file_path = output_path
        # Ensure directory exists
        dir_name = os.path.dirname(file_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name)
    else:
        # Default behavior
        task_dir = os.path.join(base_dir, task_name)
        if not os.path.exists(task_dir):
            os.makedirs(task_dir)
            
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{timestamp}.txt"
        file_path = os.path.join(task_dir, filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(result_content)
    
    return file_path
