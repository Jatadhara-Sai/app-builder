import os
import re
import json
import traceback
from dotenv import load_dotenv

# Optional LLM import
llm = None
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except Exception:
    ChatGoogleGenerativeAI = None

from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent

from agent.prompts import planner_prompt, architect_prompt, coder_system_prompt
from agent.states import Plan, TaskPlan, CoderState, ImplementationTask
from agent.tools import (
    write_file,
    read_file,
    get_current_directory,
    list_files,
    init_project_root,
)

# --- Env ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if ChatGoogleGenerativeAI and api_key:
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", api_key=api_key)
    except Exception:
        llm = None

PROJECT_DIR = init_project_root()

# --- Tool helpers (support .invoke or plain call) ---
def call_write_file(path: str, content: str):
    if hasattr(write_file, "invoke"):
        return write_file.invoke({"path": path, "content": content})
    return write_file(path, content)

def call_read_file(path: str) -> str:
    if hasattr(read_file, "invoke"):
        return read_file.invoke({"path": path})
    return read_file(path)

def call_list_files(dirpath: str = "."):
    if hasattr(list_files, "invoke"):
        return list_files.invoke({"directory": dirpath})
    return list_files(dirpath)

# --- JSON extraction from LLM ---
def extract_json_from_text(text: str):
    if not text or not isinstance(text, str):
        raise ValueError("Empty LLM response")
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"```json\s*([\s\S]*?)```", text, re.IGNORECASE)
    if not m:
        m = re.search(r"```(?:[\s\S]*?)\n([\s\S]*?)```", text)
    if m:
        candidate = m.group(1).strip()
        return json.loads(candidate)
    m2 = re.search(r"(\{[\s\S]*\})", text)
    if m2:
        return json.loads(m2.group(1))
    raise ValueError("Could not extract valid JSON from LLM response")

def gemini_json_prompt(prompt: str):
    if not llm:
        raise RuntimeError("No LLM available")
    resp = llm.invoke(prompt)
    text = getattr(resp, "content", None) or resp
    text = str(text).strip()
    return extract_json_from_text(text)

# --- Local fallback planner ---
def local_planner(user_prompt: str) -> dict:
    p = user_prompt.strip().lower()
    words = [w for w in re.split(r"\W+", user_prompt) if w]
    name = " ".join(words[:3]).title() or "Custom App"
    features = []
    if "calendar" in p or "event" in p:
        features = [
            "Monthly calendar view",
            "Add events to specific dates (title, time, description)",
            "Edit and delete events",
            "Persist events locally (localStorage)"
        ]
    else:
        features = ["Add items", "Edit items", "Delete items", "Basic UI"]
    return {
        "app_name": name + (" Calendar" if "calendar" in p else ""),
        "description": f"A simple app based on: {user_prompt}",
        "techstack": "html, css, js",
        "features": features,
        "files": []
    }

# --- Agents ---
def planner_agent(state: dict) -> dict:
    user_prompt = state["user_prompt"]
    try:
        if llm:
            j = gemini_json_prompt(planner_prompt(user_prompt))
        else:
            raise RuntimeError("LLM not configured")
    except Exception as e:
        print("[planner_agent] Fallback planner:", e)
        j = local_planner(user_prompt)
    plan = Plan(
        name=j.get("app_name") or "Unnamed App",
        description=j.get("description", ""),
        techstack=j.get("techstack", "html, css, js"),
        features=j.get("features", []),
        files=j.get("files", []),
    )
    return {"plan": plan}

def architect_agent(state: dict) -> dict:
    plan: Plan = state["plan"]
    try:
        if llm:
            resp_json = gemini_json_prompt(architect_prompt(plan=plan.model_dump_json()))
        else:
            raise RuntimeError("LLM not configured")
    except Exception as e:
        print("[architect_agent] Fallback architect:", e)
        steps = [
            ImplementationTask(filepath="index.html", task_description="Create calendar HTML structure"),
            ImplementationTask(filepath="style.css", task_description="Add CSS for calendar"),
            ImplementationTask(filepath="script.js", task_description="Add JS logic for calendar")
        ]
        return {"task_plan": TaskPlan(implementation_steps=steps)}

    if "implementation_steps" not in resp_json:
        resp_json["implementation_steps"] = []
    task_plan = TaskPlan(**resp_json)
    return {"task_plan": task_plan}

# --- coder_agent with LLM + guaranteed fallback ---
def coder_agent(state: dict) -> dict:
    coder_state: CoderState = state.get("coder_state")
    if coder_state is None:
        coder_state = CoderState(task_plan=state["task_plan"], current_step_idx=0)

    steps = coder_state.task_plan.implementation_steps
    if coder_state.current_step_idx >= len(steps):
        return {"coder_state": coder_state, "status": "DONE"}

    current_task = steps[coder_state.current_step_idx]
    print(f"[coder_agent] Working on: {current_task.filepath} - {current_task.task_description}")

    try:
        existing_content = call_read_file(current_task.filepath)
    except Exception:
        existing_content = ""

    # Step 1: Try LLM
    if llm:
        try:
            system_prompt = coder_system_prompt()
            user_prompt = (
                f"Task: {current_task.task_description}\n"
                f"File: {current_task.filepath}\n"
                f"Existing content:\n{existing_content}\n\n"
                "Use write_file(path, content) to save your changes."
            )
            coder_tools = [read_file, write_file, list_files, get_current_directory]
            react_agent = create_react_agent(llm, coder_tools)
            react_agent.invoke({"messages": [("system", system_prompt), ("user", user_prompt)]})
            print("[coder_agent] ✅ LLM-assisted step executed.")
        except Exception as e:
            print("[coder_agent] ⚠️ LLM coder failed:", e)
            traceback.print_exc()

    # Step 2: Always fallback
    try:
        desc = current_task.task_description.lower()
        if "calendar" in desc or "event" in desc:
            if current_task.filepath.endswith("index.html"):
                call_write_file(current_task.filepath, INDEX_HTML_FALLBACK(state.get("plan")))
            elif current_task.filepath.endswith("style.css"):
                call_write_file(current_task.filepath, STYLE_CSS_FALLBACK())
            elif current_task.filepath.endswith("script.js"):
                call_write_file(current_task.filepath, SCRIPT_JS_FALLBACK())
            else:
                call_write_file(current_task.filepath, f"<!-- placeholder {current_task.filepath} -->")
        else:
            if current_task.filepath.endswith("index.html"):
                call_write_file(current_task.filepath, GENERIC_INDEX_HTML(state.get("plan")))
            elif current_task.filepath.endswith("style.css"):
                call_write_file(current_task.filepath, GENERIC_STYLE_CSS())
            elif current_task.filepath.endswith("script.js"):
                call_write_file(current_task.filepath, GENERIC_SCRIPT_JS())
            else:
                call_write_file(current_task.filepath, f"/* placeholder {current_task.filepath} */")
        print(f"[coder_agent] ✅ Fallback wrote {current_task.filepath}")
    except Exception as e:
        print("[coder_agent] ⚠️ Fallback error:", e)

    coder_state.current_step_idx += 1
    return {"coder_state": coder_state}

# --- fallback content ---
def INDEX_HTML_FALLBACK(plan: Plan | None):
    name = plan.name if plan else "Calendar App"
    return f"""<!doctype html>
<html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/><title>{name}</title><link rel="stylesheet" href="style.css"></head>
<body>
<div class="container"><header><h1>{name}</h1><div class="nav"><button id="prevBtn">&lt;</button><div id="monthYear"></div><button id="nextBtn">&gt;</button></div></header>
<main><div id="calendar"></div><aside id="sidebar"><h2 id="selectedDateHeading">Select a date</h2><div id="eventList"></div><button id="addEventBtn" class="primary">Add Event</button></aside></main></div>
<div id="modal" class="modal hidden"><div class="modal-content"><h3 id="modalTitle">Add Event</h3><form id="eventForm"><label>Title<input type="text" id="eventTitle" required></label><label>Time<input type="time" id="eventTime"></label><label>Description<textarea id="eventDesc"></textarea></label><div class="modal-actions"><button type="submit" class="primary">Save</button><button type="button" id="cancelBtn">Cancel</button><button type="button" id="deleteBtn" class="danger hidden">Delete</button></div></form></div></div>
<script src="script.js"></script></body></html>"""

def STYLE_CSS_FALLBACK():
    return "body{font-family:sans-serif;background:#f4f6f8;margin:0;padding:20px}h1{color:#333}"

def SCRIPT_JS_FALLBACK():
    return "console.log('Calendar app loaded - fallback');"

def GENERIC_INDEX_HTML(plan: Plan | None):
    name = plan.name if plan else "My App"
    return f"""<!doctype html><html><head><meta charset="utf-8"/><title>{name}</title><link rel="stylesheet" href="style.css"></head><body><h1>{name}</h1><div id="app"></div><script src="script.js"></script></body></html>"""

def GENERIC_STYLE_CSS():
    return "body{font-family:Arial,Helvetica,sans-serif;padding:20px;background:#f0f0f0}"

def GENERIC_SCRIPT_JS():
    return "console.log('App scaffold loaded');"

# --- Graph setup ---
graph = StateGraph(dict)
graph.add_node("planner", planner_agent)
graph.add_node("architect", architect_agent)
graph.add_node("coder", coder_agent)
graph.add_edge("planner", "architect")
graph.add_edge("architect", "coder")
graph.add_conditional_edges(
    "coder",
    lambda s: "END" if s.get("status") == "DONE" else "coder",
    {"END": END, "coder": "coder"}
)
graph.set_entry_point("planner")
agent = graph.compile()

# --- Print Graph Structure ---
def print_state_graph():
    print("\n=== State Graph Nodes ===")
    for node in graph.nodes:
        print(f" - {node}")

    print("\n=== State Graph Edges ===")
    # Print static edges
    for src, dst in graph.edges:
        print(f" - {src} → {dst}")

    # Print conditional edges explicitly
    if hasattr(graph, "conditional_edges"):
        for src, mapping in graph.conditional_edges.items():
            for label, dst in mapping.items():
                # "END" gets mapped to __end__
                if dst == END:
                    dst = "__end__"
                print(f" - {src} → {dst} (conditional: {label})")

    print("\n=== ASCII Flow ===")
    print("__start__ → planner → architect → coder ↺ (loops until DONE) → END\n")



if __name__ == "__main__":
    print_state_graph()
    out = agent.invoke(
        {"user_prompt": "create a calendar web application to add events using html, css, js"},
        {"recursion_limit": 100}
    )
    print("Result keys:", out.keys())
    print("Plan:", out.get("plan"))
