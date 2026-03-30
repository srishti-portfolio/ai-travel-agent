print("MCP SERVER STARTED")
import asyncio
import json
import os
import requests
from dotenv import load_dotenv

from mcp import types as mcp_types
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type

load_dotenv()
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# -------- TOOLS --------

def get_places(city: str):
  url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query=tourist+places+in+{city}&key={API_KEY}"
  res = requests.get(url).json()

  places = [p["name"] for p in res.get("results", [])[:10]]

  return {"places": places}

def get_directions(origin: str, destination: str):
  url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&key={API_KEY}"
  res = requests.get(url).json()

  route = res["routes"][0]["legs"][0]

  return {
    "distance": route["distance"]["text"],
    "duration": route["duration"]["text"]
  }


places_tool = FunctionTool(get_places)
directions_tool = FunctionTool(get_directions)

# -------- MCP SERVER --------

app = Server("tourist-mcp-server")

@app.list_tools()
async def list_tools():
  return [
    adk_to_mcp_tool_type(places_tool),
    adk_to_mcp_tool_type(directions_tool)
  ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):

  try:
    if name == places_tool.name:
      result = get_places(**arguments)

    elif name == directions_tool.name:
      result = get_directions(**arguments)

    else:
      result = {"message": "Tool not found"}

  except Exception as e:
    result = {"message": f"Error: {str(e)}"}

  # ALWAYS return valid MCP format
  return [
    mcp_types.TextContent(
      type="text",
      text=json.dumps(result)
    )
  ]

async def main():
  async with mcp.server.stdio.stdio_server() as (read, write):
    await app.run(
      read,
      write,
      InitializationOptions(
          server_name="tourist-server",
          server_version="1.0",
          capabilities=app.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={}
          ),
        ),
      )

if __name__ == "__main__":
  asyncio.run(main())