"""Confirm that the OpenAI paths work with your key. It makes one embedding call and, when OPENAI_CHAT_MODEL is set, one
planning call (well under one US cent together).

Run:  python confirm_openai.py        with OPENAI_API_KEY set, and OPENAI_CHAT_MODEL set to a chat model that supports structured outputs"""
import os, sys
if not os.environ.get("OPENAI_API_KEY"):
    sys.exit("OPENAI_API_KEY is not set in this terminal.\n  Windows PowerShell:  $env:OPENAI_API_KEY = \"sk-...\"\n  macOS or Linux:      export OPENAI_API_KEY=\"sk-...\"")
os.environ["EMBED_PROVIDER"] = "openai"
import embedder
v = embedder.embed_query("What is the supplier termination policy?")
print(("  ok    " if len(v) == 1536 else "  FAIL  ") + f"embedding: {embedder.MODEL} returned {len(v)} numbers, {embedder.tokens_used} tokens billed")
model = os.environ.get("OPENAI_CHAT_MODEL")
if not model:
    sys.exit("\nOPENAI_CHAT_MODEL is not set, so the planner stays on rules. To try the model planner, set it to a model ID from\nOpenAI's models page that supports structured outputs, and run this script again.")
import planner
question = "What was net revenue in Europe last quarter?"
plan = planner.plan_with_openai(question)
step = plan.steps[0] if plan.steps else None
good = step is not None and step.source == "metrics" and step.metric is not None and step.metric.metric == "net_revenue" \
       and step.metric.filters.get("region") == ["Europe"] and step.metric.filters.get("quarter") == ["2026-Q3"]
print(("  ok    " if good else "  FAIL  ") + f"planner: {model} planned {len(plan.steps)} step(s) for '{question}'")
print("        " + plan.model_dump_json(exclude_defaults=True))
print("\nThe OpenAI paths work. With OPENAI_CHAT_MODEL set, the lab scripts plan with the model." if good else
      "\nThe plan differs from what the lab expects (one metrics step: net_revenue, region Europe, quarter 2026-Q3). Send this output to the facilitator.\nThe lab still runs: set PLANNER=rules to use the rules planner.")
