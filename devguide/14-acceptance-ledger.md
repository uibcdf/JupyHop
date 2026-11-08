# 14 — Acceptance ledger

Date: 2026-11-07. Every scenario in [08](08-scenarios-and-acceptance.md)
has a gate and a test target below. `A-<scenario>` is a **planned acceptance
test ID**, not an existing automated test. M0 spikes are feasibility evidence;
they do not satisfy later product gates. Details, versions and isolation:
[M0 report](13-m0-validation.md). M1 coverage: [M1 report](15-m1-foundations.md).

For future gates the fixture, assertions and failure output follow the expected
behavior of the corresponding row in 08. Real infrastructure is never a fixture.
SEC gates apply from the first relevant prototype onward, not only at release.

| Scenario | Gate | Test target / current evidence | Product acceptance |
| --- | --- | --- | --- |
| NET-01 | M2 | `A-NET-01` | Pending |
| NET-02 | M2 | `A-NET-02` | Pending |
| NET-03 | M2 | `A-NET-03` | Pending |
| NET-04 | M2 | `A-NET-04` | Pending |
| NET-05 | M5 | `A-NET-05` | Pending |
| NET-06 | M2 | `A-NET-06` | Pending |
| NET-07 | M5 | `A-NET-07` | Pending |
| NET-08 | M0 | Design boundary in 01, 08 and 13 | M0 satisfied; no relay promised |
| DISC-01 | M2 | `A-DISC-01` | Pending |
| DISC-02 | M2 | `A-DISC-02` | Pending |
| DISC-03 | M2/M5 | `A-DISC-03`; `experiments.m0_spike` | Pending (M0 feasibility only) |
| DISC-04 | M2 | `A-DISC-04`; `experiments.m0_spike` | Pending (M0 feasibility only) |
| DISC-05 | M2 | `A-DISC-05`; `experiments.m0_spike` | Pending (M0 feasibility only) |
| DISC-06 | M2 | `A-DISC-06` | Pending |
| DISC-07 | M2 | `A-DISC-07`; `experiments.m0_spike` | Pending (M0 feasibility only) |
| DISC-08 | M2 | `A-DISC-08` | Pending |
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
| SEC-01 | M1 | `A-SEC-01` | Pending |
| SEC-02 | M2 | `A-SEC-02`; `experiments.m0_spike` | Pending (M0 feasibility only) |
| SEC-03 | M1/M2 | `A-SEC-03` | Pending |
| SEC-04 | M4/M5 | `A-SEC-04` | Pending |
| SEC-05 | M2 | `A-SEC-05`; `experiments.m0_spike` | Pending (M0 feasibility only) |
| SEC-06 | M2 | `A-SEC-06` | Pending |
| SEC-07 | M2/M4 | `A-SEC-07` | Pending |
| SEC-08 | M1 | `A-SEC-08`; `experiments.m0_spike` | Pending (M0 feasibility only) |
| NET-09 | M2/M6 | `A-NET-09` | Pending |
| NET-10 | M2 | `A-NET-10`; `experiments.m0_spike` | Pending (M0 feasibility only) |
| NET-11 | M2/M6 | `A-NET-11` | Pending |
| NET-12 | M4/M5 | `A-NET-12` | Pending |
| NET-13 | M4 | `A-NET-13` | Pending |
| NET-14 | M5 | `A-NET-14` | Pending |
| NET-15 | M5/M6 | `A-NET-15` | Pending |
| DISC-09 | M2/M5 | `A-DISC-09`; `experiments.m0_spike` | Pending (M0 feasibility only) |
| DISC-10 | M2 | `A-DISC-10` | Pending |
| DISC-11 | M2 | `A-DISC-11` | Pending |
| DISC-12 | M2/M4 | `A-DISC-12`; `experiments.m0_spike` | Pending (M0 feasibility only) |
| LIFE-13 | M4 | `A-LIFE-13` | Pending |
| LIFE-14 | M4/M6 | `A-LIFE-14` | Pending |
| LIFE-15 | M4/M6 | `A-LIFE-15` | Pending |
| LIFE-16 | M4 | `A-LIFE-16` | Pending |
| LIFE-17 | M4 | `A-LIFE-17` | Pending |
| UX-01 | M2 | `A-UX-01` | Pending |
| UX-02 | M2 | `A-UX-02` | Pending |
| UX-03 | M2 | `A-UX-03` | Pending |
| UX-04 | M4 | `A-UX-04` | Pending |
| UX-05 | M2 | `A-UX-05` | Pending |
| UX-06 | M1/M2 | `A-UX-06` | Pending |
| UX-07 | M4/M6 | `A-UX-07` | Pending |
| UX-08 | M5 | `A-UX-08` | Pending |
