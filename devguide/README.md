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
8. [Scenario catalogue](08-scenarios-and-acceptance.md) — real network, user and failure cases with acceptance gates
9. [Session lifecycle and authentication](09-session-lifecycle-and-auth.md) — independent lifetimes, discovery, reconnection and process-manager choices
10. [Remote runtime and protocol](10-remote-runtime-and-protocol.md) — bootstrap, helper alternatives, schema and version compatibility
11. [Discovery and connectivity](11-discovery-and-connectivity.md) — detection, routing, tunnels, IPv6, URLs and authentication limitations
12. [User experience](12-user-experience.md) — low-configuration workflow, CLI selection, diagnosis and advanced use

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

A user can discover and open an already-running, authorized Jupyter Server over SSH, without manual forwarding; then start a managed Jupyter session, disconnect, reconnect from another authorized client, list sessions, and explicitly stop a managed session. Discovery is best-effort and must never imply cross-user visibility or control. Local ports are allocated as needed; remote servers remain loopback-only and authenticated.

JupyHop is developed by UIBCDF and is licensed under the [MIT License](../LICENSE).

The MVP's nonnegotiable workflows are an existing-server open through ProxyJump (M2) and a managed-server restart-free reconnect from another client (M4). Run M0 feasibility spikes before freezing helper, discovery, token handoff, process-manager, and tunnel designs.

This directory is the project's design source of truth. Update specifications and decisions when findings from prototypes change the plan.

## Milestone evidence

- [M0 validation and ADR](13-m0-validation.md): isolated feasibility experiments,
  selected baseline, and explicit deferred evidence.
- [Acceptance ledger](14-acceptance-ledger.md): every scenario's release gate and
  test target; feasibility is distinct from shipped acceptance.
