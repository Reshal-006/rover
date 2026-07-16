# Rover System Architecture & Diagrams

This document contains high-fidelity visual diagrams representing Rover's core components, pipelines, and data flows.

---

## 1. System Architecture

Overview of how external inputs flow through Rover backend, AI layers, and output components.

```mermaid
graph TD
    User["GitHub User"] -->|Labels Issue 'rover'| GH["GitHub Repository"]
    User -->|Enters URL / Extension| DB["Streamlit Dashboard"]
    GH -->|Webhook Payload| API["FastAPI Listener (api/main.py)"]
    API -->|Triggers Thread| AG["Agent Orchestrator (src/agent.py)"]
    DB -->|Triggers Async Scan| SC["Scanner Engine (src/scanner.py)"]
    
    subgraph Core AI System
        AG -->|AST Context Lookup| IDX["Codebase Indexer (src/indexer.py)"]
        AG -->|One-Shot Structured Call| LLM["LLM Client (src/llm.py)"]
        AG -->|Apply Code Patches| TL["Tools Layer (src/tools.py)"]
        SC -->|AST Static Rules| AST["AST Heuristic Scanner"]
        SC -->|Gemini Inspection| LLM
        SC -->|Weighted Score| RK["Ranking Engine (src/ranking.py)"]
    end
    
    SC -->|Saves results| ST["Scan Store (src/storage.py)"]
    DB -->|Loads scans| ST
    
    TL -->|Clones / Commits / PR| GH
```

---

## 2. Scan Pipeline (Proactive Discovery)

Step-by-step pipeline for repository vulnerability scanning and details storage.

```mermaid
flowchart TD
    Start["Scan Triggered"] --> Clone["Clone Target Repository"]
    Clone --> WarmupIndex["Warm Up Codebase AST Index Cache"]
    WarmupIndex --> Traverse["Traverse Supported Extensions (.py, etc.)"]
    Traverse --> AST["AST Heuristics Scan (Security rules/bugs)"]
    AST --> LLM["LLM Inspect Findings (Verify context & suggestions)"]
    LLM --> Rank["Ranking & Deduplication (Weighted score)"]
    Rank --> Save["Save Scan Metadata & Findings JSON"]
    Save --> End["Completed status (Polled by UI)"]
```

---

## 3. Fix Pipeline (Analyze ➔ Gather Context ➔ Solve)

The optimized deterministic reasoning loop of the autonomous fixing agent.

```mermaid
stateDiagram-v2
    [*] --> ReadIssue : Labeled Issue Latch
    ReadIssue --> InitAgent : Load Agent Prompt & Repo Context
    InitAgent --> LocalIndexing : Build/Load Local AST Codebase Index
    LocalIndexing --> ContextGathering : Smart Search & Gather Context Files
    ContextGathering --> OneShotLLM : Structured BugResolution Generation
    OneShotLLM --> ApplyPatch : Apply patch & unit tests to workspace
    ApplyPatch --> RunPytest : Run local pytest validation
    
    state RunPytest {
        [*] --> CheckPass
        CheckPass --> SuccessState : Test Passes
        CheckPass --> RetryReview : Test Fails
        RetryReview --> ReviewLLMCall : 1-Retry LLM Review with test outputs
        ReviewLLMCall --> ApplyCorrectedPatch : Apply corrected code & tests
        ApplyCorrectedPatch --> ReRunPytest : Re-run pytest validation
        ReRunPytest --> SuccessState : Success
        ReRunPytest --> FailureState : Failure (Max retries reached)
    }
    
    SuccessState --> CommitAndPush : Commit changes & execute push loop
    FailureState --> CommitAndPush : Commit changes & execute push loop (fail status logged)
    CommitAndPush --> CreatePR : Open Pull Request on GitHub
    CreatePR --> CommentOnIssue : Post final report comment
    CommentOnIssue --> [*]
```

---

## 4. GitHub App Authentication Flow

Flowchart of access token exchange and caching mechanics.

```mermaid
sequenceDiagram
    participant GH as GitHub REST API
    participant RC as Repo Context (src/github_auth.py)
    participant FS as Local Token Cache
    
    RC->>FS: Check active cache token for Repository
    alt Token Valid
        FS-->>RC: Return Installation Token
    else Token Expired / Missing
        RC->>RC: Load App ID & Private PEM Key
        RC->>RC: Sign JSON Web Token (JWT)
        RC->>GH: POST /app/installations/{id}/access_tokens with JWT
        GH-->>RC: Return installation_token & expires_at
        RC->>FS: Cache token & set expiration
    end
    RC->>GH: Execute Git/PyGithub Operations (with Token)
```

---

## 5. Dashboard Flow

Interaction model of the user interface.

```mermaid
graph LR
    Dashboard["Streamlit UI"] -->|Poll Scan ID| API["FastAPI /scan/{id}"]
    Dashboard -->|Load Scan list| Store["ScanStore (scans/*.json)"]
    Dashboard -->|Load Agent runs| Logs["Logs (logs/*.json)"]
    Dashboard -->|Manual scan URL| API
    Extension["Browser Extension"] -->|redirects| Dashboard
```

---

## 6. Component Diagram

Visual architecture showing folder layout relationships.

```mermaid
graph TB
    subgraph api/
        main.py["main.py (FastAPI)"]
    end
    subgraph dashboard/
        app.py["app.py (Streamlit UI)"]
    end
    subgraph extension/
        manifest["manifest.json"]
        popupHTML["popup.html"]
        popupJS["popup.js"]
    end
    subgraph src/
        agent["agent.py"]
        tools["tools.py"]
        llm["llm.py"]
        auth["github_auth.py"]
        scanner["scanner.py"]
        ranking["ranking.py"]
        storage["storage.py"]
        indexer["indexer.py"]
    end
    
    app.py --> auth
    app.py --> storage
    main.py --> agent
    main.py --> scanner
    agent --> llm
    agent --> indexer
    agent --> tools
    scanner --> ranking
    scanner --> storage
    popupJS -->|Redirects with params| app.py
```
