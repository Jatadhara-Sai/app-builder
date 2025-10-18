import os
import shutil
from dotenv import load_dotenv
import gradio as gr

from agent.graph import agent, print_state_graph  # use print_state_graph from graph.py

# --- Load environment ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("⚠️ No LLM API key found. Running with local fallback (works offline).")


# --- Create zip of generated_project directory ---
def make_generated_zip(zip_name="generated_project.zip", project_dir="generated_project"):
    if os.path.exists(zip_name):
        os.remove(zip_name)
    if not os.path.isdir(project_dir):
        raise FileNotFoundError(f"Project directory '{project_dir}' not found. No files were generated.")
    base_name = zip_name.replace(".zip", "")
    shutil.make_archive(base_name, 'zip', root_dir=project_dir)
    return os.path.abspath(zip_name)


# --- Run agent pipeline ---
def build_app_and_package(user_prompt: str):
    print("📌 Running LangGraph pipeline for prompt:", user_prompt)
    final_state = agent.invoke({"user_prompt": user_prompt}, {"recursion_limit": 100})

    # Package generated files
    try:
        zip_path = make_generated_zip()
    except FileNotFoundError:
        zip_path = None
        print("⚠️ No generated_project folder found after run.")

    # Prepare textual summary for UI
    plan = final_state.get("plan")
    task_plan = final_state.get("task_plan")
    coder_state = final_state.get("coder_state")
    summary = {
        "plan": plan.model_dump() if plan else None,
        "task_plan": task_plan.model_dump() if task_plan else None,
        "coder_step": getattr(coder_state, "current_step_idx", None),
    }

    return summary, zip_path


# --- Gradio interface ---
def gradio_interface(user_prompt: str):
    summary, zip_path = build_app_and_package(user_prompt)
    plan_text = str(summary)
    file_to_return = zip_path if zip_path and os.path.exists(zip_path) else None
    return plan_text, file_to_return


if __name__ == "__main__":
    # Print state graph at startup
    print_state_graph()

    iface = gr.Interface(
        fn=gradio_interface,
        inputs=gr.Textbox(lines=2, placeholder="Enter your app idea here... e.g. 'Build a calendar with adding events'"),
        outputs=[
            gr.Textbox(label="Generated Plan & Pipeline State"),
            gr.File(label="Download generated project (.zip)")
        ],
        title="App Builder",
        description="Type your app idea and get a structured plan + a downloadable ZIP containing the generated project files."
    )
    iface.launch()
