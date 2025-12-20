import os
import asyncio
import json
from dotenv import load_dotenv
from typing import Dict, Any, List

load_dotenv()

# ADK Imports
# specific imports dependent on google-adk package structure
try:
    from google.adk.agents import Agent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.tools import google_search
    from google.genai import types
    from google.adk.models import Gemini
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

    async def run_task(self, task_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a task using the ADK Agent.
        Returns a dictionary with 'report' and 'new_context'.
        """
        try:
            task_name = task_config.get("name", "Unknown Task")
            task_definition = task_config.get("task_definition", task_config.get("prompt", ""))
            
            # Context is now expected to be a JSON object (dict), but handle legacy string just in case
            context_data = task_config.get("context", {})
            if isinstance(context_data, str) and context_data:
                # Legacy support or simple string
                context_str = context_data
            else:
                context_str = json.dumps(context_data, indent=2)

            tool_names = task_config.get("tools", [])
            model_name = task_config.get("model", "gemini-2.5-flash-lite") 

            logger.info(f"Starting execution for task: {task_name}")

            # Construct Core System Prompt
            system_instruction = (
                "You are an Asynchronous Task Agent. Your goal is to execute tasks over multiple iterations.\n\n"
                "1. State Awareness: Every run, you receive a task_definition and a context (your memory). "
                "Read the context to understand what was achieved in previous runs.\n"
                "2. Execution: Perform the specific actions required by the task_definition using available tools.\n"
                "3. Feedback Loop: After execution, you must determine what is left to do.\n"
                "4. Output Format: You must always return two distinct blocks:\n\n"
                "USER_REPORT: A human-readable summary of what you did.\n\n"
                "NEW_MEMORY: A structured JSON object that updates the context field for your next run. "
                "Ensure you include 'Next Steps' or 'Open Actions' for your future self."
            )

            # Construct User Message
            user_message = (
                f"TASK DEFINITION:\n{task_definition}\n\n"
                f"CURRENT CONTEXT (MEMORY):\n{context_str}\n\n"
                "Please execute the task and provide the USER_REPORT and NEW_MEMORY."
            )

            tools = self._get_tools(tool_names)

            # Define Model Explicitly to pass API Key
            model = Gemini(model=model_name, api_key=os.getenv("GOOGLE_API_KEY"))

            agent = Agent(
                name=task_name.replace(" ", "_").lower(),
                model=model,
                description=f"Agent for task: {task_name}",
                instruction=system_instruction,
                tools=tools
            )

            # Unique session info for this run
            app_name = f"async_agent_{task_name}"
            user_id = "scheduler_user"
            session_id = f"sess_{os.urandom(4).hex()}"

            session_service = InMemorySessionService()
            session = await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
            runner = Runner(agent=agent, app_name=app_name, session_service=session_service)

            content = types.Content(role='user', parts=[types.Part(text=user_message)])
            
            logger.info(f"Sending prompt to agent for task '{task_name}'...")
            
            final_response_text = ""
            events = runner.run_async(user_id=user_id, session_id=session_id, new_message=content)

            async for event in events:
                if event.is_final_response():
                    final_response_text = event.content.parts[0].text
                    logger.info("Task execution completed successfully.")

            # Parse Output
            report = ""
            new_memory = {}

            if "USER_REPORT:" in final_response_text:
                parts = final_response_text.split("USER_REPORT:")
                # usually parts[0] is empty or intro, parts[1] is the rest.
                # But we also have NEW_MEMORY somewhere.
                # Let's try a regex or simple split.
                remaining = parts[1]
                if "NEW_MEMORY:" in remaining:
                    report_part, memory_part = remaining.split("NEW_MEMORY:")
                    report = report_part.strip()
                    
                    # Robust JSON extraction
                    import re
                    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", memory_part, re.DOTALL)
                    
                    clean_memory = ""
                    if json_match:
                        clean_memory = json_match.group(1)
                    else:
                        # Fallback: try to find the first { and last }
                        start_idx = memory_part.find("{")
                        end_idx = memory_part.rfind("}")
                        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                            clean_memory = memory_part[start_idx:end_idx+1]
                        else:
                            clean_memory = memory_part.strip() # Hope for the best

                    try:
                        if not clean_memory:
                            raise ValueError("Empty memory block found")
                        new_memory = json.loads(clean_memory)
                    except Exception as e:
                        logger.error(f"Failed to parse NEW_MEMORY JSON. Raw content prefix: {memory_part[:100]}... Error: {e}")
                        # Fallback: keep old context if parsing fails? Or save error?
                        new_memory = context_data # Preserve old context
                        report += f"\n\n[SYSTEM ERROR: Failed to parse NEW_MEMORY. {str(e)}]"
                else:
                    report = remaining.strip()
                    logger.warning("NEW_MEMORY block missing from response.")
            else:
                # Fallback if format not followed
                report = final_response_text
                logger.warning("USER_REPORT block missing from response.")

            return {
                "report": report,
                "new_context": new_memory
            }

        except Exception as e:
            logger.error(f"Error executing task {task_config.get('name')}: {e}", exc_info=True)
            return {
                "report": f"Error executing task: {str(e)}",
                "new_context": task_config.get("context", {}) # No change on error
            }

# Synchronous wrapper if needed
def run_task_sync(task_config: Dict[str, Any]) -> Dict[str, Any]:
    return asyncio.run(TaskRunner().run_task(task_config))
