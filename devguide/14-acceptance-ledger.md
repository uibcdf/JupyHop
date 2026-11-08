# 14 — Acceptance ledger

Created: 2026-11-07; updated through M2: 2026-11-08. Every scenario in [08](08-scenarios-and-acceptance.md)
has a gate and a test target below. `A-<scenario>` is a **planned acceptance
test ID**, not an existing automated test. M0 spikes are feasibility evidence;
they do not satisfy later product gates. Details, versions and isolation:
[M0 report](13-m0-validation.md). M1 coverage: [M1 report](15-m1-foundations.md).
Current existing-server acceptance and limitations: [M2 report](16-m2-existing-servers.md).

For future gates the fixture, assertions and failure output follow the expected
behavior of the corresponding row in 08. Real infrastructure is never a fixture.
SEC gates apply from the first relevant prototype onward, not only at release.

| Scenario | Gate | Test target / current evidence | Product acceptance |
| --- | --- | --- | --- |
| NET-01 | M2 | `test_zero_config_discovery_and_open_existing_server[destination]`; `experiments.browser_smoke` | M2 verified via disposable jump |
| NET-02 | M2 | M1 selected-UID test; `test_another_process_owner_cannot_be_verified` | M2 identity mechanism verified; two-user topology M5 pending |
| NET-03 | M2 | `test_zero_config_discovery_and_open_existing_server[direct]` | M2 direct route verified; physical LAN not tested |
| NET-04 | M2 | `test_zero_config_discovery_and_open_existing_server[direct]` | M2 direct SSH mechanism verified; site policy external |
| NET-05 | M5 | `A-NET-05` | Pending |
| NET-06 | M2 | M1 unavailable-jump test; `test_ssh_policy_denies_forwarding_without_stopping_server` | M2 failure/state preservation verified |
| NET-07 | M5 | `A-NET-07` | Pending |
| NET-08 | M0 | Design boundary in 01, 08 and 13 | M0 satisfied; no relay promised |
| DISC-01 | M2 | `test_zero_config_discovery_and_open_existing_server`; browser smoke | M2 verified |
| DISC-02 | M2 | `test_multiple_servers_custom_paths_and_duplicate_runtime_metadata` | M2 verified |
| DISC-03 | M2/M5 | `experiments.m2_conda_smoke`; stdlib helper integration | M2 verified for known paths; broader profiles M5 pending |
| DISC-04 | M2 | Directory-symlink/private-permission unit tests; empty JSON discovery test | M2 partial/unsupported behavior verified |
| DISC-05 | M2 | `test_read_only_metadata_does_not_delete_stale_or_expose_token`; identity-change integration | M2 verified; no stale-file deletion |
| DISC-06 | M2 | `test_stop_is_refused_without_any_remote_action` | M2 stop guard verified; no adoption |
| DISC-07 | M2 | Password integration; token form/browser smoke | M2 normal login verified; custom auth not universally supported |
| DISC-08 | M2 | Documented M2 auth/proxy/version restrictions in 16 | M2 limitation explicit; no universal proxy compatibility claim |
| LIFE-01 | M3 | `A-LIFE-01` | Pending |
| LIFE-02 | M4 | `A-LIFE-02`; `experiments.m0_spike` | Pending (M0 feasibility only) |
| LIFE-03 | M4 | `A-LIFE-03`; `experiments.m0_spike` | Pending (M0 feasibility only) |
| LIFE-04 | M4 | `A-LIFE-04`; `experiments.m0_spike` | Pending (M0 feasibility only) |
| LIFE-05 | M4 | `A-LIFE-05` | Pending |
| LIFE-06 | M4 | `A-LIFE-06` | Pending |
| LIFE-07 | M4 | `A-LIFE-07` | Pending |
| LIFE-08 | M4 | `A-LIFE-08` | Pending |
| LIFE-09 | M3/M4 | `A-LIFE-09`; `experiments.m0_spike` | Pending (M0 feasibility only) |
| LIFE-10 | M5 | `A-LIFE-10` | Pending |
| LIFE-11 | M4 | `A-LIFE-11` | Pending |
| LIFE-12 | M4 | `A-LIFE-12` | Pending |
| SCI-01 | M5 | `A-SCI-01` | Pending |
| SCI-02 | M5 | `A-SCI-02` | Pending |
| SCI-03 | M4 | `A-SCI-03` | Pending |
| SCI-04 | M5 | `A-SCI-04` | Pending |
| SCI-05 | M7 | `A-SCI-05` | Pending |
| SEC-01 | M1 | `test_unknown_host_key_is_refused`; `test_changed_host_key_is_refused` | M1 satisfied (SSH trust) |
| SEC-02 | M2 | Token/password normal login and invalid-auth integration | M2 verified; no auth bypass |
| SEC-03 | M1/M2 | Allowlisted discovery unit test; real browser navigation-history smoke | M2 generic-output and normal-login handling verified |
| SEC-04 | M4/M5 | `A-SEC-04` | Pending |
| SEC-05 | M2 | `test_private_master_ignores_configured_forward_and_retries_collision` | M2 verified; unrelated listener untouched |
| SEC-06 | M2 | Browser availability unit tests; actual no-browser/signal CLI integration | M2 verified |
| SEC-07 | M2/M4 | M2 unsafe metadata/filesystem unit tests; identity-change integration | M2 metadata gate verified; managed registry M4 pending |
| SEC-08 | M1 | `test_remote_shell_injection_is_literal`; unit input/quoting tests | M1 satisfied (SSH arguments) |
| NET-09 | M2/M6 | 16 documents IPv4-only policy; strict address validation | M2 explicit unsupported boundary; IPv6 support M6 pending |
| NET-10 | M2 | Custom /science/ HTTP/WS integration and real browser smoke | M2 simple ASCII base paths verified |
| NET-11 | M2/M6 | 16 documents HTTPS/complex URL refusal; strict metadata scheme gate | M2 explicit unsupported boundary; TLS compatibility M6 pending |
| NET-12 | M4/M5 | `A-NET-12` | Pending |
| NET-13 | M4 | M2 owned-master collision and independent-open integration | M2 baseline verified; full M4 recovery gate pending |
| NET-14 | M5 | `A-NET-14` | Pending |
| NET-15 | M5/M6 | `A-NET-15` | Pending |
| DISC-09 | M2/M5 | Custom-runtime integration; `experiments.m2_conda_smoke` | M2 known-path coverage verified; exhaustive discovery not promised |
| DISC-10 | M2 | Empty JSON discovery test; complete=false invariant | M2 honest partial result verified; arbitrary endpoint override unimplemented |
| DISC-11 | M2 | `test_multiple_servers_custom_paths_and_duplicate_runtime_metadata` | M2 verified |
| DISC-12 | M2/M4 | Invalid-auth and fresh-login integration; no credential cache | M2 baseline verified; live rotation acceptance M4 pending |
| LIFE-13 | M4 | `A-LIFE-13` | Pending |
| LIFE-14 | M4/M6 | `A-LIFE-14` | Pending |
| LIFE-15 | M4/M6 | `A-LIFE-15` | Pending |
| LIFE-16 | M4 | `A-LIFE-16` | Pending |
| LIFE-17 | M4 | `A-LIFE-17` | Pending |
| UX-01 | M2 | Zero-config direct/jump integration; browser smoke | M2 verified for supported defaults |
| UX-02 | M2 | Empty JSON discovery with exit 6 and partial diagnostics | M2 verified |
| UX-03 | M2 | Selection unit tests and multiple-server integration | M2 verified; no noninteractive guessing |
| UX-04 | M4 | `A-UX-04` | Pending |
| UX-05 | M2 | No-browser/signal CLI integration; browser-unavailable unit case | M2 verified; URL limited to current client |
| UX-06 | M1/M2 | `test_stdlib_helper_finds_jupyter_in_another_environment` | M1/M2 no-install path verified |
| UX-07 | M4/M6 | `A-UX-07` | Pending |
| UX-08 | M5 | `A-UX-08` | Pending |
