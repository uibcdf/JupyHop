---
myst:
  html_meta:
    description: "Choose your first JupyHop workflow: install locally, check SSH, open an existing Jupyter server or prepare a new remote session."
    "property=og:description": "Choose your first JupyHop workflow: install locally, check SSH, open an existing Jupyter server or prepare a new remote session."
---

(getting-started)=
# Choose your starting point

JupyHop runs on your **local Linux computer**, beside the browser. Jupyter and
its kernels run on the **remote Linux computer** you reach through SSH.
You normally install JupyHop only locally.

## First time here?

**[Follow the Quickstart →](quickstart.md)**

It takes you from client installation to a working notebook. You choose one of
two paths: open a server that is running already, or start a named server in an
existing remote environment.

## Need to prepare something first?

| Your situation | Next step |
| --- | --- |
| You need the local client | [Install JupyHop](installation.md), then return to the Quickstart |
| SSH does not reach the remote computer yet | [Set up SSH or a gateway route](ssh.md); verify ordinary SSH first |
| You do not know which remote environment contains Jupyter | [Find or prepare the remote environment](remote-setup.md) |
| Jupyter is already running and SSH works | [Open the existing server](existing-servers.md) |
| You want JupyHop to start and manage a project | [Start a managed session](managed-sessions.md) |

## Already connected once?

[Return to the same living kernel](recovery.md),
[choose and finish sessions in the menu](managed-sessions.md#manage-from-one-terminal),
or [reuse profiles and inspect several hosts](configuration.md).
If something went differently from the example, begin with
[Troubleshooting](troubleshooting.md); it links each symptom to a safe next check.

```{toctree}
:maxdepth: 1
:hidden:

installation
quickstart
remote-setup
existing-servers
managed-sessions
```
