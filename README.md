# Plan 

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![Docker Required](https://img.shields.io/badge/docker-required-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

A lightweight, parallel CI/CD runner.

**Plan** is platform agnostic CI runner. It's a dependency-free, local CI engine that parses YAML pipelines, resolves job dependencies into a Directed Acyclic Graph (DAG), and executes jobs concurrently inside isolated Docker containers.

---

## Table of Contents

- [Why Plan?](#why-plan)
- [Core Features](#-core-features)
- [Prerequisites](#️-prerequisites)
- [Installation](#-installation)
- [Usage](#-usage)
- [Pipeline Configuration](#-pipeline-configuration-mini-ciyml)
- [How It Works](#-how-it-works)
- [Uninstallation](#️-uninstallation)
- [Contributing](#-contributing)
- [License](#-license)

---

## Why Plan?

Most CI tools are black boxes running on someone else's infrastructure. Plan is the opposite: a transparent, single-purpose engine you can read end-to-end in an afternoon, run entirely on your own machine, and point at any repo — local or remote — to see exactly how DAG resolution, scheduling, and container isolation work in practice.

## Core Features

| Feature | Description |
|---|---|
| **Topological Sorting (DAGs)** | Parses job `needs` to build a dependency graph. Uses Kahn's Algorithm to compute exact execution order and detect circular dependencies. |
| **Dynamic Concurrency** | Releases jobs to the thread pool the moment their upstream dependencies succeed, avoiding worker starvation. |
| **Docker Isolation** | Mounts your codebase into ephemeral Docker containers (`ubuntu`, `node`, `python`, etc.) for safe, reproducible execution. |
| **Transitive Skip Logic** | If a job fails, downstream dependents cascade to `SKIPPED` while independent parallel jobs continue unaffected. |
| **Git & Webhook Integration** | Clones target repositories on the fly and optionally POSTs a JSON status report to a webhook on completion. |
| **Built-in Auto-Updater** | Silently checks for newer releases and notifies you in the terminal. |

---

## Prerequisites

Before installing, make sure you have:

1. **Python 3.8+**
2. **Docker Desktop / Docker Engine** (must be running)
3. **Git**

---

## Installation

### Linux / macOS / WSL

```bash
curl -fsSL https://raw.githubusercontent.com/mosakrm0/plan-tool/main/install.sh | bash
```

### Windows (PowerShell)

Open PowerShell as a standard user and run:

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/mosakrm0/plan-tool/main/install.ps1" -UseBasicParsing | Invoke-Expression
```

> **Windows users:** if you see a "command not found" error after installation, fix your PATH automatically:
> ```powershell
> python -m runner --fix-path
> ```
> Close and reopen your terminal afterward.

### Verify the install

```bash
plan --help
```

---

## Usage

Once installed, the global `plan` command is available from anywhere in your terminal.

**Run a local directory** (great for testing pipelines as you write them):

```bash
plan --local ./my-project
```

**Run a remote Git repository:**

```bash
plan --repo https://github.com/username/project.git
```
## CLI Arguments

| Argument | Description |
|---|---|
| `--local <path>` | Path to a local directory to run the pipeline in. |
| `--repo <url>` | URL of a Git repository to clone and run in a temporary folder. |
| `--pipeline <file>` | Custom YAML filename (defaults to common CI filenames or `.github/workflows`). |
| `--webhook <url>` | URL to POST the final `report.json` to upon completion. |
| `--fix-path` | *(Windows only)* Adds the Python Scripts folder to your PATH. |
| `-v`, `--var` KEY=VALUE | Set a pipeline variable (repeatable). CLI variables override values declared in the pipeline file. |
| `-s`, `--secret` KEY=VALUE | Inject a secret into job environments (repeatable). Secret values are not printed by Plan. |

---

## Variables and secrets

Plan supports injecting variables and secrets from the CLI so pipelines can be parameterized at runtime.

- Use `-v KEY=VALUE` or `--var KEY=VALUE` to set a pipeline variable (repeatable).
- Use `-s KEY=VALUE` or `--secret KEY=VALUE` to inject a secret into job environments (repeatable).

Behavior and precedence:
- Pipeline file variables are used first.
- Job-level variables in the pipeline override pipeline-level values.
- CLI-provided variables (`-v`) override file values.
- Secrets (`-s`) are injected last and override other values with the same name.

Example:

```bash
plan --repo https://gitlab.com/user/repo.git -v image=myorg/app -v tag=0.2 -s DOCKER_PASS=abc123
```

---

## Pipeline Configuration (`.ci.yml`)

Create a `.ci.yml` or `.ci.yaml` file in the root of your project:

```yaml
# Global Docker image for all jobs
image: node:18-alpine

jobs:
  lint:
    steps:
      - name: Run linter
        run: npm run lint

  test:
    steps:
      - name: Unit Tests
        run: npm test

  build:
    # Waits for 'lint' and 'test' to finish successfully
    needs:
      - lint
      - test
    steps:
      - name: Compile Application
        run: npm run build
```

**Result:** `lint` and `test` run in parallel; `build` starts only once both succeed. If either fails, `build` is marked `SKIPPED` automatically.

---

## How It Works

1. **Parse** — the YAML pipeline is loaded and validated.
2. **Graph** — jobs and their `needs` are compiled into a DAG.
3. **Sort** — Kahn's Algorithm produces a valid execution order and flags any cycles.
4. **Schedule** — a thread pool dispatches each job the instant its dependencies succeed.
5. **Execute** — each job runs inside an isolated, ephemeral Docker container with your codebase mounted.
6. **Report** — results are collected into `report.json` and optionally POSTed to a webhook.

---

## 🗑️ Uninstallation

**Remove the cloned source directory:**

*Linux / macOS:*
```bash
rm -rf ~/.plan
```

*Windows (PowerShell):*
```powershell
Remove-Item -Recurse -Force $env:USERPROFILE\.plan
```

---
