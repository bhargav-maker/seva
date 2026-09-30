# E2E Test Infra: SEVA AI Kiosk Platform

## Test Philosophy
- **Opaque-box & Requirement-driven:** Derived strictly from `ORIGINAL_REQUEST.md` and user-facing specifications, exercising the platform via HTTP REST API (`/api/*`), live stream (`/api/stream`), and frontend browser interaction as an end user would.
- **Methodology:** Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial Testing + Real-World Workload Testing.
- **Progressive Testability:** Tier 1 tests verify fundamental isolated behaviors before complex cross-module dependencies are tested.

---

## Feature Inventory & Test Mapping
| # | Feature | Requirement | Tier 1 | Tier 2 | Tier 3 |
|---|---------|-------------|:------:|:------:|:------:|
| 1 | Dual-Model LLM Gateway | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 2 | Deterministic Schema Validator | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 3 | Context Pruner (Rolling Scratchpad) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 4 | Safe Fallback Engine | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 5 | Isolated Chromium Sandbox | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 6 | Interactive DOM Extractor | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 7 | Native CDP Screencast Stream | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 8 | Primitive Action Executor | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 9 | State Signature Calculator | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 10 | State Mutation Auditor | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 11 | Two-Step Stall Detector | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 12 | FastAPI Host REST Endpoints | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 13 | Hard Step Budget Guard | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 14 | Finish Termination Gate | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 15 | Touch-Friendly Rural Kiosk UI | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |
| 16 | Multi-Lingual Web Speech STT/TTS | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |
| 17 | Live MJPEG Viewport Display | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |
| 18 | Real-Time ODAV Audit Log | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |
| 19 | Human Checkpoint Modal | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |
| 20 | Ephemeral Data Purge | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |
| 21 | High-Fidelity Mock Portals | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |

---

## Test Architecture
- **Test Runner:** `pytest` running against the active virtual environment (`vdak-vm/venv` or `vdak-host/venv`).
- **Test Invocation:** `python -m pytest tests/ -v`
- **Pass/Fail Semantics:** All assertions must pass with exit code 0. Zero warnings treated as failures where strict schema/type assertions apply.
- **Directory Layout:**
  - `tests/test_phase1_schema.py`: M1 unit and schema assertions.
  - `tests/test_phase2_sandbox.py`: M2 Playwright and CDP screencast assertions.
  - `tests/test_phase3_odav.py`: M3 ODAV engine, state machine, and REST API assertions.
  - `tests/test_phase4_kiosk_ui.py`: M4 frontend, speech integration, and portal mock assertions.
  - `tests/e2e/test_tier1_feature.py`: Tier 1 feature isolation tests.
  - `tests/e2e/test_tier2_boundary.py`: Tier 2 boundary and corner case tests.
  - `tests/e2e/test_tier3_pairwise.py`: Tier 3 pairwise cross-feature interaction tests.
  - `tests/e2e/test_tier4_workload.py`: Tier 4 end-to-end citizen workflow application scenarios.
  - `tests/e2e/test_tier5_adversarial.py`: Tier 5 white-box coverage hardening tests.

---

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Dialect | Complexity |
|---|----------|--------------------|---------|------------|
| 1 | Income Certificate Application (`/portal/income`) | F1, F2, F3, F5, F6, F7, F8, F9, F10, F12, F14, F16 | Marathi (`mr-IN`) | High |
| 2 | 7/12 Satbara Land Record Search (`/portal/satbara`) | F1, F2, F4, F5, F6, F7, F8, F9, F11, F12, F16, F18 | Hindi (`hi-IN`) | Medium |
| 3 | Farmer Agriculture Subsidy Application (`/portal/mahadbt`) | F1, F2, F5, F6, F7, F8, F9, F10, F12, F13, F14, F19 | Marathi (`mr-IN`) | High |
| 4 | Ration Card Status Lookup (`/portal/ration`) | F1, F2, F4, F5, F6, F7, F8, F9, F10, F12, F14, F15 | English (`en-IN`) | Medium |
| 5 | Mid-Session Citizen Cancellation & Data Purge | F5, F12, F15, F20 | Marathi (`mr-IN`) | Medium |
| 6 | Form Submission Requiring Human OTP Checkpoint | F5, F6, F8, F9, F11, F12, F17, F19 | Hindi (`hi-IN`) | High |

---

## Coverage Thresholds
- **Tier 1:** ≥5 test cases per feature (21 features × 5 = 105 tests)
- **Tier 2:** ≥5 test cases per feature (boundary/error values: empty inputs, overflow, bad JSON, timeouts, rate limits) (21 features × 5 = 105 tests)
- **Tier 3:** Pairwise feature combinations (at least 25 pairwise tests)
- **Tier 4:** ≥6 realistic end-to-end citizen public service workflows
- **Total Minimum Expected:** ~241 test cases
