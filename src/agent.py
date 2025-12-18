import os
import asyncio
from typing import Dict, Any, List

# ADK Imports
# specific imports dependent on google-adk package structure
try:
    from google.adk.agents import Agent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.tools import google_search
    from google.genai import types
except ImportError:
    # Fail gracefully if ADK not installed yet so other parts can be tested
    print("Warning: ADK libraries not found. Agent execution will fail.")

from .utils import setup_logging

logger = setup_logging("TaskRunner")

class TaskRunner:
    def __init__(self):
        self.tool_map = {
            "google_search": google_search,
            # Add more tools here as needed
        }

    def _get_tools(self, tool_names: List[str]) -> List[Any]:
        tools = []
        for name in tool_names:
            if name in self.tool_map:
                tools.append(self.tool_map[name])
            else:
                logger.warning(f"Tool '{name}' not found in tool_map.")
        return tools

    async def run_task(self, task_config: Dict[str, Any]) -> str:
        """
        Executes a task using the ADK Agent.
        """
        try:
            task_name = task_config.get("name", "Unknown Task")
            prompt = task_config.get("prompt", "")
            tool_names = task_config.get("tools", [])
            model_name = task_config.get("model", "gemini-2.0-flash") # Default to flash

            logger.info(f"Starting execution for task: {task_name}")

            tools = self._get_tools(tool_names)

            agent = Agent(
                name=task_name.replace(" ", "_").lower(),
                model=model_name,
                description=f"Agent for task: {task_name}",
                instruction="You are an automated task agent. Execute the user's request precisely.",
                tools=tools
            )

            # Unique session info for this run
            app_name = f"will_do_{task_name}"
            user_id = "scheduler_user"
            session_id = f"sess_{os.urandom(4).hex()}"

            session_service = InMemorySessionService()
            session = await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
            runner = Runner(agent=agent, app_name=app_name, session_service=session_service)

            content = types.Content(role='user', parts=[types.Part(text=prompt)])
            
            logger.info(f"Sending prompt to agent: {prompt[:50]}...")
            
            final_response_text = ""
            events = runner.run_async(user_id=user_id, session_id=session_id, new_message=content)

            async for event in events:
                if event.is_final_response():
                    final_response_text = event.content.parts[0].text
                    logger.info("Task execution completed successfully.")

            return final_response_text

        except Exception as e:
            logger.error(f"Error executing task {task_config.get('name')}: {e}", exc_info=True)
            return f"Error: {str(e)}"

# Synchronous wrapper if needed
def run_task_sync(task_config: Dict[str, Any]) -> str:
    return asyncio.run(TaskRunner().run_task(task_config))
