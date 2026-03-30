import os
from dotenv import load_dotenv

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import (
  MCPToolset,
  StdioServerParameters,
  StdioConnectionParams,
)
from google.adk.models import Gemini

# Load environment variables
load_dotenv()

MODEL = os.getenv("MODEL")

# ---- ADK AGENT (uses MCP tools) ----
root_agent = LlmAgent(
  model=Gemini(model=MODEL),
  name="tourist_agent",
  instruction="""
  You are a tourist assistant.

  IMPORTANT:
  - ALWAYS use available tools to answer user queries.
  - NEVER answer without calling a tool.

  If user asks:
  - "tourist places" → call get_places(city)
  - "directions" → call get_directions(origin, destination)

  After calling the tool:
  - Read the result
  - Convert it into a clear human-friendly response

  If tool returns error:
  - Tell user politely

  DO NOT stay silent.
  """,
  tools=[
    MCPToolset(
      connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
          command="python",
          args=["./app/adk_mcp_server/server.py"],  # path to your MCP server
          env={
              # pass env vars to MCP server if needed
              "GOOGLE_MAPS_API_KEY": os.getenv("GOOGLE_MAPS_API_KEY"),
          },
        ),
          timeout=20,
      )
    )
  ],
)

# expose variable name used by ADK runner
agent = root_agent