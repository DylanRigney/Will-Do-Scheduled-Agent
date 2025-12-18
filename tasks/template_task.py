# Task Template
# Copy this dictionary structure to create new tasks.
# Comments explain the purpose of each field.

template_task = {
    # Unique name of the task.
    "name": "Template Task",

    # How often to repeat. 
    # Options: 'daily', 'weekly', 'monthly', 'X days' (e.g. '3 days'), 'X weeks' (e.g. '2 weeks').
    "frequency": "daily",

    # ISO 8601 Datetime string (YYYY-MM-DDTHH:MM:SS) for the next execution.
    # Set to None to disable or for templates.
    "next_run": None,

    # Natural language instructions for the agent.
    "prompt": "Describe what you want the agent to do here.",

    # List of tools to use. Available: 'google_search'.
    "tools": [
        "google_search"
    ],

    # Model to use. Default: 'gemini-2.0-flash'.
    "model": "gemini-2.0-flash"
}
