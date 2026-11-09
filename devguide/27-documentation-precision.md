# 27 — Documentation precision and continuous example checks

Date: 2026-11-09.
Status: published at https://www.uibcdf.org/jupyhop/. Local acceptance, hosted
documentation/source workflows and independent HTTPS receiving checks pass.

## Review findings and changes

The [first review](26-documentation-review.md) supplied the missing onboarding
and reference guides. This second pass found precision and maintenance gaps,
rather than a need for more public pages:

- Helper/managed-server Python uses -I. The environment guide and remote
  prerequisite check now explain why PYTHONPATH/user-site-only imports are
  insufficient. Kernel commands retain their own kernelspec behavior.
- The JSON current-boot/account identity.scope and stable machine/account
  registry-directory scope use different inputs. The JSON/session references
  now distinguish them and use different invented values in archive examples.
  Consumers use returned paths rather than constructing a path from identity.scope.
- Managed start uses its private server configuration and enables installed
  JupyterLab, with a server/API fallback. Other automatic server extensions and
  ordinary user Jupyter config are not loaded by this launcher. Existing-server
  access retains the external launcher's configuration within the supported boundary.
- A managed UUID identifies a server with potentially several notebooks/kernels.
  Stop affects all its kernels. Simultaneous clients can use independent forwards;
  reconnecting must select the original Jupyter notebook/kernel session, and
  JupyHop does not coordinate concurrent file edits.
- New Jupyter password confirmation precedes native SSH authentication during
  start. The prompt roles and ordering are explicit.
- The release guide's dispatch example is now a template for an approved
  unoccupied coordinate; it no longer suggests re-uploading published 0.2.0=py_0.

These are clarifications of existing behavior. Installed-client code, protocols,
registry schema, dependencies and published packages are unchanged.

## Sustainable validation

Extend the existing stdlib-only HTML checker, rather than adding a documentation
plugin or a second CLI definition. `make -C docs check` now also validates
standalone console-fenced JupyHop argv against the real parser with canonical
option names, TOML fences against parse_config, and JSON decoding. It supports
continued console lines and a single explicit stdin redirection without opening
its file. It reports a source path/block line while suppressing raw bad values.

This is syntax/config validation, not a shell interpreter, endpoint test or
formal CLI JSON schema. Complex shell control flow and runtime prerequisites
retain their separate acceptance checks. Contributor/testing guides document
these boundaries. D47's parser-derived documentation direction remains unchanged.

## Observed local acceptance

- Strict Sphinx 9.2.0 / MyST 5.1.0 build: 27 HTML pages, no warnings, 1387 local
  links/resources/fragments and all generated command/option sections pass.
- The source gate passes 63 CLI commands, two TOML configurations and five JSON
  examples without executing any of those commands.
- Eleven focused checker tests cover malformed options, abbreviations, options
  on the wrong command, shell chaining, malformed redirection, config versions/
  fields and JSON. They also prove no CLI/SSH/shell execution or input-file read,
  ordinary-text fences are ignored and a missing source directory fails.
- All 252 unit tests pass on CPython 3.14.9; lint/format and strict types for the
  20 installed-client modules pass. No scientific session is used by these checks.
- A reproducible temporary-module experiment observes ordinary Python importing
  both a temporary PYTHONPATH module and a temporary user-site module; -I cannot
  import either and disables user-site imports. Nothing is installed in a real
  user site. An independent mocked-identity experiment changes only boot identity:
  the observation scope changes while the machine/account state root stays fixed.
- External linkcheck passes, including the official Python isolated-mode reference.

## Files, limitations and next step

Updated public pages: environments, remote setup, managed sessions, recovery,
sessions, JSON reference, troubleshooting, release and contributor guides.
README, CONTRIBUTING and the devguide testing policy track those corrections.
Maintenance code: [example/HTML checker](../experiments/docs_check.py) and
[focused regressions](../tests/test_docs_check.py).

The documented Linux 0.2.0 scope is covered without adding features or navigation
pages. The physical-client/site-policy and future-platform limits in reports
23–26 remain explicit. Continue user stabilization within that scope; additional
platforms/features need their own evidence. Hosted acceptance is recorded below.

## Publication closeout

Candidate 6a603a0b95e6fbcd06f206bc3fc79a863c02859d passes the
[documentation workflow](https://github.com/uibcdf/jupyhop/actions/runs/42652971630):
strict HTML checks, the new 63-command/two-TOML/five-JSON source gate, artifact
upload and Pages deployment all succeed. Independent HTTPS checks receive all
27 public HTML pages and confirm updated content in eight affected guides.

Its [source workflow](https://github.com/uibcdf/jupyhop/actions/runs/42652971451)
passes all six jobs. Every Python 3.11–3.14 observes 321 passing tests, including
the eleven new checker regressions. Lint/types, complete safe artifacts,
installed-client upgrade, browser, server comparisons and real Unix account/
password acceptance pass their configured gates; generated account cleanup is
confirmed. The local review also builds/inspects temporary wheel/sdist artifacts
without publishing or replacing any package.

This documentary closeout records the observed candidate rather than relabeling
later commits as that tested source. Public HTML inputs and installed-client
behavior are unchanged by the closeout. The second review is complete within
the stated Linux scope; new platform/site guarantees remain separate work.
