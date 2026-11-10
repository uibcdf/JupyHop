# 32 — Documentation audit: clarity, first use and presentation

Date: 2026-11-10. Release reviewed: published 0.3.0.
Snapshot: **599046e4f04a7324f3e7863c063b4a74604278c8**.
Status: audit complete; recommendations below await implementation.

## Verdict

JupyHop has substantial, useful documentation and a clear practical purpose.
The public homepage already explains remote access and shows the core command.
The reference material covers the implemented Linux workflows well. However,
the first-use material asks readers to absorb too much operational detail before
they see a complete, reassuring example of success. The product's simpler 0.3.0
interaction is not consistently reflected in the order of the examples.

**Recommendation:** improve the entry pages, tutorial sequence and visual
demonstration within the existing Sphinx site. Retain the technical reference,
security guarantees and parser-derived CLI. Adding more reference pages or
changing the documentation framework would not address the main findings.

| Question | Assessment |
| --- | --- |
| Is it complete? | Strong coverage of supported operations and limits. First-use completeness is weaker: expected screens/output, a single guided route and a finished fresh-setup recipe need work. |
| Is it clear? | The homepage lead is clear. Clarity becomes uneven when examples mix core actions, interpreter roles, scripting rules and implementation history. |
| Is it attractive? | The theme is tidy, readable and responsive in the inspected views. Product-specific visual explanation and a clear primary action are missing. |
| Can a reader follow it? | An SSH/Jupyter-experienced reader can. A researcher who needs guidance must make several avoidable navigation/setup decisions. |
| Does it communicate simplicity? | Only partly. Names, selectors, automatic browser opening and the management menu already reduce work, but the introductory examples often lead with IDs or additional commands. |
| Is it improvable? | Yes: prioritize the first successful connection, show its result, then offer deeper explanations at the relevant step. |

These are an expert content/interface assessment and observed rendering facts.
They are not measured reader conversion, satisfaction or task-completion rates.

## Scope and method

The repository review established what the released tool actually does before
assessing its presentation. It covered README/package metadata, the actual CLI
parser and dispatch, config/default selection, managed launch, server selection,
inventory/history, diagnostics and relevant regression cases. Architecture and
UX contracts, the previous documentation reviews
[25](25-public-documentation.md), [26](26-documentation-review.md) and
[27](27-documentation-precision.md), and the
[0.3.0 implementation](30-03-implementation.md) and
[publication evidence](31-03-conda-publication.md) provided context.

All **26 public Markdown pages**, their navigation/configuration and the full
README were read. The review followed links for four reader situations:

| Reader situation | Coverage now | Main friction |
| --- | --- | --- |
| SSH works and Jupyter is already running | Install, SSH, discover/open and login are documented | The shortest route is mixed with optional diagnostics and advanced settings. |
| SSH works and a new remote server is needed | Environment preparation and managed start exist | The preparation recipe does not itself establish tmux on the noninteractive SSH PATH; the quickstart then uses a detached launch unnecessarily. |
| Work should continue from another computer | Recovery, independent connections and surviving-kernel conditions are explained | ID-first examples and dense lifetime terminology obscure the ordinary resume action. |
| Several sessions need inspection or completion | Names, selectors, manage, counters and archive history are documented | The simplest management entry point is introduced late and has no illustrated example. |

The live homepage was inspected in Chrome. The exact deployed Pages artifact
from [documentation run 42837304874](https://github.com/uibcdf/jupyhop/actions/runs/42837304874)
was also inspected locally at desktop/mobile sizes, in light/dark modes, with
navigation and search checks. Public HTTPS receiving and offline HTML/example
checks are recorded below. No scientific server/session was used or modified.

## What already works and should be retained

- The homepage immediately states the purpose and shows `jupyhop open workstation`.
  It correctly explains automatic ports and the attached terminal's lifetime.
- Conda installation is available and the guides correctly identify Linux,
  Python 3.11–3.14, OpenSSH and the absence of a mandatory remote JupyHop package.
- Existing servers and servers started by JupyHop are distinguished. Opening an
  existing server does not authorize stopping it.
- Remote preparation, environments/kernels, authentication, recovery, updates,
  scripting/JSON, troubleshooting and security all have substantive coverage.
- Native SSH passwords and Jupyter login remain separate; privacy-safe support
  reports are distinguished from ordinary JSON. The security page has a useful
  [two-step explanation](../docs/security.md#two-authentication-steps).
- CLI help comes from the real parser. The strict build and example checks are
  valuable maintenance safeguards, and the theme's mobile navigation/search work.
- The source/publication evidence is unusually explicit. Keep it accessible to
  reviewers without making it a prerequisite for opening a first notebook.

## Findings and priorities

P1 means address before broader first-user outreach. P2 means the next editorial
or presentation pass. No new release-blocking product defect is established by
this documentation audit. Observed rendering errors are identified explicitly;
reader-effort implications remain assessment rather than user-study results.

### F01 — Version requirements are rendered incorrectly — P1

**Evidence:** [Quickstart](../docs/quickstart.md#start-and-recover-an-owned-server)
line 83 and [Compatibility](../docs/compatibility.md) line 8 begin a Markdown
line with `>=3.11`. MyST interprets the leading `>` as a blockquote marker. The
published HTML contains a separate quote beginning `=3.11`, losing the comparator
and visually turning prerequisite prose into a large grey callout.

**Action:** keep the comparison inside inline code or write “Python 3.11 or
later”; preserve the Conda upper bound where applicable. Check both rendered
pages after building. The current warning-free build and 77-example check pass
despite this error, so source syntax checks alone do not establish readability.

### F02 — The README delays the install-and-use path — P1

**Evidence:** [README](../README.md) has 542 lines. Its
[Installation](../README.md#installation) section starts at line 356, after
the feature catalogue, fifteen scenarios, topology, architecture, limits and
roadmap. There are 28 Markdown links before that section. The early “At a
glance” command helps, but it assumes installation. The opening status paragraph
and links emphasize test counts, historical milestones and publication evidence.

**Action:** lead with the reader's problem, who the tool suits, install/open and
the result. Keep two or three recognizable situations. Link the existing
developer scenario/architecture reports for the full catalogue. Replace
“should”/MVP language for released everyday behavior with present-tense wording.
The tagline “lightweight hub” may suggest a portal to an unfamiliar reader;
explicitly identify the CLI and its local-browser role.

### F03 — The homepage needs a stronger first action and fit check — P1

**Evidence:** the [homepage](../docs/index.md) lead and command are good, but
“Choose your workflow” presents nine destinations at equal visual weight. There
is no prominent install/first-session action next to the command. In the
390×844 capture the first direct Quickstart link begins around y=936, below the
initial viewport. The Linux/platform statement appears in “Current release”,
also below the introductory material. Global navigation remains available.

**Action:** keep the clear lead; add a visible “Install and open your first
notebook” entry and a compact Linux/SSH fit statement. Offer two primary choices:
“Jupyter is already running” and “Start a remote Jupyter server”. Treat resume,
management, support and reference as subsequent destinations. Do not imply that
open creates a missing server or that an unprepared remote computer needs no setup.

### F04 — The quickstart obscures the simplest supported path — P1

**Evidence:** [Quickstart](../docs/quickstart.md) is 143 lines with nine command
blocks. Before its first open example it discusses Include/Match, batch mode,
authentication timeouts and helper/doctor behavior. It runs discover and open
separately although open already discovers. Its first managed example uses
`--no-open`, then requires another command to open the new server. Normal start
already attaches and opens the browser, as verified in
[CLI dispatch](../src/jupyhop/cli.py). This can add another invocation and SSH
authentication. The detailed managed guide already shows the normal start.

**Action:** make one ordinary successful route explicit, then give optional
branches for gateway setup, no server found, another environment and headless
use. Keep the ordinary SSH trust check. For the managed first-use route, show
normal start; explain `--no-open` in automation/detached-launch guidance. End
each route at a usable notebook and a clear next action.

### F05 — Fresh remote preparation leaves a setup decision unresolved — P1

**Evidence:** [Remote setup](../docs/remote-setup.md#create-an-environment-when-needed)
installs tmux in an activated Conda environment and checks `command -v tmux`
there. It correctly warns that this may not expose tmux to noninteractive SSH,
but then sends the reader back to managed start. The
[launcher](../src/jupyhop/_managed_remote.py) finds tmux on its own PATH;
`--server-python` does not activate the environment. The troubleshooting page
explains this condition, so this is an incomplete easy recipe rather than an
undocumented prerequisite or proof the command always fails.

**Action:** end preparation with the actual local check
`ssh workstation 'command -v tmux'`. Give a complete permitted path for making
tmux available, or an explicit administrator/setup branch before continuing.
Label each command block's execution location outside the copyable block. Also
state that mamba is an installation prerequisite or show the Conda equivalent;
the current “Conda or mamba” section gives only mamba commands.

### F06 — First-use guides describe success without showing it — P1

**Evidence:** existing/managed guides explain login and selection in prose, but
show no terminal chooser, management menu or browser result. JSON examples exist
in the reference; those are not first-use demonstrations. The prompt sequence
is described across prose and security/reference pages without an end-to-end
illustration beside the first action.

**Action:** add a short annotated transcript from disposable fixtures and one
small browser/terminal illustration with a text equivalent. Explain at the
relevant step: SSH password belongs to SSH; a new managed-session password is
chosen during start; the browser uses that password or an existing server's
own password/token. A gateway may prompt separately. Managed password
confirmation precedes SSH authentication in the current implementation.
After browser login, show one harmless notebook result and how to disconnect and
return. Keep credentials absent from screenshots and URLs. Keep expected output
in text fences, separate from copyable commands and example-parser input.

### F07 — Friendly names and manage should lead the everyday examples — P1

**Evidence:** [Managed sessions](../docs/managed-sessions.md#observe-and-reopen),
[Recovery](../docs/recovery.md#reconnect-from-the-same-or-another-client) and the
quickstart still often show `SESSION_ID` before friendly alternatives. The manage
section is last in the managed guide, after record/archival details; its heading
starts around y=3725 in the desktop rendering, although the contents sidebar can
jump there. The [implementation](../src/jupyhop/controls.py) already pins names
and numbered choices to exact UUIDs, and preserves strict UUID scripting.

**Action:** introduce `resume workstation`, `open workstation --name analysis`
and `manage workstation` as ordinary human workflows. Keep UUIDs as stable IDs
for diagnostics, explicit recovery and scripts. Show two named sessions, the
managed overview and a confirmed finish action. Explain that overview counters
cover managed records; they are not an exhaustive count of every Jupyter process.
Manage does not launch a new server: start remains a separate command. Preserve
the fact that interactive stop normally confirms archival too, while scripts
remain stop-only unless they explicitly authorize that extra phase.

### F08 — Visual explanation is missing despite a sound theme — P2

**Evidence:** the inspected light/dark pages are legible and mobile layouts do
not overflow horizontally. The 26 public Markdown pages contain no product
screenshot, terminal demo or local/remote diagram. Theme/copy-button icons are
not product illustrations. README has useful text topology diagrams, but the
public introduction relies on prose and a table.

**Action:** use a small laptop → optional SSH gateway → workstation diagram,
labeling JupyHop/browser locally and Jupyter/kernels remotely. Add one restrained
product demonstration and visually prioritize the primary action. Give images
alt text and an adjacent usable text explanation. Keep fast loading, keyboard
access, light/dark modes, search and copy buttons. A theme/framework migration,
large animation or new dependency is not needed before fixing the entry route.

### F09 — Navigation and search need a first-time reader's vocabulary — P2

**Evidence:** the four navigation groups are coherent, but
[Getting started](../docs/getting-started.md) is mostly a list of five pages.
Installation, quickstart and preparation cross-link without one consistently
preferred next step. Search works: ProxyJump leads to SSH and tmux to
troubleshooting. In the sampled password query, the first result is Scripting
and exit codes, before the simple two-authentication explanation. Long tutorial
commands also require horizontal code scrolling on mobile; the page itself fits.

**Action:** make the starting page a guided decision, add a conspicuous next step
to task pages, and expose quick help for “Which password?”, “No server found”
and “Can I close this terminal?”. Introduce terms with plain equivalents:
“started by JupyHop” before managed provenance/UUID terminology. Format long
copyable tutorial commands over valid shell continuation lines. Preserve the
generated full CLI reference for readers who need exact options.

### F10 — Current guidance still carries historical and developer detail — P2

**Evidence:** [Recovery](../docs/recovery.md#credentials-and-client-upgrades)
still discusses only the older installed 0.1.0→0.2.0 upgrade, while
[Updating](../docs/upgrading.md) describes the actual 0.3.0 upgrade gates.
Compatibility's first Conda evidence link points to the historical 0.2.0 report.
The observed-matrix section opens with M5/M6 counts before current-release
evidence. Multiple introductory pages link directly to detailed implementation
or publication reports before explaining their first action.

**Action:** lead public guides with current behavior and concise support facts;
label historical observations and keep detailed provenance in devguide/release
references. Audit remaining 0.2/MVP/“source candidate” wording by context rather
than globally replacing versions. Keep one canonical tutorial per task and link
to it from README/landing pages, reducing repeated workflows that drift apart.

## Proposed entry experience

This is an editorial/design proposal, not implemented UI or a new command set.
Its purpose is to make the next iteration concrete enough to review.

1. **Recognize the need.** Explain opening notebooks on a remote workstation from
   a laptop, with computation/data staying remote and no manual port selection.
   Identify the CLI and current Linux support immediately.
2. **Check the starting point.** Ask whether ordinary SSH works and whether
   Jupyter is already running. Link setup only where those prerequisites are missing.
3. **Install and use.** Give one short recommended client installation, then the
   relevant existing-server or managed-start action.
4. **Recognize success.** Show selection, login, a working notebook and the effect
   of keeping/closing the terminal. Authentication stays enabled.
5. **Return or finish.** Show a named resume/menu and a clearly confirmed stop.
6. **Deepen when needed.** Offer environments, gateways, profiles, troubleshooting,
   supported limits, scripts and developer evidence as distinct next destinations.

Suggested opening copy:

> **Use your remote Jupyter notebooks from your laptop.**
>
> JupyHop finds your running Jupyter server, connects through your existing SSH
> access and opens it in your browser. Your files and computations stay on the
> remote computer. You do not have to choose ports or build tunnels by hand.
>
> Already running Jupyter? Open it. Need a new server? Start one in an existing
> remote environment. Return later to the same session while its kernel is alive.

Primary action: **Install and open your first notebook**. Secondary action:
**Start a remote server**. Display the Linux/SSH requirement beside those actions.

For the existing-server fast path, make the preconditions explicit: a Linux
client with mamba/Conda, trusted working `ssh workstation`, a Linux remote helper
Python 3.11 or later and a discoverable supported authenticated Jupyter server
already running under that remote account. `workstation` is replaced by the
reader's working SSH alias. Then the ordinary local sequence is:

```console
mamba create -n jupyhop -c uibcdf -c conda-forge python=3.14 jupyhop=0.3.0
mamba activate jupyhop
jupyhop open workstation
```

Follow immediately with the expected chooser/login/browser result. Explain
keeping the terminal attached and link the missing-server/environment branch.
Do not present this as a universal fresh-machine installation or a timed promise.

For a prepared remote environment, the normal new-server action is already:

```console
jupyhop start workstation --server-python /absolute/remote/env/bin/python --workdir '~/projects/analysis' --name analysis
```

State where to obtain/substitute the actual Python path and existing project
directory; require compatible Jupyter, a kernel/frontend and tmux on the SSH PATH.
After password prompts this command normally opens the browser. It should not be
followed by another start or an unnecessary mandatory open command.

The local/remote explanation can be a simple diagram with the same text nearby:

```text
Your laptop                               Remote Linux workstation
JupyHop + browser  --- existing SSH --->   Jupyter + kernels + notebooks
                      optional gateway
```

The gateway needs the existing authorized SSH route, not JupyHop/Jupyter.
Ordinary remote operation does not need a remote JupyHop installation. Explain
the optional notebook diagnostic installation separately in its existing guide.

## Recommended implementation sequence and acceptance

1. **First-use corrections:** F01–F04. Correct rendered requirements; shorten the
   README entry; provide a visible homepage action; simplify the first successful
   path while preserving SSH trust and authentication. Check rendered desktop and
   mobile pages, not just source Markdown.
2. **Complete the practical journey:** F05–F07. Finish the fresh setup checks;
   label local/remote steps; show real synthetic output, password roles, named
   return and menu/finish actions. Keep detailed automation separate.
3. **Presentation and maintenance:** F08–F10. Add a small diagram/demo, improve
   navigation/next steps, refresh current-release wording and reduce duplication.
   Retain stable public URLs where possible, with working links when reorganizing.

Acceptance for that subsequent rewrite should include:

- A new reader can explain what JupyHop does, where it is installed, where Jupyter
  runs and which prerequisite path applies before reading architecture/reference.
- The primary first-use action and platform fit are visible in the initial
  desktop/mobile view. The ordinary success route does not require protocol,
  JSON, UUID storage or developer-release knowledge.
- Existing-server and new-server tutorials each have prerequisites, execution
  location, commands, expected result and one clear next step. No invented CLI,
  automatic credential retrieval or unsupported platform is advertised.
- A prepared reader can reach a usable notebook, disconnect safely, return to
  the same surviving session and finish a synthetic managed session by name/menu.
  Stop still warns about terminating every kernel of that server.
- Rendered version requirements are intact. Mobile code scrolling stays contained;
  menus, copy controls, search and light/dark presentation remain usable.
- Existing strict Sphinx/reference/CLI-example checks pass. Fixture validation of
  changed command recipes remains separate from syntax parsing and never uses
  real scientific workloads.

Then run an **unassisted reader walkthrough** with a small initial group of
representative SSH-using researchers. Ask them to identify the use case, choose
the right setup, connect to a prepared disposable server, explain password
prompts and find resume/finish/help. Record wrong turns, external help and time
separately for installation, prerequisite setup and first connection. These are
proposed measurements; this audit does not claim observed reader timings or
guarantee “working in five minutes”.

## Validation and evidence ledger

- Current deployed artifact:
  [13773648216](https://github.com/uibcdf/jupyhop/actions/runs/42837304874/artifacts/13773648216),
  ZIP SHA256 a3a02dc44fe0e638be4ccea53c54591106970346cb2dae6c42c93e3ad3d86dde.
  It belongs to the reviewed commit; its digest was verified before local inspection.
- Independent HTTPS GETs returned 200 for all 28 generated HTML pages. Main
  article text matched the artifact for all 26 authored pages. Delivery adds
  provider markup, so raw whole-file byte equality was not claimed.
- Offline check passed **28 HTML pages, 1482 local reference/resource/fragment
  occurrences**, required guides and generated CLI commands/options. The source
  gate accepted **77 CLI examples, two TOML configurations and six JSON blocks**.
  It parses those examples; it does not execute their remote actions or evaluate
  reader comprehension. Historical runtime/installed tests remain separate evidence.
- Chrome 157.0.8103.38, a private temporary profile and the default browser
  sandbox were used. Desktop: 1440×1000; mobile: 390×844 CSS pixels. Reviewed
  views include the live homepage, artifact homepage in light/dark, quickstart,
  managed start, mobile navigation and mobile CLI reference. No inspected view
  had horizontal page overflow; several long code blocks scroll internally.
- Homepage observations: core command around y=327 on desktop/y=462 on mobile;
  first direct Quickstart link around y=630/y=936 respectively. On the desktop
  quickstart, the first discover/open block begins around y=1380. These are
  snapshot/viewport observations, not universal positions or reading times.
- Search returned results for ProxyJump, password and tmux. Top results were SSH,
  scripting and troubleshooting respectively. The mobile menu opened successfully.
- Rendered HTML confirmed the two unintended blockquotes in F01 despite passing
  the existing build checks. Source/image inspection found no public product
  illustrations; embedded copy/theme icons were excluded from that assessment.
- The two proposed JupyHop commands in this audit were parsed without execution;
  local audit/index link targets and private-identifier checks passed.
- Screenshots, DOM observations, receiving results and review helpers are retained
  outside the source tree. Owned preview servers and Chrome processes were closed.
  No end-user study, full accessibility certification, complete external-link
  crawl, new package qualification or new remote scientific test is claimed here.

This task records the audit and adds its developer-guide index entry. Public
guide content, product behavior, dependencies, packages and site deployment are
unchanged. The recommended next work is the staged documentation rewrite above,
followed by the reader walkthrough.
