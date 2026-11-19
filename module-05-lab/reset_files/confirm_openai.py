"""Confirm that the OpenAI embedding path works with your key. It makes two small API calls (well under one US cent).

Run:  python confirm_openai.py        with OPENAI_API_KEY set in the terminal"""
import math, os, sys
if not os.environ.get("OPENAI_API_KEY"):
    sys.exit("OPENAI_API_KEY is not set in this terminal.\n  Windows PowerShell:  $env:OPENAI_API_KEY = \"sk-...\"\n  macOS or Linux:      export OPENAI_API_KEY=\"sk-...\"")
os.environ["EMBED_PROVIDER"] = "openai"
import embedder
from openai import OpenAI

texts = ["A late payment charge is applied when the minimum amount due is not received by the payment due date.",
         "What is the late fee on a credit card?",
         "The locker can be operated during branch hours by the hirers named in the agreement."]
vs = embedder.embed_documents(texts)
cos = lambda a, b: sum(x * y for x, y in zip(a, b)) / math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))
checks = [("model", embedder.MODEL, True),
          ("vectors returned", len(vs), len(vs) == 3),
          ("dimensions", len(vs[0]), len(vs[0]) == 1536),
          ("length of the first vector", round(math.sqrt(sum(x * x for x in vs[0])), 4), abs(math.sqrt(sum(x * x for x in vs[0])) - 1) < 0.01),
          ("cosine, charge text and fee question", round(cos(vs[0], vs[1]), 3), cos(vs[0], vs[1]) > cos(vs[0], vs[2])),
          ("cosine, charge text and locker text", round(cos(vs[0], vs[2]), 3), True),
          ("tokens billed", embedder.tokens_used, embedder.tokens_used > 0)]
short = OpenAI().embeddings.create(model=embedder.MODEL, input=texts[:1], dimensions=512).data[0].embedding
checks.append(("dimensions when dimensions=512 is requested", len(short), len(short) == 512))
for name, value, good in checks:
    print(("  ok    " if good else "  FAIL  ") + f"{name}: {value}")
print(f"\n  Cost of this run at USD {embedder.PRICE_PER_MILLION_TOKENS} per million tokens: USD {embedder.cost_usd():.8f}")
print("\nThe OpenAI path works. Every lab script will now use it in this terminal." if all(c[2] for c in checks) else "\nSomething differs from what the lab expects. Send this output to the facilitator.")
