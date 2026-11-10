# 33 — Documentation onboarding implementation

Date: 2026-11-10. Public release documented: **0.3.0**.
Review baseline: **894a8d5**. Public-documentation implementation commit:
**d7b6ed15fc6dd0ec502aeb7d69db5da325b8e753**. This implements the
[documentation audit](32-documentation-onboarding-audit.md); its findings describe
the earlier public snapshot, not the rewritten pages.

Status: guides rewritten; local acceptance, hosted build/deployment and
independent public receiving observed. Unassisted reader validation and the
Anaconda overview follow-up remain separate work.

## Result and decisions

The entry experience now follows the reader's task: recognize remote Jupyter
access, install locally, check SSH, then open an existing server or start a new
named one. Each route shows how to recognize success and what to do next.
Resume/menu examples precede ID/storage details; optional profiles, multiple
hosts and JSON show the depth available after that first connection.

Retain **Sphinx, MyST and the PyData theme**. The changes use existing theme
colors/navigation, a small responsive stylesheet, standard containers and a
shared metadata template. No runtime or build dependency was added. The client
code, command set, supported platform, package version and published Conda
archive are unchanged. This documentation deployment is not a package release.

The README is now 162 lines, with Installation at line 16, compared with 542
lines and Installation at line 356 in the audited snapshot. Detailed scenarios,
architecture and historical acceptance remain in devguide; the public reference
retains exact ownership, endpoint, scripting, state and authentication contracts.

## Audit disposition

| Finding | Change and evidence |
| --- | --- |
| F01: rendered requirements | Replace the leading Markdown comparator with prose or inline code; rendered quickstart/compatibility have no unintended blockquote and the Conda range remains intact. |
| F02: README entry | Put purpose, installation and first open at the front; link canonical task guides and deeper developer material. |
| F03: first action and fit | Give the homepage one primary first-notebook action, two readiness branches, Linux/SSH fit and a quieter capabilities link. |
| F04: ordinary success path | Open searches directly; normal start opens the browser. Move detached launch/automation detail out of the first successful route. |
| F05: remote setup | Locate the actual environment, check isolated imports/kernels and verify tmux using a noninteractive SSH command. Supply an explicit permitted system-install/admin branch before managed start. |
| F06: recognizable success | Add numbered-choice output, prompt roles, a real fixture notebook image/output and a generated management-menu transcript. |
| F07: names and management | Lead with named start/resume/stop, menu choices, managed counts and confirmed stop-and-archive. Retain UUID recovery and script guards. |
| F08: visual explanation | Add responsive route cards, a selectable-text local/SSH/remote diagram and a small JupyterLab illustration with a text equivalent. Check light/dark and mobile renderings. |
| F09: wayfinding and vocabulary | Turn Getting started into a decision guide, add next-step links and password/terminal/discovery help. Preserve page URLs and principal renamed heading anchors. |
| F10: current guidance | Lead compatibility/recovery/update pages with 0.3.0 behavior and evidence; label earlier observations as history. |
| F11: discovery and previews | Add distinct summaries to 26 guides, preview titles/URLs/image, and GitHub About description/site/topics. Anaconda overview editing remains pending; package publication is already confirmed separately. |
| F12: depth | Show benefits for living-kernel return, projects, scientific environments, explicit multi-host inventory, optional profiles and automation. |
| F13: friendliness | Label execution locations, substitutions, expected outcomes and safe next checks. Explain each password when needed and keep lifecycle consequences explicit. |

Managed and existing servers remain distinct throughout. Unmanaged discovery is
partial and open-only; management counters concern retained managed records.
The menu does not launch servers or aggregate all hosts. Names/UUIDs are
identifiers, not login tokens. Reconnection does not restore a dead kernel.

## Reproducible demonstrations

Run `python -m experiments.docs_assets` with the existing experiments dependencies,
OpenSSH server/client, tmux and Chrome. The
[contributor instructions](../docs/contributing.md#keep-the-first-use-experience-useful)
explain the prerequisites and output files.

The experiment uses the existing private loopback SSH lab with ProxyJump and two
synthetic managed sessions. It captures the actual manage CLI with terminal-like
streams, normalizes only the SSH alias/UUIDs, opens an authenticated forward and
executes the Quickstart cell in a real kernel. The observed output is:

```text
hello from the remote kernel
45
```

It saves the synthetic notebook and captures JupyterLab with a fresh Chrome
profile/default sandbox. It also renders a static sharing card without external
assets. Outputs are `first-notebook.png` (1120×520), `share-card.png` (1200×630)
and `session-menu.txt`. Both images together are below 100 KiB. They contain no
credentials, real infrastructure identifiers or scientific data. Owned browser,
tunnels, fixture kernels and servers are cleaned on exit. No real SSH host or
research session is used.

## Local acceptance observed

- Strict Sphinx build with warnings as errors succeeded using the declared
  documentation toolchain in a temporary mamba environment: Python 3.14.10,
  Sphinx 9.2.0, MyST 5.1.0, PyData theme 0.24.0, copybutton 0.5.2.
- `experiments.docs_check`: **28 HTML pages, 1572 local link/resource/fragment
  occurrences**, all generated CLI commands/options, **70 standalone CLI
  examples, two TOML configurations and six JSON examples**. This parses
  examples without executing shell/SSH actions.
- Existing checker tests: **11 passed**. Existing session UX and open integration
  modules: **24 passed** in disposable loopback fixtures, separate from syntax
  checks and from historical release qualification.
- `ruff check .`, `ruff format --check .` and `git diff --check` passed.
  Private-identifier checks covered changed guides, assets' transcript, styles,
  templates and the experiment. The two images were inspected visually.
- All 26 authored pages have distinct nonempty descriptions, matching Open Graph
  descriptions, preview titles, expected canonical/preview URLs and image text
  alternatives. The public sharing image is a local static asset.
- Chrome 157.0.8103.38 inspected desktop 1440×1000 and mobile 390×844. Homepage,
  quickstart, management and troubleshooting were captured; all 26 authored pages
  were checked at narrow width without horizontal page overflow. Long code and
  reference tables can still scroll within their containers.
- The primary action is within the first viewport: around y=373–423 desktop and
  y=577–651 mobile. The Linux/SSH fit statement also fits, ending around y=465 and
  y=758 respectively. These are snapshot observations, not universal layout bounds.
- Keyboard navigation reached the primary action with a visible focus outline;
  the mobile navigation opened; light/dark controls worked. A native browser
  click copied exactly `jupyhop open workstation`, verified through the temporary
  profile's clipboard. The clipboard check required focus and native activation
  in headless Chrome; a JavaScript click alone was not qualifying evidence.
- Search returned useful routes: password led to SSH then Passwords and security;
  ProxyJump led to SSH; tmux led to remote setup then troubleshooting.

Screenshots and DOM observations are retained outside the source tree. No
end-user walkthrough, search-ranking/conversion measurement, full external-link
crawl or accessibility certification is claimed. The documented site-approved
APT example was not executed; the fixtures already provide tmux. Installed
package qualification remains the separate [0.3.0 publication evidence](31-03-conda-publication.md).

## External entry points and publication

GitHub About was updated and independently reread: a concise SSH/session
description, website `https://www.uibcdf.org/jupyhop/`, and topics `jupyter`,
`jupyterlab`, `python`, `ssh`. The connector lacks metadata-edit capability;
`gh repo edit` performed that reversible change.

The [documentation workflow](https://github.com/uibcdf/jupyhop/actions/runs/42854984300)
built/checked this exact commit and deployed Pages successfully. Artifact
[13782571477](https://github.com/uibcdf/jupyhop/actions/runs/42854984300/artifacts/13782571477)
was downloaded through the connector, and its ZIP SHA256 matched GitHub's receipt:
`d66691d8022697eab742023331ac03273d3946aeb94e77bac7b78dd7bc6cdcb9`.
The hosted HTML also passed the offline reference/CLI checks. Independent HTTPS
GETs returned **200 for all 28 HTML pages**. Article text matched that exact
artifact, and descriptions, preview metadata and canonical URLs matched for all
26 authored pages. The two PNGs and menu transcript also matched byte for byte.
Delivery can add provider markup, so whole-HTML byte equality is not claimed.
The public entry is [www.uibcdf.org/jupyhop](https://www.uibcdf.org/jupyhop/).

The [source checks](https://github.com/uibcdf/jupyhop/actions/runs/42854984740)
also completed successfully: all six jobs, covering Linux clients on Python
3.11, 3.12, 3.13 and 3.14 and the two server-compatibility comparisons. Job status
was reread through the connector; local checks are not substituted for hosted
acceptance. The temporary mamba documentation environment was removed after
verification; review artifacts remain outside the repository.

The Anaconda overview still needs a maintainer edit/recheck: public documentation
URL, useful description and reconciliation of its stale `latest_version` field.
No authenticated Anaconda editing session was configured here. Do not rebuild or
replace the already published archive to change overview text. The audit's
package/release distinction and the [publication record](31-03-conda-publication.md)
remain authoritative for the actual 0.3.0 file.

## Remaining validation

Use the audit's unassisted reader protocol: start at repository/package or a deep
link, ask readers to choose a route, connect to a disposable notebook, explain
passwords, return to a living kernel, finish managed work and locate a deeper
capability and a safe failure-recovery step. Record confusion and requests for
help, repair repeated problems, and repeat affected tasks. The rewritten entry
pages are ready for that review; reader engagement cannot be established by
technical checks alone.
