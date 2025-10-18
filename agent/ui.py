# ui.py
import gradio as gr
from agent.graph import agent
from agent.states import Plan, TaskPlan, CoderState


def run_agent(user_prompt: str):
    try:
        # Run the LangGraph agent
        result = agent.invoke({"user_prompt": user_prompt}, {"recursion_limit": 100})

        # Extract states
        plan: Plan = result.get("plan")
        task_plan: TaskPlan = result.get("task_plan")
        coder_state: CoderState = result.get("coder_state")
        status = result.get("status", "IN PROGRESS")

        # If planner failed
        if plan is None:
            return (
                "❌ Planner failed — no plan generated.",
                "",
                "FAILED",
                str(result),
            )

        # Format plan
        plan_text = f"""
## 📋 {plan.name}

**📝 Description:**  
{plan.description}  

**🧰 Tech Stack:**  
{plan.techstack}  

### ✨ Features
""" + "\n".join([f"- {f}" for f in plan.features])

        # Format implementation steps
        steps_text = "### 🛠️ Implementation Steps\n\n"
        if task_plan:
            for i, step in enumerate(task_plan.implementation_steps, 1):
                steps_text += f"{i}. **{step.filepath}** → {step.task_description}\n"

        final_state = str(result)

        return plan_text, steps_text, f"⚡ {status}", final_state

    except Exception as e:
        return "❌ Error occurred", "", "FAILED", str(e)


# ---------------- UI ---------------- #
with gr.Blocks(
    theme=gr.themes.Base(
        primary_hue="cyan",
        secondary_hue="pink",
        neutral_hue="slate",
    ),
    css="""
        body, .gradio-container {
            background-color: #0f172a !important; /* deep slate */
            color: #f1f5f9 !important; /* light text */
        }
        #hero {
            text-align: center;
            padding: 2rem;
            background: linear-gradient(90deg, #06b6d4, #3b82f6, #8b5cf6);
            color: white;
            border-radius: 1rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        }
        #hero h1 {
            font-size: 2.8rem;
            margin: 0.5rem 0;
        }
        #hero p {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        .output-box {
            background: #1e293b; /* dark slate */
            color: #e2e8f0; /* gray text */
            padding: 1rem;
            border-radius: 0.75rem;
            font-family: monospace;
            white-space: pre-wrap;
            border: 1px solid #334155;
        }
    """,
) as demo:
    # Hero Section
    gr.HTML(
        """
        <div id="hero">
            <h1>🚀 AI Project Builder</h1>
            <p>Plan • Architect • Code — Automated with LangGraph + Gemini</p>
        </div>
        """
    )

    with gr.Row():
        user_prompt = gr.Textbox(
            label="💡 Enter Your Project Idea",
            placeholder="e.g., Build a modern weather dashboard in React",
            lines=2,
        )
    run_btn = gr.Button("✨ Generate Project", variant="primary")

    with gr.Tabs():
        with gr.TabItem("📋 Project Plan"):
            plan_output = gr.Markdown(elem_classes="output-box")

        with gr.TabItem("🛠️ Steps"):
            steps_output = gr.Markdown(elem_classes="output-box")

        with gr.TabItem("⚡ Status"):
            status_output = gr.Textbox(label="Agent Status")

        with gr.TabItem("🧾 Final State"):
            final_output = gr.Textbox(label="Full Result", lines=20)

    run_btn.click(
        fn=run_agent,
        inputs=[user_prompt],
        outputs=[plan_output, steps_output, status_output, final_output],
        show_progress="full"
    )


if __name__ == "__main__":
    demo.launch()
