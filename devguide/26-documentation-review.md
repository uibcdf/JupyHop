# 26 — Public documentation review

Date: 2026-11-09.
Status: published at https://www.uibcdf.org/jupyhop/. Local content/example,
browser/link, hosted build/deployment and independent HTTPS checks passed.

## Assessment and scope

The initial public site covered all eight implemented commands, ownership,
authentication, routing and supported-platform limits. It needed more practical
detail for a fresh user who has SSH access but does not already know Jupyter's
runtime/environment conventions. Several scripting distinctions were too easy
to misinterpret without reading the implementation.

The review compared the public guides and README with the devguide contracts,
stabilization/publication evidence, actual argparse parser, config validators,
CLI dispatch, output parsers, remote state observations and SSH/launch helpers.
Historical experiment observations remain historical; current roadmap summaries
now identify the published Conda package and live website separately from PyPI.

This increment changes documentation only. The client, bootstrap/protocols,
registry schema, supported OS matrix and published Conda bytes are unchanged.
It adds no functionality, dependency, tag, migration or scientific-host operation.

## Gaps closed

| Finding | Change / implementation basis |
| --- | --- |
| Remote prerequisites were listed without a complete preparation path | New remote guide locates Python/runtime/kernels, describes optional environment creation and gives a private-runtime, authenticated manual launch example; local versus remote steps are explicit |
| Server Python could be mistaken for notebook kernel Python | Added a user kernelspec registration example, overwrite-name warning and reconnect-versus-switch distinction |
| Session IDs, observations and storage were spread across developer reports | New session reference covers managed UUID/unmanaged observation IDs, eight observed states, active/archive paths, host/account scope and the 128-record bound |
| Successful status could be mistaken for readiness | Explicitly document exit-0 observations of stale/failed/unreachable records and the need to inspect servers[].state |
| CLI JSON could be mistaken for an internal wire envelope | New JSON reference distinguishes doctor, discover, fleet, lifecycle, launch and attached-open shapes with synthetic examples and null/error/exit behavior |
| Selection exits were too broadly described | Single-host absent/unverified selection uses 6; hostless fleet selection failures, including no candidates, use 7 |
| Automation lacked a concrete protected-password/partial-result example | Added stdin/new-password bounds, --no-open versus --no-browser, --json confirmation/selection rules and a shell fragment preserving discovery exit 6 under set -e |
| Existing clients had no update procedure | New upgrade guide describes installing the selected numeric Conda release and reconnecting without changing remote runners/state |
| SSH/TOML edge cases required inference | Added fixed-LocalForward migration, browser-client loopback scope, noninteractive tmux PATH diagnosis, quoted dotted TOML host keys, helper replacement and sequential inventory limits |
| Loopback could be confused with per-account access control | Clarify that Jupyter authentication remains necessary for processes/users able to reach either loopback endpoint |

The ordinary quickstart stays short and links to task/reference pages. Navigation
retains its four existing groups and source URLs. Generated CLI help remains the
single source for command/option spelling. The public site now has 25 Markdown
documents and 27 generated HTML pages including search/index.

## Experiments and validation

- Strict Sphinx 9.2.0/MyST 5.1.0/PyData 0.24.0 build on isolated Python 3.14.9
  passes without warnings. `make -C docs check` verifies 1381 local
  links/resources/fragments and all current CLI commands/options.
- Extracted Markdown examples: all 63 fenced JupyHop commands parse using the
  actual argparse factory; both TOML examples pass parse_config; all five JSON
  blocks decode. Synthetic CLI dispatch checks confirm empty discovery exit 6,
  failed fleet exit 3, empty/status-nonready exit 0, missing managed UUID exit 11,
  archive shape and single-host/fleet selection exits 6/7. No SSH runs in these
  dispatch checks.
- The shell example runs under sh -e with a disposable executable returning
  0, 6 or 3. The first two branches parse the JSON; 3 remains an error. New
  result files have mode 0600 in exclusive private working directories.
- Executed the manual-launch shell block extracted directly from the new guide
  using JupyterLab 4.6.4 / Server 2.21.1 and isolated HOME/config/data/runtime.
  Its runtime is private, the OS assigns a nonzero port, and actual OpenSSH
  ProxyJump discovery/open yields a verified unmanaged server and normal login
  page. The native metadata bytes remain unchanged. CLI Ctrl-C exits 130 while
  the original server stays alive. Only generated loopback SSH/Jupyter processes
  and paths are used and cleaned. No kernel computation is needed for this
  documentation acceptance.
- Executed the documented ipykernel registration in isolated user data and
  checked the resulting interpreter path and kernelspec listing. The environment
  creation recipe pins the already observed stack; no remote scientific
  environment or global kernelspec was installed/changed during this review.
- Normal-sandbox Chrome checks seven new/expanded pages at 1440x1050 and 390x844
  under the /jupyhop/ mount, without horizontal page overflow. Search for
  missing_tmux returns troubleshooting. Desktop/mobile screenshots were inspected;
  all owned preview/browser resources were closed.
- External Sphinx linkcheck passes after respecting GitHub rate-limit backoff.
  Original links and new upstream Jupyter/IPython references remain accessible.
- Temporary wheel/sdist rebuild and source-artifact inspection pass: all new
  guides/configuration inputs are included, generated HTML/cache is excluded,
  and MIT/version/entrypoint/zero-mandatory-dependency checks remain satisfied.
  These local review artifacts are not uploaded or substituted for Conda 0.2.0.
- All 241 existing unit tests pass on Python 3.14.9 with
  `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q`. The initial shared-shell
  invocation stopped before collection because an unrelated installed smonitor
  pytest plugin imported an unavailable module. Disabling third-party plugin
  autoload isolates the repository tests; that external project was not modified.

Local validation uses an exclusive temporary documentation environment rather
than modifying the active shared development environment. Hosted deployment
results are recorded in the closeout below.

## Files and acceptance

New user guides: [remote setup](../docs/remote-setup.md),
[sessions/states/storage](../docs/sessions.md), [JSON reference](../docs/json-reference.md)
and [client update](../docs/upgrading.md). Updated pages cover quickstart,
installation, managed/existing servers, environments, configuration, SSH,
recovery, scripting, security, troubleshooting and their navigation indexes.
README adds public Conda installation and the new entry points. Devguide CLI
doctor scope and roadmap publication summaries now match implementation/evidence.

The current Linux 0.2.0 workflows have a documented install/prepare/open or
start/reconnect/stop/archive path, actionable failure branches, exact reference
contracts and tested examples. Completeness is bounded by that implemented scope.
macOS, broader endpoints/authentication, archive restoration/deletion, automatic
kernel restoration and additional supervision backends remain future work.
Physical client/network/logout observations retain the limits in report 23.

Next: continue user stabilization within the supported Linux matrix and review
documentation alongside each behavioral change. M7 features remain separate.

## Publication closeout

Reviewed candidate ee4d4b408e80df03e0bed931fc912f02b48c770c passes the
[documentation workflow](https://github.com/uibcdf/jupyhop/actions/runs/42642182999):
strict build checks all 27 pages and 1381 local references; official Pages
artifact deployment succeeds. Independent receiving checks validate HTTPS
normally for all 27 public pages and confirm the four new guides plus updated
configuration, scripting and troubleshooting content.

The same candidate's [source workflow](https://github.com/uibcdf/jupyhop/actions/runs/42642183001)
passes all six jobs. Each Python 3.11–3.14 runs 310 tests; lint/types, artifacts,
installed-client upgrades, server comparisons, browser workflows and real Unix
account/password acceptance with fixture cleanup pass their configured gates.

The subsequent documentary closeout records these observations without changing
the deployed HTML inputs, relabeling the tested candidate, replacing Conda bytes
or creating a release. The scoped documentation review is complete; future
platform/site-policy claims still require their separate evidence.
