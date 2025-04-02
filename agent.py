import os
import dotenv
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from pydantic import BaseModel, Field
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from typing import Optional


dotenv.load_dotenv()
GROQ_API = os.getenv("GROQ_API")
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "travel-agent"

llm = ChatGroq(
    api_key=GROQ_API,
    temperature=0.2,
    model_name="llama3-70b-8192",
)

conn=sqlite3.connect('memory/travel_agent.db', check_same_thread=False)
memory = SqliteSaver(conn)
# from langgraph.checkpoint.memory import MemorySaver
# memory = MemorySaver()

class State(MessagesState):
    days: Optional[int] = None
    place: Optional[str] = None
    itinerary_plan: Optional[str]


class structData(BaseModel):
    """Extract data from the user input"""
    days: int=Field(description="number of days of the trip")
    place: str=Field(description="Destination of the trip")

data_structured_llm = llm.with_structured_output(structData, method='json_mode')

#nodes
def collect_info(state: State):
    user_input=state["messages"][-1]
    days=state.get("days",None)
    place=state.get("place","")
    if days==0 or place=="missing":
        sys_prompt=f"there is missing data in the user input. you need to extract days and place of a trip from the user input and replace it in the missing value accordingly. existing data are \"days\": {days} and \"place\": {place}. output should be in JSON format"
        message=[SystemMessage(content=sys_prompt),user_input]
    else:
        sys_prompt="Extract the data from the user input which is number of days and the destination place and set number of days in \"days\" key and destination in \"place\" key if any data is missing set that field as \"missing\" for \"place\" and 0 for \"days\" in JSON format"
        message=[SystemMessage(content=sys_prompt),user_input]

    result=data_structured_llm.invoke(message)

    return {"days": result.days,"place": result.place}

def analysis(state:State):
    if state["days"]==0:
        return {"messages":[AIMessage(content="Please provide the number of days for the trip")]}
    elif state["place"]=="missing":
        return {"messages":[AIMessage(content="Please provide the destination place for the trip")]}
    
def human_response(state: State):
    pass

itinerary_formate ="""
Create a well-structured travel itinerary for a {days}-day trip to {destination}. 

Include:
- A brief introduction about the trip.
- A detailed plan for each day, covering **morning, afternoon, and evening activities**.
- Any special recommendations (restaurants, local experiences, must-visit spots).
- A closing note with travel tips.

Write the itinerary in a **natural, engaging, and paragraph format** with using bullet points or structured lists.
"""

def itinerary(state: State):
    days=state["days"]
    place=state["place"]

    sys_prompt=itinerary_formate.format(days=days,destination=place)
    message=[SystemMessage(content=sys_prompt)]

    result=llm.invoke(message)

    return {"itinerary_plan": result, "messages": [AIMessage(content="Response generated successfully")]}

def info_check(state: State):
    if state["days"]==0 or state["place"]=="missing":
        return "analysis"
    else:
        return "itinerary"
    
#building graph
builder = StateGraph(State)

builder.add_node("collect_info", collect_info)
builder.add_node("analysis", analysis)
builder.add_node("human_response", human_response)
builder.add_node("itinerary", itinerary)

builder.add_edge(START, "collect_info")
builder.add_conditional_edges("collect_info", info_check, ["analysis", "itinerary"])
builder.add_edge("analysis", "human_response")
builder.add_edge("human_response", "collect_info")
builder.add_edge("itinerary", END)

# memory = MemorySaver()
graph=builder.compile(interrupt_before=["human_response"], checkpointer=memory)


def run_graph(user_query, thread_id):
    thread = {"configurable": {"thread_id": thread_id}}
    msg=[HumanMessage(content=user_query)]
    for event in graph.stream({"messages":msg,}, thread, stream_mode="values"):
        ms=event.get("messages",[])
        for m in ms:
            print(m.content)
    return state_message(thread)
    
def state_message(thread):
    graph_state = graph.get_state(thread)
    if graph_state[0]['messages'][-1].content == "Response generated successfully":
        return graph_state[0]['itinerary_plan'].content
    return graph_state[0]['messages'][-1].content