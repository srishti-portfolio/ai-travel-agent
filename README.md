# AI Travel Agent (ADK + MCP)

## Overview
This project builds an AI agent using Google ADK that connects to external tools via Model Context Protocol (MCP).

The agent retrieves real-time data from Google Maps API and uses it in responses.

## Features
- Tourist places search
- Distance between locations and time taken to reach the location
- MCP-based tool integration

## Architecture
User → ADK Agent → MCP → Google Maps API → Response

## Deployment
Deployed on Google Cloud Run.

## API Endpoint
POST /chat

Example:
{
  "message": "Show me tourist places in Ranchi"
}

## Tech Stack
- Google ADK
- MCP
- Gemini 2.5 Flash
- Google Maps API
