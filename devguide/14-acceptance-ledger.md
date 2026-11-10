# 14 — Acceptance ledger

Created: 2026-11-07; updated through 0.2.0 stabilization. Every scenario in [08](08-scenarios-and-acceptance.md)
has a gate and a test target below. `A-<scenario>` is a **planned acceptance
test ID**, not an existing automated test. M0 spikes are feasibility evidence;
they do not satisfy later product gates. Details, versions and isolation:
[M0 report](13-m0-validation.md). M1 coverage: [M1 report](15-m1-foundations.md).
Current existing-server acceptance: [M2 report](16-m2-existing-servers.md).
Managed launch evidence: [M3 report](17-m3-managed-launch.md).
Lifecycle/kernel/legacy-runner evidence: [M4 report](18-m4-lifecycle.md).
Profiles/multi-host/real-account/archive evidence: [M5 report](19-m5-scientific-workflows.md).
Beta compatibility/security/artifact evidence: [M6 report](20-m6-beta-readiness.md).
Native SSH authentication, real-site endurance and installed upgrade evidence:
[0.2.0 report](23-02-stabilization-evidence.md).
Later operator-observed physical home-client access, kernel recovery and
single-host concurrency: [pilot report](28-02-physical-client-pilot.md). This does
not claim moving the same live kernel between two physical clients.

For future gates the fixture, assertions and failure output follow the expected
behavior of the corresponding row in 08. Automated fixtures use disposable
targets. Explicit operator site pilots create only marked temporary resources on
authorized hosts; real infrastructure is never hard-coded into a fixture.
SEC gates apply from the first relevant prototype onward, not only at release.

| Scenario | Gate | Test target / current evidence | Product acceptance |
| --- | --- | --- | --- |
| NET-01 | M2/0.2 | Disposable jump/browser, real password-route doctor in 23 and physical home/gateway/workstation pilot in 28 | Real home-route manual/managed Jupyter login and kernel operation observed; earlier second-target doctor remains a prerequisite-only observation |
| NET-02 | M2/M5 | Real-account acceptance; protected runtime and foreign open/lifecycle refusal | M5 verified with two actual Unix UIDs; authorization follows the selected SSH account |
| NET-03 | M2/0.2 | Direct integration and authorized real-site manual/managed workflows in 23 | Direct SSH/Jupyter verified on a real Linux target; broader physical network transitions remain manual |
| NET-04 | M2 | `test_zero_config_discovery_and_open_existing_server[direct]` | M2 direct SSH mechanism verified; site policy external |
| NET-05 | M5 | Two-target profile/kernel integration plus M4 independent-client test | Two-target mechanisms verified on disposable targets; physical home pilot covers two servers on one workstation, not simultaneous physical destinations |
| NET-06 | M2 | M1 unavailable-jump test; `test_ssh_policy_denies_forwarding_without_stopping_server` | M2 failure/state preservation verified |
| NET-07 | M5 | Changed SSH route integration uses the same alias/config, direct then ProxyJump | Fresh OpenSSH routing and retained session identity; physical network move remains a site test |
| NET-08 | M0 | Design boundary in 01, 08 and 13 | M0 satisfied; no relay promised |
| DISC-01 | M2 | `test_zero_config_discovery_and_open_existing_server`; browser smoke | M2 verified |
| DISC-02 | M2 | `test_multiple_servers_custom_paths_and_duplicate_runtime_metadata` | M2 verified |
| DISC-03 | M2/M5 | M2 Conda spike, configured paths/helper-server tests and physical pilot's manual Conda server | Plain open from home finds the Conda server in the ordinary runtime; exhaustive environment enumeration not promised |
| DISC-04 | M2 | Directory-symlink/private-permission unit tests; empty JSON discovery test | M2 partial/unsupported behavior verified |
| DISC-05 | M2/0.2 | `test_read_only_metadata_does_not_delete_stale_or_expose_token`; crowded-runtime/two-server integration | No stale-file deletion; 110 stale records cannot hide verified live endpoints within the bounded scan |
| DISC-06 | M2 | `test_stop_is_refused_without_any_remote_action` | M2 stop guard verified; no adoption |
| DISC-07 | M2 | Password integration; token form/browser smoke | M2 normal login verified; custom auth not universally supported |
| DISC-08 | M2 | Documented M2 auth/proxy/version restrictions in 16 | M2 limitation explicit; no universal proxy compatibility claim |
| LIFE-01 | M3/0.2 | Managed integration/browser smoke and physical home-client launch in 28 | Correct remote user/workdir/Python, normal auth and kernel execution observed, including on the real home route |
| LIFE-02 | M4/0.2 | Independent-client/browser acceptance and 7200-second real-site pilot | Same kernel/memory after browser/tunnel/first-client exit and two hours disconnected; configured KillUserProcesses=false/Linger=no observed, forced last logout unmeasured |
| LIFE-03 | M4 | Independent-client integration and `experiments.m4_reconnect` | Separate software clients verified; 28 adds same-home-client recovery over a real gateway, not transfer of one kernel between physical computers |
| LIFE-04 | M4 | `test_two_owned_forwards_share_one_live_kernel_without_restarting` | Same kernel memory verified, including after one tunnel closes |
| LIFE-05 | M4/0.2 | Selected-only stop/pidfd guards and physical pilot stopping A while B executes | Graceful stop verified; B retains PID/memory/result after A stops; no forced escalation |
| LIFE-06 | M4 | `test_reboot_and_reused_process_identity_never_signal_a_live_server` | Boot identity change simulated; stale detection/no restoration; no physical reboot |
| LIFE-07 | M4 | Lost start/stop replies integration; stop-intent retry unit test | Retry before/after signal verified; no automatic duplicate/restart |
| LIFE-08 | M4 | M3 same-name concurrent starts; M4 concurrent stops | Reservations/atomicity and lifecycle concurrency verified |
| LIFE-09 | M3/M4/0.2 | Distinct-server integration and physical two-server pilot | Distinct UUIDs, ports, workdirs and kernel PIDs observed; explicit fixed-port requests are not implemented |
| LIFE-10 | M5 | `experiments.m5_account_acceptance` | Actual users independently launch identical display names; records/credentials/lifecycle stay separate |
| LIFE-11 | M4 | Independent-client test preserves notebook session/kernel IDs without POST on reconnect | Existing association verified; multiple-kernel frontend UX remains broader acceptance |
| LIFE-12 | M4 | `test_crashed_server_is_stale_and_is_never_automatically_restarted`; M2 endpoint loss checks | Process loss verified; no kernel resurrection or automatic restart |
| SCI-01 | M5 | CLI profile precedence, two-target Conda/venv launch, native stdlib helper and shared server environment | Explicit executable profiles verified; no activation hooks or CLI kernel-selector promise |
| SCI-02 | M5 | Profile integration verifies relative HOME path, symlink canonicalization, tilde, spaces/Unicode/metacharacters | Remote path semantics verified; long-running scientific filesystem behavior remains broader acceptance |
| SCI-03 | M4/0.2 | Independent-client/browser acceptance and real-site toy computation | Same kernel/session/memory and advancing workload after 7200 disconnected seconds; physical last logout/reboot unmeasured |
| SCI-04 | M5 | `test_two_hosts_profile_launch_science_reconnect_and_archive` | Two disposable targets/kernels/forwards coexist and reconnect without losing memory |
| SCI-05 | M7 | `A-SCI-05` | Pending |
| SEC-01 | M1 | `test_unknown_host_key_is_refused`; `test_changed_host_key_is_refused` | M1 satisfied (SSH trust) |
| SEC-02 | M2 | M3 native password hash/login; wrong-password denial; M2 token/password login | M2/M3 authentication verified; no argv or generic-output credentials |
| SEC-03 | M1/M2/0.2 | Stdin/allowlist/browser tests; native controlling-terminal/RPC tests and real password-route doctor | Jupyter password stays outside argv/output/history; OpenSSH owns SSH password input; terminal echo/restoration and private RPC separation verified |
| SEC-04 | M4/M5 | Real-account foreign read/open/stop/archive refusal and pidfd/provenance checks | Verified with actual distinct UIDs; neither user's healthy server is modified by rejected actions |
| SEC-05 | M2/0.2 | Configured-forward/collision, borrowed-forward cancellation and missing-private-socket tests | Only owned foreground masters/explicit forwards used; no network fallback, unrelated listener/master adoption or cross-forward cancellation |
| SEC-06 | M2 | Browser availability unit tests; actual no-browser/signal CLI integration | M2 verified |
| SEC-07 | M2/M5 | Schema/atomic/ownership checks plus archive live/uncertain/start-time/symlink refusal | Explicit inactive move preserves recovery evidence; permanent deletion unimplemented |
| SEC-08 | M1 | `test_remote_shell_injection_is_literal`; unit input/quoting tests | M1 satisfied (SSH arguments) |
| NET-09 | M2/M6 | Strict metadata address gate; reviewed IPv4-only policy in beta compatibility guide | Explicit unsupported boundary; no IPv6 transport support claimed |
| NET-10 | M2 | Custom /science/ HTTP/WS integration and real browser smoke | M2 simple ASCII base paths verified |
| NET-11 | M2/M6 | Strict metadata HTTPS gate; reviewed beta compatibility guide | Explicit unsupported boundary; no TLS-verification bypass or HTTPS support claimed |
| NET-12 | M4/M5 | Lost replies, fresh forwards and changed OpenSSH route test | Broken-connection/config-route mechanisms verified; actual suspend/OS network move remains manual |
| NET-13 | M4 | M2 owned-master collision; M4 simultaneous tunnels/same-kernel test | Independent owned forwards verified; unrelated SSH never reused/killed |
| NET-14 | M5 | Changed-route/duplicate-alias test plus same-name conflict through alternate alias | Distinct routes reach one registry/UUID; no silent duplicate managed process |
| NET-15 | M5/M6 | `test_large_contents_and_sustained_websocket_through_jump` | 8 MiB API roundtrip with SHA256, 64 requests/64 KiB output each on one WebSocket; bounded loopback smoke, not a WAN endurance claim |
| DISC-09 | M2/M5 | Custom-runtime integration, per-host runtime_dirs config and explicit path merging | Known-path coverage verified; another client needs the same custom path preference where not in remote state |
| DISC-10 | M2 | Empty JSON discovery test; complete=false invariant | M2 honest partial result verified; arbitrary endpoint override unimplemented |
| DISC-11 | M2/0.2 | Multiple-server/custom-runtime/deduplication and crowded-runtime integration | Live endpoints retained across runtime paths when stale diagnostics fill the sample; discovery remains bounded and partial |
| DISC-12 | M2/M6 | `test_live_password_rotation_requires_fresh_authorized_login` | Same live server, fresh client/tunnel; old password denied, new password accepted; existing cookies follow upstream policy |
| LIFE-13 | M4 | Reused PID/start/socket refusal and M2 changed-server open guard | Replacement identity cannot authorize old-session stop/open; no continuity claim |
| LIFE-14 | M4/M6/0.2 | Trusted M3/M5 runner acceptance and installed-client upgrade experiment | Live kernel/registry/runner bytes preserved across tested installed old/new clients; no migration/replacement |
| LIFE-15 | M4/M6/0.2 | Historical runners, installed 0.1.0-to-0.2.0 acceptance, strict parser/schema refusal | Tested combinations and refusal policy documented; arbitrary client versions/future migrations not promised |
| LIFE-16 | M4 | CLI SIGINT/SIGHUP/SIGTERM cleanup and independent-client memory acceptance | Attached lifetime/kernel survival verified; no attached-forward survival promise after SIGKILL/network failure |
| LIFE-17 | M4 | Lost start reply after spawn/checkpoint; status promotes starting to ready | Recovery verified without duplicate launch; pre-PID unconfirmed intent remains starting |
| UX-01 | M2/0.2 | Zero-config direct/jump integration, browser smoke and physical manual-server open | Plain open HOST from home works with existing SSH config/default runtime and normal token login |
| UX-02 | M2 | Empty JSON discovery with exit 6 and partial diagnostics | M2 verified |
| UX-03 | M2/0.2/0.3 | Selection tests, multiple-server integration and physical two-choice picker | 0.3 adds exact names and consistent interactive choice after the 0.2 pilot; no noninteractive guessing |
| UX-04 | M4/M5 | Exact UUID confirmation for stop/archive, no-SSH guard, live archive refusal | Neither lifecycle action guesses a selection; archive never authorizes stopping a live server |
| UX-05 | M2 | No-browser/signal CLI integration; browser-unavailable unit case | M2 verified; URL limited to current client |
| UX-06 | M1/M2 | M2 stdlib discovery helper; M3 separate stdlib start/open helper | M1–M3 no remote package installation verified; per-session runner written only by start |
| UX-07 | M4/M6 | Strict protocol/schema refusal, M3/M5 runner acceptance and version policy | Tested rollout/refusal and actionable errors; installed-helper upgrades and migrations are outside beta scope |
| UX-08 | M5 | Actual CLI/profile launch validates remote relative/tilde/symlink/Unicode/metacharacter paths | Literal path behavior verified without shell activation or injection |
| UX-09 | 0.3 | test_session_ux.py and disposable test_session_ux_ssh.py | Names/choosers, UUID pinning, EOF/headless rules and actual menu Ctrl-C/SIGTERM pass in the four-Python suite; installed acceptance in 30 |
| UX-10 | 0.3 | test_session_inventory.py, test_session_ux.py and installed package smoke | Read-only bounds/unknown counts, history guards, full-registry refusal and separate completion phases pass locally and in installed/hosted acceptance; see 30 |
| UX-11 | 0.3 | test_feedback.py, test_diagnostics.py, native SSH auth and ssh_permissions_smoke | Curation/redaction/context, actual notebook API, native default policy and terminal passwords pass; qualified candidate in 30 |
