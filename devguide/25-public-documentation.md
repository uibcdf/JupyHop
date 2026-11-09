# 25 — Public Sphinx documentation

Status: user documentation and publication workflow implemented; local build,
HTML checks and browser acceptance passed. Hosted deployment is pending observed
results. The maintainer authorized preparing and publishing the public website.

## Content delivered

The site describes the implemented 0.2.0 Linux workflows. Getting started covers
Conda/source installation, first open, existing servers and managed launch. The
user guide covers SSH/passwords/ProxyJump, helper/server/kernel environments,
profiles, multiple hosts and recovery. Reference/support includes the CLI, JSON/
exit codes, compatibility, troubleshooting and credentials. Project pages cover
release notes, contribution/documentation builds and package publication.

The existing-server/managed-server distinction is explicit from the homepage.
Discovery stays partial; only verified managed UUIDs authorize stop/archive.
Site persistence, process loss and unperformed physical-client cases retain the
limits recorded in the stabilization evidence. macOS remains future issue #2.
Examples use generated roles, reserved example domains and placeholder paths.
Existing Markdown guide URLs are preserved; references to design/evidence outside
the site link to their canonical GitHub files.

## D47 — Small Sphinx/MyST toolchain and parser-derived CLI

Use Sphinx, myst-parser, PyData Sphinx Theme and sphinx-copybutton. They match the
neighboring projects' documentation approach while allowing the existing Markdown
guides to remain source documents. No notebook execution or automatic private
Python API catalog is required for this CLI-first tool.

The verified local builder is CPython 3.14, Sphinx 9.2.0, MyST Parser 5.1.0,
PyData Theme 0.24.0 and copybutton 0.5.2. Direct documentation dependencies are
bounded to these minor release families in the optional docs extra and dedicated
Conda environment. Sphinx 9.2 requires Python >=3.13; the documented build uses
3.14. Client support remains CPython 3.11–3.14 with zero mandatory Python packages.

A small Sphinx directive constructs jupyhop.cli._parser and renders its current
root/subcommand help. It invokes no CLI commands, SSH or Jupyter operations.
This deliberately couples documentation to one internal parser factory instead
of maintaining duplicate option definitions or adding a CLI-reference package.
An internal parser refactor must preserve/update this integration; docs CI catches
an import/rendering failure. All eight commands and their options are checked
against the generated HTML.

## D48 — Pages artifact deployment

The reviewed UIBCDF Sphinx publisher at
[eab6e26](https://github.com/uibcdf/action-sphinx-docs-to-gh-pages/blob/eab6e2605bb35738275e4ee5c89941f4bc2f6f99/action.yml)
targets a generated gh-pages branch, creates runner-local Git commits and uses
force push. That is its existing publication contract, not a discovered defect.
For this new site, select GitHub's official Pages artifact workflow instead:
build/check once, retain the validated output, then deploy that artifact without
writing a repository branch.

Official checkout/setup/configure/upload/deploy actions are pinned to reviewed
release commits. Build has read-only contents permission; deployment has Pages
write and OIDC token permissions in the github-pages environment. Pull requests
build/validate without deployment. Main pushes and manual main dispatch can
publish only after the build/check job succeeds. No package/token publication,
source tag or Conda rebuild is part of documentation deployment.

References: [Sphinx Markdown](https://www.sphinx-doc.org/en/master/usage/markdown.html),
[MyST references](https://myst-parser.readthedocs.io/en/latest/syntax/cross-referencing.html),
[GitHub Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## Validation observed locally

- Strict Sphinx build (-n -W --keep-going) passes with no warnings. The site has
  21 source documents and 23 generated HTML pages including search/index.
- The offline HTML check passes 1105 local links/resource references/fragments,
  required user guides and all current CLI commands/options. Theme HTML/Jinja
  fragments under _static are resources, not rendered site documents.
- Fault injection into a copy of the actual build rejects a missing page and a
  missing fragment. Sphinx caches stay outside the publishable HTML tree.
- Normal-sandbox Chrome with an exclusive temporary profile passes desktop,
  CLI-sidebar and mobile layout without horizontal page overflow under the
  /jupyhop/ path. Browser search for ProxyJump returns SSH results. The preview
  server and owned Chrome processes were closed afterward.
- External Sphinx linkcheck passes after respecting a GitHub rate-limit backoff;
  local-reference acceptance remains independent of external service availability.
- All 241 existing unit tests, lint/format and strict types pass. Product SSH/
  Jupyter code and protocols are unchanged; hosted client checks remain separate.

The source manifest includes documentation Python, CSS and Makefile, and prunes
docs/_build. Artifact inspection checks the source inputs and refuses generated
documentation in an sdist. HTML is neither a mandatory runtime dependency nor
part of the client wheel.

## Files and remaining acceptance

Main changes: [site entry](../docs/index.md), task guides in docs/,
[Sphinx config](../docs/conf.py), [CLI directive](../docs/_ext/jupyhop_cli.py),
[HTML checker](../experiments/docs_check.py), [Makefile](../docs/Makefile),
[Conda builder](../devtools/conda-envs/docs_env.yaml),
[workflow](../.github/workflows/docs.yml), optional dependencies, README/
contribution links and source-manifest/artifact checks.

Observe the exact hosted build/deployment, confirm HTTPS delivery, navigation,
search/resources and the live CLI page before marking publication complete.
Record the resulting URL/run and keep private workstation/profile data outside
the repository. Package 0.2.0's already qualified Conda bytes remain unchanged.
After publication, continue user stabilization within the documented Linux
boundary; optional M7 features are outside this documentation increment.
