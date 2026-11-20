"""The data the assistant passes between its steps, provided. Every class is a pydantic model, so a plan written by a
language model is checked against these types before anything runs."""
from typing import Literal, Optional
from pydantic import BaseModel, Field
from metrics import MetricRequest

SOURCES = ("metrics", "graph", "documents")
LABELS = ("calculated metric", "retrieved fact", "inferred relationship", "model interpretation")

class GraphRequest(BaseModel):
    template: str = Field(description="Name of a query in graph/queries, for example suppliers_of_plant")
    params: dict[str, str] = Field(default_factory=dict, description="Identifiers to put into the query, for example {'plant': 'PL-AHM'}")

class DocRequest(BaseModel):
    query: str = Field(description="What to look for in the policy documents, in plain words")
    audience: str = Field(default="all_staff", description="The document collection the step needs: all_staff, or procurement_legal for contract summaries")

class Step(BaseModel):
    id: str
    source: Literal["metrics", "graph", "documents"]
    purpose: str = Field(description="Why the step is needed, in a few words")
    metric: Optional[MetricRequest] = None
    graph: Optional[GraphRequest] = None
    doc: Optional[DocRequest] = None

class Reading(BaseModel):
    text: str                           # a reading the planner chose, in one sentence
    steps: list[str] = Field(default_factory=list, description="Ids of the steps the reading belongs to; empty when it concerns the whole question")

class Plan(BaseModel):
    question: str
    sources: list[str] = Field(default_factory=list, description="The sources the question needs, from metrics, graph, documents")
    steps: list[Step] = Field(default_factory=list)
    composition: Optional[str] = Field(default=None, description="'breach_and_spend' for the composed supplier question, else null")
    spend_threshold: Optional[float] = None
    interpretations: list[Reading] = Field(default_factory=list, description="Readings the planner chose, such as which quarter 'last quarter' is")
    cannot_plan: Optional[str] = Field(default=None, description="Why no step could be planned, when that is the case")

class Evidence(BaseModel):
    step_id: str
    source: str
    kind: Literal["metric", "graph_stated", "graph_inferred", "passage"]
    statement: str                      # one sentence a reader can check
    values: dict = Field(default_factory=dict)
    citation: dict = Field(default_factory=dict)   # enough to fetch the evidence again: metric request, SPARQL, or chunk key and quote

class Claim(BaseModel):
    text: str
    label: str                          # one of LABELS
    citations: list[dict] = Field(default_factory=list)
    verified: Optional[bool] = None     # None for a model interpretation, which cites nothing

class Refusal(BaseModel):
    step_id: str
    source: str
    resource: str
    reason: str

class Answer(BaseModel):
    status: Literal["answered", "partial", "refused", "abstained"]
    claims: list[Claim] = Field(default_factory=list)
    refusals: list[Refusal] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)     # parts of the question for which the evidence was not enough
    abstention: Optional[str] = None
    summary: Optional[str] = None       # one or two sentences of prose; always labelled model interpretation
