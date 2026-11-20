import gradio as gr
from assignment_chat.main_langchain import assignment_agent
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
from typing import Optional
import os

from utils.logger import get_logger



_logs = get_logger(__name__)

load_dotenv('.secrets')
llm_agent = None

def get_agent():
    global llm_agent
    if llm_agent is None:
        llm_agent = assignment_agent()
    return llm_agent

#The agent needs a human message to being with
#If there is history, that is added as well 
def begin_chat(message: str, history: list[dict]) -> str:
    messages = []
    llm_calls = 0

    for msg in history:
        if msg['role'] == 'user':
            messages.append(HumanMessage(content=msg['content']))
        elif msg['role'] == 'assistant':
            messages.append(AIMessage(content=msg['content']))
            llm_calls += 1
    messages.append(HumanMessage(content=message))

    state = {
        "messages": messages,
        "llm_calls": llm_calls
    }

    response = get_agent().invoke(state)
    return response['messages'][len(response['messages']) - 1].content

initial_message = """
Hi, I’m Sirius Black, your Job Search Sidekick.

Job hunting can feel brutal, confusing, and a little soul-crushing at times — so I’ll keep it real, supportive, and useful.

I can help you with:
- Finding job listings in any city you care about
- Matching job titles to the skills employers actually want
- Searching a semantic skill database for the right qualifications
- Giving you a quick market snapshot if you want the short version

You can ask me things like:
- “Give me Data Scientist listings in Toronto”
- “What skills do I need for AI Engineer or Revit Designer?”
- “Show me architecture jobs in Toronto and give me sample listings”

Let’s make this job search less chaotic and a lot more strategic. What would you like to do?
"""

chat = gr.ChatInterface(
    fn=begin_chat,
    chatbot=gr.Chatbot(placeholder= initial_message)
)

if __name__ == "__main__":
    _logs.info('Starting Job Opportunity Chat App...')
    chat.launch()
