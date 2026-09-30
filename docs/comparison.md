# Comparison / Positioning

This page compares **SV-Copilot** with other popular AI coding agents and tools. The goal is to clarify where SV-Copilot excels, where it differs, and why you might choose it over alternatives.

## Overview

| Feature / Dimension | SV-Copilot | Cursor | Cline | OpenHands (formerly OpenDevin) |
|---|---|---|---|---|
| **Primary Interface** | CLI + VSCode extension | Standalone IDE (VS Code fork) | VSCode extension | Web UI + CLI |
| **Agent Architecture** | Slice-based, plan-then-execute | Chat + inline edits | Autonomous file editing | Sandboxed agent loop |
| **Execution Model** | Local (your machine) | Local (your machine) | Local (your machine) | Remote sandbox (Docker) |
| **Multi-file Edits** | Yes (via slices) | Yes (via composer) | Yes (sequential) | Yes (agentic) |
| **Terminal Integration** | Full (built-in) | Limited (built-in terminal) | Full (via VSCode terminal) | Full (sandboxed) |
| **Git Awareness** | Deep (auto-commit, branch per slice) | Basic (manual) | Basic (manual) | None |
| **Cost** | Free (open source) | Free tier + Pro ($20/mo) | Free (open source) | Free (open source) |
| **Privacy** | Fully local (no telemetry) | Local + optional cloud | Fully local | Local + optional cloud |
| **Extensibility** | Plugin system (planned) | Extension API (limited) | Extension API | Plugin system |
| **Maturity** | Early (active development) | Mature (production) | Mature (production) | Mature (production) |

## Detailed Comparison

### vs Cursor

**Cursor** is a standalone IDE (fork of VS Code) with deep AI integration. It provides inline completions, chat, and composer for multi-file edits.

**SV-Copilot advantages:**
- **Slice-based workflow**: SV-Copilot's slice system enforces a plan-then-execute discipline, reducing hallucination and unintended changes.
- **Git-native**: Every slice creates a branch and auto-commits, making it easy to review, revert, or cherry-pick changes.
- **Fully open source**: No paid tiers, no data leaving your machine.
- **Terminal-first**: SV-Copilot treats terminal commands as first-class actions, not afterthoughts.

**Cursor advantages:**
- **Polished UX**: Inline completions, tab-to-accept, and a mature editor experience.
- **Multi-model support**: Switch between GPT-4, Claude, and others easily.
- **Larger ecosystem**: More users, more extensions, more tutorials.

**Verdict**: Choose Cursor for a polished, IDE-integrated experience. Choose SV-Copilot for a disciplined, git-aware, privacy-first workflow.

### vs Cline

**Cline** is a VSCode extension that provides autonomous file editing via a chat interface. It can create and edit files, run terminal commands, and use MCP tools.

**SV-Copilot advantages:**
- **Slice-based planning**: Cline edits files directly; SV-Copilot plans first, then executes in controlled slices.
- **Better git integration**: SV-Copilot automatically branches and commits per slice.
- **Structured output**: SV-Copilot produces clear, reviewable diffs per slice.

**Cline advantages:**
- **MCP support**: Cline can use any MCP-compatible tool (web search, databases, etc.).
- **More autonomous**: Cline can handle complex multi-step tasks with less user guidance.
- **Larger community**: More active development and plugins.

**Verdict**: Choose Cline for autonomous, tool-rich workflows. Choose SV-Copilot for structured, reviewable, git-disciplined development.

### vs OpenHands

**OpenHands** (formerly OpenDevin) is an AI agent that operates in a sandboxed Docker environment. It can browse the web, run code, and interact with files.

**SV-Copilot advantages:**
- **Local execution**: No Docker, no sandbox, no overhead. Runs directly on your machine.
- **VSCode integration**: Works within your existing editor and terminal.
- **Git-native**: OpenHands has no git awareness; SV-Copilot is built around git.

**OpenHands advantages:**
- **Sandboxed safety**: Experiments and errors are contained in Docker.
- **Web browsing**: OpenHands can browse documentation, search the web, and fetch APIs.
- **Multi-agent**: OpenHands can coordinate multiple agents for complex tasks.

**Verdict**: Choose OpenHands for sandboxed experimentation and web-aware tasks. Choose SV-Copilot for local, git-disciplined development.

## When to Use SV-Copilot

- You want a **disciplined, plan-then-execute** workflow.
- You care deeply about **git hygiene** (branch per feature, auto-commit).
- You want **full privacy** — no data leaves your machine.
- You prefer **CLI-first** or **terminal-integrated** development.
- You are building **open source** and want a free, extensible tool.

## When to Use Alternatives

- **Cursor**: You want a polished IDE with inline completions and a mature UX.
- **Cline**: You need MCP tool integration or highly autonomous agents.
- **OpenHands**: You want sandboxed safety or web-browsing capabilities.

## Future Positioning

SV-Copilot is evolving toward:
- **Plugin system** for custom tools and integrations
- **Multi-model support** (Claude, GPT-4, local models)
- **Collaborative slices** (team workflows)
- **CI/CD integration** (run slices in pipelines)

Stay tuned — the slice-based approach is fundamentally different and, we believe, better for serious software engineering.