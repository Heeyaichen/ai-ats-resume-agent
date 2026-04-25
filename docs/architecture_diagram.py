"""
Generate the README architecture diagram for AI-ATS-Resume Scoring Agent.

Prerequisites:
  pip install -r docs/architecture_requirements.txt
  brew install graphviz   # macOS, if dot is not already installed

Run from the repository root:
  python docs/architecture_diagram.py

Output:
  docs/ats_agent_architecture.png
"""

from diagrams import Cluster, Diagram, Edge
from diagrams.azure.aimachinelearning import (
    AzureOpenai,
    CognitiveSearch,
    CognitiveServices,
    FormRecognizers,
    Language,
    TranslatorText,
)
from diagrams.azure.analytics import LogAnalyticsWorkspaces
from diagrams.azure.compute import ACR, ContainerApps, FunctionApps
from diagrams.azure.database import CacheForRedis, CosmosDb
from diagrams.azure.devops import ApplicationInsights
from diagrams.azure.identity import AzureActiveDirectory
from diagrams.azure.integration import ServiceBus
from diagrams.azure.storage import BlobStorage
from diagrams.azure.web import StaticApps
from diagrams.onprem.ci import GithubActions
from diagrams.onprem.iac import Terraform
from diagrams.onprem.vcs import Github
from diagrams.programming.framework import React


GRAPH_ATTR = {
    "bgcolor": "white",
    "compound": "true",
    "fontsize": "22",
    "fontname": "Helvetica",
    "labelloc": "t",
    "nodesep": "0.55",
    "pad": "0.35",
    "ranksep": "0.85",
    "splines": "ortho",
}

NODE_ATTR = {
    "fontname": "Helvetica",
    "fontsize": "12",
    "margin": "0.10",
}

EDGE_ATTR = {
    "fontname": "Helvetica",
    "fontsize": "10",
    "color": "#374151",
    "arrowsize": "0.75",
}


def main() -> None:
    with Diagram(
        "",
        filename="docs/ats_agent_architecture",
        show=False,
        outformat="png",
        direction="TB",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        edge_attr=EDGE_ATTR,
    ):
        with Cluster("Client & Identity"):
            recruiter = React("Recruiter Browser\nReact SPA")
            entra = AzureActiveDirectory("Microsoft Entra ID\nMSAL + API scope")

        with Cluster("Frontend"):
            swa = StaticApps("Static Web Apps\nproduction frontend")

        with Cluster("Runtime Orchestration"):
            api = ContainerApps("FastAPI Container App\n/api/upload, /api/score, SSE")
            queue = ServiceBus("Service Bus Queue\nats-agent-jobs")
            worker = ContainerApps("Worker Container App\nguarded agent loop")
            function = FunctionApps("Blob Trigger Function\nbackup enqueue")

        with Cluster("Storage, State & Streaming"):
            blob = BlobStorage("Blob Storage\nresumes-raw")
            cosmos = CosmosDb("Cosmos DB\njobs, scores,\ntraces, review flags")
            redis = CacheForRedis("Azure Cache for Redis\nSSE pub/sub + cache")
            search = CognitiveSearch("Azure AI Search\ncandidate vectors")

        with Cluster("Azure AI Tooling"):
            docintel = FormRecognizers("Document Intelligence\nPDF/DOCX extraction")
            translator = TranslatorText("Translator\ndetect + translate")
            language = Language("AI Language\nPII detection")
            safety = CognitiveServices("Content Safety\nmoderation")
            openai = AzureOpenai("Azure OpenAI\ngpt-4o + embeddings")

        with Cluster("Observability"):
            appinsights = ApplicationInsights("Application Insights\ntraces + metrics")
            logs = LogAnalyticsWorkspaces("Log Analytics\ncentral logs")

        with Cluster("CI/CD & Infrastructure as Code"):
            github = Github("GitHub Repo\nmain branch")
            actions = GithubActions("GitHub Actions\nCI/CD workflows")
            terraform = Terraform("Terraform\nAzure IaC")
            acr = ACR("Container Registry\nAPI + worker images")

        # Primary user flow.
        recruiter >> Edge(label="sign in", color="#2563eb") >> entra
        recruiter >> Edge(label="HTTPS", color="#2563eb") >> swa
        swa >> Edge(label="token validation", style="dashed", color="#6b7280") >> entra
        swa >> Edge(label="POST /api/upload\nGET /api/score/{job_id}", color="#2563eb") >> api
        api >> Edge(label="SSE progress", color="#2563eb") >> swa

        # Upload and queue orchestration.
        api >> Edge(label="store resume", color="#059669") >> blob
        api >> Edge(label="create job", color="#059669") >> cosmos
        api >> Edge(label="direct enqueue", color="#059669") >> queue
        blob >> Edge(label="backup blob trigger", style="dashed", color="#6b7280") >> function
        function >> Edge(label="backup enqueue", style="dashed", color="#6b7280") >> queue
        queue >> Edge(label="consume job", color="#059669") >> worker

        # Agent tool calls and result persistence.
        worker >> Edge(label="download resume") >> blob
        worker >> Edge(label="persist score + trace") >> cosmos
        worker >> Edge(label="publish events") >> redis
        redis >> Edge(label="SSE replay") >> api
        worker >> Edge(label="extract text") >> docintel
        worker >> Edge(label="language path") >> translator
        worker >> Edge(label="PII") >> language
        worker >> Edge(label="safety") >> safety
        worker >> Edge(label="score, summary,\nembeddings") >> openai
        worker >> Edge(label="vector lookup") >> search

        # Telemetry.
        [api, worker, function] >> Edge(label="telemetry", style="dotted") >> appinsights
        appinsights >> Edge(label="workspace logs", style="dotted") >> logs

        # Delivery and infrastructure management.
        # Kept local to the CI/CD cluster to avoid long crossing edges in the
        # README diagram. Runtime dependencies are shown in the main flow above.
        github >> actions
        actions >> Edge(label="plan/apply", color="#6b7280") >> terraform
        actions >> Edge(label="build/push", color="#6b7280") >> acr


if __name__ == "__main__":
    main()
