# 32 — Documentation audit: discovery, first use and depth

Date: 2026-11-10. Release reviewed: published 0.3.0.
Public-documentation snapshot: **599046e4f04a7324f3e7863c063b4a74604278c8**.
Expanded review after the first audit at **e210b2d61cd4ec7f2352a204d642ba3c5c72781f**;
the public guides have not changed between these reviews.
Status: expert audit complete for the reviewed snapshot. The
[implementation report](33-documentation-onboarding-implementation.md) records
the subsequent rewrite, observed checks and remaining reader/external validation.
The findings below retain the original evidence; they do not describe current
public-page content after that rewrite.

## Verdict

JupyHop has substantial, useful documentation and a clear practical purpose.
The public homepage already explains remote access and shows the core command.
The reference material covers the implemented Linux workflows well. However,
the first-use material asks readers to absorb too much operational detail before
they see a complete, reassuring example of success. The product's simpler 0.3.0
interaction is not consistently reflected in the order of the examples.

The first audit mainly examined what happens **after a reader arrives**. That
was insufficient for the wider goal: help someone find JupyHop, recognize their
own problem, feel confident about trying it, and discover its depth. This
expanded review adds external entry points, a progression of capabilities and
an explicit standard for friendly instructions. Simplifying the first page
must still communicate that JupyHop can launch, recover and manage sessions,
not only open a browser through SSH.

**Recommendation:** improve the entry pages, tutorial sequence and visual
demonstration within the existing Sphinx site. Retain the technical reference,
security guarantees and parser-derived CLI. Adding more reference pages or
changing the documentation framework would not address the main findings.

The audit itself cannot produce engagement. Its recommendations provide a
testable design brief; whether the documentation feels inviting and easy
requires the rewrite and observation of actual readers. Search ranking and
reader conversion are not established by this review.

| Question | Assessment |
| --- | --- |
| Can someone find it? | Repository/package links already exist, but empty GitHub About fields, generic page titles and incomplete package-overview metadata weaken the entry experience. Indexing/ranking has not been measured. |
| Is it complete? | Strong coverage of supported operations and limits. First-use completeness is weaker: expected screens/output, a single guided route and a finished fresh-setup recipe need work. |
| Is it clear? | The homepage lead is clear. Clarity becomes uneven when examples mix core actions, interpreter roles, scripting rules and implementation history. |
| Is it attractive? | The theme is tidy, readable and responsive in the inspected views. Product-specific visual explanation and a clear primary action are missing. |
| Can a reader follow it? | An SSH/Jupyter-experienced reader can. A researcher who needs guidance must make several avoidable navigation/setup decisions. |
| Does it communicate simplicity? | Only partly. Names, selectors, automatic browser opening and the management menu already reduce work, but the introductory examples often lead with IDs or additional commands. |
| Does it feel friendly? | The tone is generally factual, but readers need clearer checkpoints, plain explanations and a safe next action when something differs from the example. |
| Does it communicate power? | The capabilities exist in separate guides. A compact path from one connection to named sessions, multiple hosts and repeatable workflows is missing. |
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
README were read. The review followed links for these reader situations:

| Reader situation | Coverage now | Main friction |
| --- | --- | --- |
| Arriving from a repository, package listing or search/deep link | README and package/source metadata link to documentation; task pages have navigation | GitHub About is empty; inspected page summaries/previews are absent; a deep-page arrival needs a clearer route to the first success. |
| SSH works and Jupyter is already running | Install, SSH, discover/open and login are documented | The shortest route is mixed with optional diagnostics and advanced settings. |
| SSH works and a new remote server is needed | Environment preparation and managed start exist | The preparation recipe does not itself establish tmux on the noninteractive SSH PATH; the quickstart then uses a detached launch unnecessarily. |
| Work should continue from another computer | Recovery, independent connections and surviving-kernel conditions are explained | ID-first examples and dense lifetime terminology obscure the ordinary resume action. |
| Several sessions need inspection or completion | Names, selectors, manage, counters and archive history are documented | The simplest management entry point is introduced late and has no illustrated example. |
| A successful user wants more control | Profiles, explicit multi-host inventory, JSON and support diagnostics exist | There is no visible growth path distinguishing optional power from requirements for everyday use. |

The live homepage was inspected in Chrome. The exact deployed Pages artifact
from [documentation run 42837304874](https://github.com/uibcdf/jupyhop/actions/runs/42837304874)
was also inspected locally at desktop/mobile sizes, in light/dark modes, with
navigation and search checks. Public HTTPS receiving and offline HTML/example
checks are recorded below. The expanded review also inspected public GitHub
repository metadata, four delivered HTML heads and Anaconda package/release
metadata. It did not change these external services. No scientific server/session
was used or modified.

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
Check arrivals directly at installation, recovery and troubleshooting too:
brief context and a visible first-use link should orient someone who never saw
the homepage. Use reader questions such as “Use Jupyter through an SSH gateway”
alongside the exact searchable term ProxyJump.

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

### F11 — External discovery and previews need a coherent entry point — P1

**Evidence:** the public [GitHub repository](https://github.com/uibcdf/jupyhop)
has no About description, website or topics. README, Python project metadata
and the current Conda recipe already contain documentation links; this is not
an absence of all routes to the site. The four inspected live pages return 200
and have correct canonical URLs. They have no meta description or Open Graph
title/description/image. The homepage title is `JupyHop — JupyHop 0.3.0`, which
does not explain its purpose to an unfamiliar reader.

The [Anaconda package overview API](https://api.anaconda.org/package/uibcdf/jupyhop)
has an empty description, a documentation URL pointing at the GitHub quickstart
source and `latest_version: "0.2.0"`, although its versions include 0.3.0. The
[0.3.0 release metadata](https://api.anaconda.org/release/uibcdf/jupyhop/0.3.0)
independently confirms the qualified archive in `main`. This is an observed
overview inconsistency, **not a missing 0.3.0 publication**. Its cause and the
version displayed by the web interface have not been established.

**Action:** make repository, package and documentation entry points consistent.
Suggested About description: “Open, launch and reconnect to remote Jupyter
sessions through SSH, with automatic tunnels and session management.” Set its
website to the public documentation; choose a few accurate topics such as
`jupyter`, `jupyterlab`, `ssh` and `python`. Review/update the Anaconda overview
and documentation destination without rebuilding or replacing the published
archive. These external updates are recommendations, not actions taken here.

Use a descriptive homepage title such as “JupyHop — Remote Jupyter over SSH”,
task-specific page titles and distinct summaries. Give shared links a concise
preview using [Open Graph metadata](https://ogp.me/) and an accessible, lightweight
image if useful. Check the rendered head and actual link preview where supported.
[Google's title guidance](https://developers.google.com/search/docs/appearance/title-link)
and [snippet guidance](https://developers.google.com/search/docs/appearance/snippet)
support descriptive titles and page summaries; search engines may choose other
text. Missing descriptions/previews do not prove poor indexing, and adding them
does not guarantee ranking or traffic. No sitemap, analytics or new Sphinx
dependency is a prerequisite for correcting these concrete omissions.

### F12 — Show a progression of power without enlarging the first task — P1

**Evidence:** [configuration](../docs/configuration.md),
[managed sessions](../docs/managed-sessions.md), [recovery](../docs/recovery.md)
and [scripting](../docs/scripting.md) describe useful implemented capabilities.
They are presented as separate destinations. An introduction reduced to
install/open alone could leave readers thinking the product only saves one
SSH command, while a full option catalogue recreates the current overload.

**Action:** show two or three concrete future benefits near the first example:
return to a running computation, keep projects in named sessions, and inspect
several SSH hosts. Link a short capability progression, proposed below, with
task-specific detail available when needed. Show what the user gains before
the flags that provide it. Keep profiles and automation optional. Do not imply
that manage launches servers, that it combines all hosts, that discovery is
exhaustive, or that a stopped kernel's memory can be restored.

### F13 — Make friendliness an instructional contract — P1

**Evidence:** the technical facts and security explanations are useful, but
F04–F07 leave decisions and recognition of success to the reader. A friendly
adjective or extra welcome paragraph would not resolve those gaps.

**Action:** apply this contract to every first-use route and its failure branch:

- State **where to run the command, what to do, what to expect and what comes
  next**. Label the local/remote computer outside copyable commands.
- Introduce terms when needed: “the remote computer” before helper protocol,
  “the name you chose” before UUID, and explain a terminal chooser with an example.
- Explain a problem neutrally: what succeeded, what is uncertain and the next
  safe check. For partial discovery, say that known locations were checked and
  show how to provide another path; do not conclude that no server exists.
- Reassure precisely at the action: closing a tunnel leaves the remote server
  running; stop terminates its kernels; archive retains an inactive record's
  evidence. Do not promise recovery after server/kernel termination.
- Explain each password's owner when its prompt appears. Never ask readers to
  paste credentials into a report or imply that passwordless SSH is required.
- Keep ordinary instructions short and complete. Put unusual cases and full
  reference behind clear links, preserving access to prerequisites and limits.

These are documentation requirements. They do not change CLI output or remove
existing confirmation/security checks. Test the failure guidance as well as the
successful path: an unexpected prompt should not leave a reader feeling lost.

## Proposed entry experience

This is an editorial/design proposal, not implemented UI or a new command set.
Its purpose is to make the next iteration concrete enough to review.

1. **Find and recognize the need.** Make repository/package links and page
   previews lead to a clear promise. Explain opening notebooks on a remote
   workstation from a laptop, with computation/data staying remote and no manual
   port selection.
   Identify the CLI and current Linux support immediately.
2. **Check the starting point.** Ask whether ordinary SSH works and whether
   Jupyter is already running. Link setup only where those prerequisites are missing.
3. **Install and use.** Give one short recommended client installation, then the
   relevant existing-server or managed-start action.
4. **Recognize success.** Show selection, login, a working notebook and the effect
   of keeping/closing the terminal. Authentication stays enabled.
5. **Return or finish.** Show a named resume/menu and a clearly confirmed stop.
6. **See room to grow.** Show a few concrete capabilities early, then offer
   environments, gateways, profiles, troubleshooting, supported limits, scripts
   and developer evidence as distinct next destinations.

Suggested opening copy:

> **Use your remote Jupyter notebooks from your laptop.**
>
> JupyHop finds your running Jupyter server, connects through your existing SSH
> access and opens it in your browser. Your files and computations stay on the
> remote computer. You do not have to choose ports or build tunnels by hand.
>
> Already running Jupyter? Open it. Need a new server? Start one in an existing
> remote environment. Return later to the same session while its kernel is alive.
> Name your sessions, manage projects and connect to several SSH hosts as your
> work grows.

Primary action: **Install and open your first notebook**. Inside that route,
offer the already-running/new-server branches. A quieter **See what you can do**
link leads to the progression below. Display the Linux/SSH requirement beside
the first action; avoid a row of equally prominent competing destinations.

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
jupyhop start workstation \
    --server-python /absolute/remote/env/bin/python \
    --workdir '~/projects/analysis' \
    --name analysis
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

### Make the depth visible in layers

These are supported 0.3.0 capabilities, not a request for more product scope.
The reader should see the benefits before needing to learn the details.

| Reader's next goal | Demonstration to introduce | Keep explicit |
| --- | --- | --- |
| Open a notebook already running remotely | `jupyhop open workstation`, then show the browser result | It opens a verified server under the SSH account; it does not create one. |
| Start a project and return to its computation | Named start above, then `jupyhop resume workstation --name analysis` | The remote environment/tmux must be ready; memory survives only while the kernel runs. Another authorized client can reconnect. |
| Choose and finish several projects | `jupyhop manage workstation`, illustrated with two named sessions | It manages one host at a time. Only managed sessions can be stopped/archived; existing servers can be opened. Start is separate. |
| Inspect several machines | `jupyhop list workstation-a workstation-b` | These are working SSH aliases; inventory is partial and failures remain explicit. |
| Reuse settings or automate inspection | Link profiles, then show `jupyhop list workstation-a workstation-b --batch --json` | Profiles are optional; `--env` selects a JupyHop profile, not Conda activation. Batch needs noninteractive SSH; ordinary use also supports passwords. |

Add a short “When JupyHop fits” explanation: an individual with authorized SSH
access, remote environments and a local browser. It is not a shared login portal,
scheduler or multi-user JupyterHub replacement. Show the actual Linux support
and bounded discovery rather than making a “works everywhere” claim.

### Give each entry page one job

| Surface | Reader outcome and required content |
| --- | --- |
| GitHub/package overview and README | Recognize the problem and CLI, find installation/docs, see one result and a few concrete capabilities. |
| Homepage and Getting started | Understand fit, choose a route based on readiness and take one obvious next action. |
| Quickstart, existing-server and remote-setup routes | Complete one task with prerequisites, location labels, checkpoints and a missing-prerequisite branch. Keep a canonical recipe per task. |
| Managed sessions and Recovery | Return by name, choose between projects, understand the live kernel condition and finish safely. |
| Configuration, Scripting and reference | Reveal optional depth with working prerequisites; preserve exact flags, JSON contracts and limits. |
| Troubleshooting and support | Recognize an observed message, understand the next safe check and find a shareable diagnostic/report path without exposing credentials. |

## Recommended implementation sequence and acceptance

1. **Entry, relevance and promise:** F01–F04 and the entry aspects of F11–F13.
   Correct rendered requirements; shorten the README; provide a visible first
   action, fit statement and a few credible capabilities. Draft consistent
   external descriptions/titles alongside the pages they introduce. Apply the
   friendly instruction contract from the start; it is not final cosmetic polish.
2. **First success and a path to deeper use:** F05–F08 and F12–F13. Finish setup
   checks, label local/remote steps, show synthetic success output, password
   roles, named return and menu/finish actions. Add the small diagram/demo. Link
   optional profiles, multiple hosts and automation without making them mandatory.
3. **Receiving, navigation and validation:** F09–F11 plus the acceptance below.
   Check deep links, search and current-release wording; reduce duplicate recipes.
   Retain public URLs or provide working redirects when reorganizing. Synchronize
   repository/package entry metadata, inspect built desktop/mobile pages and
   previews, and run the reader walkthrough. Keep the existing Sphinx framework.

Acceptance for that subsequent rewrite should include:

- A new reader can explain what JupyHop does, where it is installed, where Jupyter
  runs and which prerequisite path applies before reading architecture/reference.
- Repository and package entries lead to the public documentation. Inspected
  titles/summaries describe the task and release metadata agrees with publication
  evidence. Preview/canonical URLs are valid; this is not a search-ranking gate.
- The primary first-use action and platform fit are visible in the initial
  desktop/mobile view. The ordinary success route does not require protocol,
  JSON, UUID storage or developer-release knowledge.
- Existing-server and new-server tutorials each have prerequisites, execution
  location, commands, expected result and one clear next step. No invented CLI,
  automatic credential retrieval or unsupported platform is advertised.
- A prepared reader can reach a usable notebook, disconnect safely, return to
  the same surviving session and finish a synthetic managed session by name/menu.
  Stop still warns about terminating every kernel of that server.
- A reader can name at least two relevant deeper capabilities and find their
  instructions, while recognizing that profiles/JSON are optional. They do not
  infer unsupported cross-user access, platforms or kernel resurrection.
- A reader can use one deliberately introduced, harmless failure to locate an
  explanation and a safe next step. They understand which password is requested
  and whether an uncertain operation should be inspected before retrying.
- Rendered version requirements are intact. Mobile code scrolling stays contained;
  menus, copy controls, search and light/dark presentation remain usable.
- Existing strict Sphinx/reference/CLI-example checks pass. Fixture validation of
  changed command recipes remains separate from syntax parsing and never uses
  real scientific workloads.

Then run an **unassisted reader walkthrough** with a small qualitative group of
SSH-using researchers, including readers unfamiliar with tunneling and some
experienced users. Use prepared disposable environments and these tasks:

1. Begin at the repository or package entry, without being handed the Quickstart
   URL. Find the docs and explain the purpose, current fit and next action in
   the reader's own words. Include a separate arrival at a troubleshooting page.
2. Choose the correct already-running/new-server route from a stated situation;
   connect, recognize success and explain the password prompts. Observe where
   prerequisite work is mistaken for an ordinary repeated step.
3. Disconnect and return to a known living kernel, then finish a synthetic
   managed session. Observe whether names, selection and stop consequences make
   sense without coaching.
4. Find a capability useful beyond the first connection, explain its benefit
   accurately and locate its guide. Verify that optional settings have not made
   the simple route appear harder.
5. Introduce one safe known setup problem and ask for the next check and support
   route. Do not collect passwords, tokens or unreviewed private reports.

Record wrong turns, requests for external help, misunderstandings and brief
confidence/clarity feedback. Separate installation, prerequisite setup and first
connection timings; do not turn one prepared setup into a universal time claim.
Set success by the observable criteria above, repair recurrent problems, and
repeat affected tasks. A small qualitative sample is not a conversion-rate or
ranking study. These tests are proposed and **have not been performed**. If
owner-accessible search coverage data becomes available later, examine it
separately; no new tracking, promotion campaign or infrastructure change is
required by this audit.

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
- Expanded-review observations, all on 2026-11-10: the GitHub connector returned
  `description: null`, `homepage: null`, `topics: []`. Fresh public HTTPS requests
  returned 200 for index, quickstart, managed-sessions and troubleshooting; each
  has its expected canonical URL and lacks description/inspected Open Graph tags.
  These describe the delivered HTML head, not search-engine indexing results.
- The Anaconda overview and 0.3.0 release APIs were inspected separately. The
  latter confirms `noarch/jupyhop-0.3.0-py_0.tar.bz2`, labels `staging` and `main`,
  SHA256 015425e8b5a4fdeeb851d6d0a744fde97fb5c369d70c486ac43c8f389a537449.
  The overview inconsistency in F11 does not invalidate those release facts.
- Six distinct proposed JupyHop command examples were parsed without execution;
  63 local file links across the audit/index, private-identifier and code-fence
  checks passed. This prose-only expansion does not rerun the unchanged public
  site's build or runtime tests.
- Screenshots, DOM observations, receiving results and review helpers are retained
  outside the source tree. Owned preview servers and Chrome processes were closed.
  No end-user study, formal search-engine indexing audit, full accessibility
  certification, complete external-link crawl, new package qualification or new
  remote scientific test is claimed here. Keyboard/focus, contrast and image
  alternatives remain checks for the proposed rendered rewrite.

At completion of this audit pass, public guides, product behavior, dependencies,
packages, repository About settings and site deployment were unchanged. The
subsequent [implementation report](33-documentation-onboarding-implementation.md)
records the rewrite and checks separately. This audit supplies the design brief;
reader engagement still requires observation of actual readers.
