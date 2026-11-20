from typing import Literal
from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain_core.messages import AnyMessage, SystemMessage, ToolMessage, HumanMessage
from typing_extensions import TypedDict, Annotated
import operator
from openai import OpenAI
import requests
import json



from dotenv import load_dotenv
import json
import requests
from utils.logger import get_logger
import os
from langchain.tools import tool
from langchain_openai import OpenAIEmbeddings
import chromadb
import pandas as pd

from assignment_chat.normalize import normalize_location
from assignment_chat.utils import clean_job_response

_logs = get_logger(__name__)

load_dotenv(".env")
load_dotenv(".secrets")



###################################################### TOOLS DEFINITIONS

#SERVICE 1 -> Using the job opportunity API as a tool 
# Extracts the params from the query and makes an api call 
# If results are not available wit all the params given by the user
# The search is broadend in "attempts"
# JOB: There is a small issue with api when calling multiple cities
@tool
def get_job_listings(
    title: str,
    city: str = "Toronto",
    remote: str = "hybrid",
    seniority: str = "mid,senior",
    limit: int = 5,
) -> str:
    """Fetch job listings from the job opportunities API for a title, city, remote type, seniority, and result limit.

    Args:
        title: The job title to search for.
        city: The city to target, such as Toronto or Montreal.
        remote: Work arrangement such as hybrid, remote, or onsite.
        seniority: Seniority filter such as mid,senior.
        limit: Maximum number of jobs to return.

    Returns:
        A formatted string of matching job listings.
    """
    if not title or not title.strip():
        return "Please provide a job title to search for."

    if limit > 5:
        limit = 5

    country, region, resolved_city = normalize_location(city)
    print(f"Country & region codes extracted from cities: {country} & {region} for {resolved_city}")

    base_url = "https://api.jobopportunitiesapi.org"
    headers = {"Accept": "application/json"}
    api_key = os.getenv("JOB_API")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    attempts = [
        {
            "country": country,
            "title": title,
            "region": region,
            "city": resolved_city,
            "remote": remote,
            "seniority": seniority,
            "limit": limit,
        },
        {
            "country": country,
            "title": title,
            "region": region,
            "limit": limit,
        },
        {
            "country": country,
            "title": title,
            "limit": limit,
        },
    ]

    for idx, params in enumerate(attempts, start=1):
        clean_params = {k: v for k, v in params.items() if v is not None and v != ""}
        try:
            response = requests.get(
                f"{base_url}/v1/jobs",
                headers=headers,
                params=clean_params,
                timeout=30,
            )
            print(f"API returned {response.status_code} on attempt {idx}, params {clean_params}")
        except requests.RequestException as exc:
            print(f"Request failed on attempt {idx}: {exc}")
            continue

        if response.status_code != 200:
            continue

        try:
            payload = response.json()
        except ValueError:
            print(f"API response on attempt {idx} was not valid JSON.")
            continue

        jobs = payload.get("data") or payload.get("jobs") or []
        if jobs:
            return clean_job_response(jobs)

    return (
        "No jobs were found for this search. "
        "Please try a different job title, city, region, country, or remote preference."
    )


#SERVICE 2 -> Multiple tables hugging face dataset Nason/onet-database is used load
# Job title, essential skills, transferable skills and descriptions into chroma db with persistence
# Please refer to embeddings.ipynb - extensive notebook that brings multiple tables
# Constructs a list of document, embedding is performed by open AI in batches and stored in chroma db
# Can run in the Docker service if persistent client is not used
# DATASET - https://huggingface.co/datasets/Nason/onet-database
@tool 
def semantic_job_query(
    query: str, 
    n_results: int = 5
):
    """Search the stored job-skill database for similar skills and role requirements.

    Args:
        query: A job title, skill, or short description to match against the database.
        n_results: Number of matching skill entries to return.

    Returns:
        A list of semantically similar skills or job requirements with metadata.
    """

    client = chromadb.PersistentClient(path="./chromadb_store")
    collection = client.get_or_create_collection("essential_skills")

    results = collection.query(query_texts=[query], n_results=n_results)

    cleaned = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        cleaned.append({
            "title": meta.get("title"),
            "onet_soc_code": meta.get("onet_soc_code"),
            "distance": float(dist),
            "document": doc,
            "metadata": meta
        })

    return cleaned


#SERVICE 3 - Uses the same jobs api -> provides a summary in the area based on the params
@tool
def get_job_market_summary(
    title: str,
    city: str = "Toronto",
    limit: int = 5
) -> str:
    """Return a short job-market summary for a role in a given city.

    Args:
        title: The job title to summarize.
        city: The city to search within.
        limit: Number of jobs to use for the summary.

    Returns:
        A concise summary of total jobs and sample titles in the market.
    """
    if not title or not title.strip():
        return "Please provide a job title."

    country, region, resolved_city = normalize_location(city)

    base_url = "https://api.jobopportunitiesapi.org"
    headers = {"Accept": "application/json"}
    api_key = os.getenv("JOB_API")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    params = {
        "country": country,
        "title": title,
        "region": region,
        "city": resolved_city,
        "limit": limit,
    }

    try:
        response = requests.get(
            f"{base_url}/v1/jobs",
            headers=headers,
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        jobs = payload.get("data") or payload.get("jobs") or []

        if not jobs:
            return f"No job opportunities found for {title} in {resolved_city}."

        total = len(jobs)
        remote_count = sum(1 for j in jobs if "remote" in str(j).lower())
        top_titles = [job.get("title") for job in jobs[:3] if job.get("title")]

        return (
            f"Job market snapshot for '{title}' in {resolved_city}:\n"
            f"- Total jobs returned: {total}\n"
            f"- Remote-friendly roles: {remote_count}\n"
            f"- Sample titles: {', '.join(top_titles)}"
        )

    except Exception as exc:
        return f"Unable to fetch job snapshot: {exc}"
    


########################################### LLM SETUP
#Augment the LLM with all the tools defined 
def augmented_model(
        tools
        ):

    model = init_chat_model(
    "openai:gpt-4o-mini",
    temperature=0.9,
    api_key=os.getenv("OPENAI_API_KEY")
)

    return model.bind_tools(tools)


def llm_call(state: dict):
    """LLM decides whether to call a tool or not"""
    model_with_tools = augmented_model(
        tools = [get_job_listings, semantic_job_query, get_job_market_summary]
    )
    return {
        "messages": [
            model_with_tools.invoke(
                [
                    SystemMessage(
                        content="You are a helpful and empathetic job search assistant tasked with finding localized job listings and essential skills needed for jobs"
                    )
                ]
                + state["messages"]
            )
        ],
        "llm_calls": state.get('llm_calls', 0) + 1
    }

######################################### TOOL NODES

def tool_node(state: dict):
    """Performs the tool call"""

    tools = [get_job_listings, semantic_job_query, get_job_market_summary]
    tools_by_name = {tool.name: tool for tool in tools}

    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
    return {"messages": result}

########################################## END CONDITION
class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int

def should_continue(state: MessagesState):
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    messages = state["messages"]
    last_message = messages[-1]

    # If the LLM makes a tool call, then perform an action
    if last_message.tool_calls:
        return "tool_node"

    # Otherwise, we stop (reply to the user)
    return END

def assignment_agent():
    """Builds the agent graph"""    

    agent_builder = StateGraph(MessagesState)

    # Add nodes
    agent_builder.add_node("llm_call", llm_call)
    agent_builder.add_node("tool_node", tool_node)

    # Add edges to connect nodes
    agent_builder.add_edge(START, "llm_call")
    agent_builder.add_conditional_edges(
                            "llm_call",
                            should_continue,
                            ["tool_node", END]
                        )
    agent_builder.add_edge("tool_node", "llm_call")

    # Compile the agent
    agent = agent_builder.compile()

    return agent
   
   

