# Rover Product Roadmap

This document outlines the planned milestones, upcoming features, and architectural directions for Rover.

---

## 📈 Release Milestones

### 🚀 v1.1.0 - Multi-Language Parsing & Sandboxing
*Goal: Expand language support and secure code validation.*

- [ ] **Tree-sitter AST Parsing**: Integrate Tree-sitter for multi-language syntax tree analysis (JavaScript, TypeScript, Go, and Rust).
- [ ] **Dockerized Test Sandboxing**: Run generated test suites inside isolated, ephemeral Docker containers (or gVisor sandboxes) rather than local subprocesses.
- [ ] **Parallel File Analysis**: Support scanning multiple files concurrently during repository audits.

### 🧠 v1.2.0 - Collaborative Multi-Agent Loops
*Goal: Improve patch accuracy through specialized agent roles.*

- [ ] **Orchestrator Pattern**: Split bug-fixing into three collaborative agents:
  - *The Critic*: Identifies issues and generates test cases.
  - *The Architect*: Proposes code changes.
  - *The Validator*: Evaluates patches and iterates on test failures.
- [ ] **Interactive Human-in-the-Loop Mode**: Allow developers to review, edit, or reject proposed patches in the Streamlit dashboard before they are pushed to GitHub.

### 🏆 v2.0.0 - Semantic Context & Native Integrations
*Goal: Enterprise-ready codebase search and developer workflows.*

- [ ] **Deep Semantic Code Search**: Embed repository symbols into a vector database (e.g. Qdrant/Chroma) to handle natural language codebase queries and semantic matching.
- [ ] **PR Review Bot (Comment-to-Fix)**: Trigger Rover fixes directly by commenting on PRs (e.g., `@rover-bot fix this`).
- [ ] **IDE Extensions**: Lightweight VS Code and JetBrains plugins to trigger local scans and review agent suggestions in-editor.
