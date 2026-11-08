# JupyHop Development Guide

> **Status: design, not implementation.** This guide specifies intended behavior and acceptance criteria. Proposed commands are not yet available.

JupyHop is a lightweight, SSH-native tool to launch, discover, manage, and reconnect to remote Jupyter sessions without deploying JupyterHub.

## Documents

1. [Product scope](01-product-scope.md) — audiences, workflows, MVP and non-goals
2. [Architecture](02-architecture.md) — responsibilities, components, state and execution
3. [CLI and configuration](03-cli-and-configuration.md) — proposed interface and settings
4. [Security and reliability](04-security-and-reliability.md) — threat model and failure handling
5. [Testing and quality](05-testing-and-quality.md) — tests, CI and release requirements
6. [Roadmap](06-roadmap.md) — sequential milestones and acceptance criteria
7. [Decisions](07-decisions.md) — agreed constraints and unresolved questions

## Product promise

From an authorized computer, reconnect to your own Jupyter session running on an SSH-accessible remote host, without remembering ports or manually managing tunnels.

## Principles

- Reuse OpenSSH aliases, keys, known hosts, and ProxyJump.
- Keep notebooks, kernels, data, and Python environments on the remote host.
- Require no central, always-on JupyHop service for the initial version.
- Preserve Jupyter authentication and remote OS permissions.
- Keep remote sessions alive across client disconnections.
- Avoid hard-coded lab hostnames, IPs, or sensitive configuration.
- Prefer standard components and a narrow scope over reimplementing JupyterHub.

## Definition of the first useful release

A user can start a managed Jupyter session on a remote host, disconnect, reconnect from another authorized client, list sessions, and explicitly stop one session. Local ports are allocated as needed; remote servers remain loopback-only and authenticated.

JupyHop is developed by UIBCDF and is licensed under the [MIT License](../LICENSE).

This directory is the project's design source of truth. Update specifications and decisions when findings from prototypes change the plan.
