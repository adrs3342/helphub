from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import AIMessage, HumanMessage
from typing import TypedDict, List, Annotated
import os
load_dotenv()
SERVERS = {
    "Tickets": {
        "transport": "stdio",
        "command" : "/Library/Frameworks/Python.framework/Versions/3.10/bin/uv",
        "args" : [
            "run",
            "fastmcp",
            "run",
            "/Users/adarshsharma/projects/helphub/mcp_srvo.py"
        ]
    }
}

class State(TypedDict):
    messages: Annotated[List, add_messages]

async def agent():
    client = MultiServerMCPClient(SERVERS)
    llm = AzureChatOpenAI(
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        api_key = os.getenv("AZURE_OPENAI_KEY"),
        api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    )
    tools = await client.get_tools()
    llm_with_tool = llm.bind_tools(tools=tools)

    
    graph = StateGraph(State)

    async def llm_node(state:State):
        resp = await llm_with_tool.ainvoke(state["messages"])
        return {"messages": [resp]}
    
    tool_node = ToolNode(tools=tools)

    graph.add_node("llm", llm_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "llm")
    graph.add_conditional_edges("llm", tools_condition)
    graph.add_edge("tools", "llm")
    agent = graph.compile()

    return agent


if __name__ == "__main__":
    asyncio.run(agent())