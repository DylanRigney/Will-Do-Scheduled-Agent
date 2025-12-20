from google.adk.agents import Agent
import inspect
import sys

print("Agent __init__ signature:")
try:
    print(inspect.signature(Agent.__init__))
except Exception as e:
    print(e)

print("\nAgent docstring:")
print(Agent.__doc__)
