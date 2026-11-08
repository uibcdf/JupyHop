# Temporary accounts for M5

Run all commands from the repository root. Requires Linux, OpenSSH server/client,
`useradd`/`userdel` and a native system Python >=3.11 exposing pidfd APIs.
No packages are installed by this script.

1. As the ordinary development user:

   ```console
   python -m experiments.m5_accounts prepare
   ```

2. Replace `PATH_FROM_PREPARE` below with the printed private `/tmp` directory:

   ```console
   sudo /usr/bin/python3 -m experiments.m5_accounts provision --root PATH_FROM_PREPARE
   python -m experiments.m5_accounts check --root PATH_FROM_PREPARE
   ```

The fixture creates two uniquely named users/groups and private homes, generated
SSH keys and a separate sshd listening only on loopback. It uses its own config
and pinned host key; the normal SSH service/configuration is unchanged. The
accounts have password authentication disabled and keys limited to loopback.
Root-owned state under `/run` records exact account and daemon identities.
`/run/sshd` is created if absent for OpenSSH privilege separation.

3. After acceptance testing, remove the fixture:

   ```console
   sudo /usr/bin/python3 -m experiments.m5_accounts cleanup --root PATH_FROM_PREPARE
   ```

Cleanup terminates processes belonging to the two generated accounts, removes
their homes/accounts/groups, and stops the pinned private sshd. It refuses changed
identities or unrelated root state. It then prints the command for removing your
remaining temporary client keys. Existing users, data and SSH services are outside
its cleanup scope. Do not use the generated homes for work you intend to retain.

Thirteen unprivileged tests cover preparation/privacy, path constraints, refusal
without sudo, changed account identity/PID refusal and symlink rejection. Native
pidfd termination was exercised only on an owned disposable child. Actual account
provisioning was performed explicitly by the operator, and the real-account
acceptance passed. Run `experiments.m5_account_acceptance --root PATH_FROM_PREPARE
--server-python ABSOLUTE_SHARED_PYTHON` as the ordinary user for that check;
the chosen Jupyter environment must be readable/executable by both accounts.
Operator cleanup requires sudo and remains explicit. For the recorded M5 run,
the operator completed cleanup; absence of both users/groups, their processes,
the private listener and privileged state was verified. The remaining temporary
keys/configuration and dedicated shared server environment were also removed.
