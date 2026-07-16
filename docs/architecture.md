# Rover System Architecture & Diagrams

This document contains high-fidelity visual diagrams representing Rover's core components and pipelines.

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
        AG -->|Tool Call / Loop| LLM["Gemini Client (src/llm.py)"]
        AG -->|Read/Edit Files| TL["Tools Layer (src/tools.py)"]
        SC -->|AST & AST Heuristics| AST["AST Heuristic Scanner"]
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
    Clone --> Traverse["Traverse Supported Extensions (.py)"]
    Traverse --> AST["AST Heuristics Scan (Security rules/bugs)"]
    AST --> LLM["LLM Inspect Findings (Verify context & suggestions)"]
    LLM --> Rank["Ranking & Deduplication (Weighted score)"]
    Rank --> Save["Save Scan Metadata & Findings JSON"]
    Save --> End["Completed status (Polled by UI)"]
```

---

## 3. Fix Pipeline (Reactive Fix Loop)

The tool-use execution loop of the autonomous fixing agent.

```mermaid
stateDiagram-v2
    [*] --> ReadIssue : Labeled Issue Latch
    ReadIssue --> InitAgent : Load Agent Prompt & Repo Context
    
    state "Reasoning Loop" as Loop {
        state "Gemini Decides Action" as Action
        state "Execute Tool" as Exec
        
        Action --> Exec : read_file() / search_code()
        Exec --> Action : Return File Content
        Action --> Edit : edit_file()
        Edit --> Test : run_tests()
        Test --> Action : Return Test Output
    }
    
    InitAgent --> Action
    Action --> Verify : Success (Failing test written & passed)
    Action --> Retry : Error / Limit exceeded
    
    Verify --> OpenPR : Create Pull Request
    OpenPR --> Comment : Post explanatory comment
    Comment --> [*]
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
    end
    
    app.py --> auth
    app.py --> storage
    main.py --> agent
    main.py --> scanner
    agent --> llm
    agent --> tools
    scanner --> ranking
    scanner --> storage
    popupJS -->|Redirects with params| app.py
```
