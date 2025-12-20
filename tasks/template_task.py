# Task Template
# Copy this dictionary structure to create new tasks.
# Comments explain the purpose of each field.

template_task = {
    # Unique name of the task.
    "name": "Template Task",

    # How often to repeat. 
    # Options: 'daily', 'weekly', 'monthly', 'X days' (e.g. '3 days'), 'X weeks' (e.g. '2 weeks'), 'X months' (e.g. '3 months').
    "frequency": "daily",

    # Datetime string (YYYY-MM-DDTHH:MM) for the next execution. Seconds are ignored.
    # Special values:
    # - "Now": Runs immediately, then schedules based on frequency.
    # - None (or null/blank): Defaults to running in 'frequency' time from now at 7:00 AM.
    # - Date only (YYYY-MM-DD): Defaults to 7:00 AM on that date.
    # - Time is optional (HH:MM), defaults to 00:00 if omitted (unless date-only rule applies).
    "next_run": None,

    # Natural language instructions for the agent.
    "task_definition": "Describe what you want the agent to do here.",

    # Structured context from previous runs. 
    # The agent's NEW_MEMORY from the last run will be saved here.
    "context": {
        "knowledge_base": "Initial knowledge...",
        "iteration_count": 0
    },
    
    # Optional: File path for the human-readable report.
    # If omitted, defaults to task_results/{task_name}/{timestamp}.txt
    "output": "reports/my_task_report.md",

    # List of tools to use. Available: 'google_search'.
    "tools": [
        "google_search"
    ],

    # Model to use. Default: 'gemini-2.5-flash-lite'.
    # Valid options include: 'gemini-2.5-flash', 'gemini-2.5-flash-lite'.
    "model": "gemini-2.5-flash-lite"
}
