"""
tests/test_phase2_sandbox.py
Validates Phase 2 Delivery Milestone (Playwright Browser Sandbox & CDP Screencast):
1. Isolated Headless Chromium lifecycle without physical desktop takeover.
2. Native CDP Screencast stream capturing live JPEG frames.
3. Asynchronous MJPEG stream generator (mjpeg_frame_generator) yielding frames at >= 20 FPS.
4. Interactive DOM selector extractor locating and indexing up to 25 elements (#id, [name], text=, tag).
5. State signature S(t) computation (deterministic 16-char SHA-256 hash, stability and mutation).
6. Primitive browser actions dispatcher (navigate, click, fill, scroll, wait, finish) with safe timeout guards.
7. Graceful error handling for missing/invalid selectors and unknown actions without crashing.
"""

import asyncio
import sys
import time
from pathlib import Path

# Ensure Windows stdout/stderr supports UTF-8
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.browser_sandbox import BrowserSandbox, PlaywrightSandbox


async def test_sandbox_lifecycle() -> BrowserSandbox:
    print("\n--- Test 1: Playwright Sandbox Lifecycle & CDP Screencast ---")
    sandbox = BrowserSandbox(headless=True)
    await sandbox.initialize()
    assert sandbox.is_running, "Sandbox should be marked as running"
    print("  [PASS] Playwright Chromium started in headless mode (zero desktop takeover).")

    # Allow CDP session to capture initial frames
    await asyncio.sleep(0.5)
    frame = await sandbox.get_frame()
    assert frame and len(frame) > 100, f"Frame capture failed or frame is too small ({len(frame)} bytes)"
    assert frame[:2] == b"\xff\xd8", "Frame is not a valid JPEG format"
    print(f"  [PASS] Captured native CDP screencast JPEG frame: {len(frame)} bytes (Magic byte: {frame[:2].hex()}).")

    fps = sandbox.fps
    print(f"  [PASS] CDP Screencast tracker: {fps:.1f} FPS.")
    return sandbox


async def test_mjpeg_stream_throughput(sandbox: BrowserSandbox):
    print("\n--- Test 2: Asynchronous MJPEG Stream Generator (>= 20 FPS Throughput) ---")
    frames_received = 0
    target_frames = 25  # Sample exactly 25 continuous frames

    gen = sandbox.mjpeg_frame_generator()
    start_time = time.time()
    for _ in range(target_frames):
        chunk = await asyncio.wait_for(gen.__anext__(), timeout=0.5)
        assert b"--frame" in chunk, "Missing multipart boundary in MJPEG chunk"
        assert b"Content-Type: image/jpeg" in chunk, "Missing Content-Type header in MJPEG chunk"
        assert b"\xff\xd8" in chunk, "JPEG payload missing in MJPEG chunk"
        frames_received += 1

    elapsed = time.time() - start_time
    measured_fps = frames_received / elapsed
    print(f"  [PASS] MJPEG generator yielded {frames_received} frames in {elapsed:.2f}s ({measured_fps:.1f} FPS).")
    assert measured_fps >= 20.0, f"Throughput failed: expected >= 20.0 FPS, got {measured_fps:.1f} FPS"
    print(f"  [PASS] Stream throughput satisfies >= 20 FPS threshold.")


async def test_dom_extraction(sandbox: BrowserSandbox):
    print("\n--- Test 3: DOM Interactive Element Extraction (Max 25 Elements) ---")
    # Load income certificate portal simulation
    await sandbox.load_portal_simulation("income")
    elements = await sandbox.extract_dom_elements(max_items=25)

    assert len(elements) > 0, "No interactive elements extracted"
    assert len(elements) <= 25, f"Extracted {len(elements)} elements, exceeded max 25 ceiling"

    selectors = [e["selector"] for e in elements]
    print(f"  [PASS] Extracted {len(elements)} interactive selectors from page:")
    for el in elements:
        print(f"    - Tag: <{el['tag']}> | Selector: {el['selector']} | Text: '{el['text']}' | Val: '{el['value']}'")

    # Assert expected selectors are present in income portal
    assert "#applicant_name" in selectors, "Missing #applicant_name input"
    assert "#annual_income" in selectors, "Missing #annual_income input"
    assert "#submit_btn" in selectors, "Missing #submit_btn button"
    assert "#jurisdiction_select" in selectors, "Missing #jurisdiction_select select"
    print("  [PASS] All critical portal form selectors successfully identified with hierarchy.")

    # Test interface contract: extract_interactive_elements
    url, contracted_elements = await sandbox.extract_interactive_elements()
    assert isinstance(url, str), "URL must be string"
    assert len(contracted_elements) == len(elements), "Contracted extraction count mismatch"
    print(f"  [PASS] extract_interactive_elements() contract returned URL: '{url}' and {len(contracted_elements)} items.")


async def test_state_signature_stability_and_mutation(sandbox: BrowserSandbox):
    print("\n--- Test 4: State Signature S(t) Determinism & Mutation ---")
    # 1. Deterministic stability: two consecutive calls on identical DOM must produce identical hash
    sig1 = await sandbox.get_state_signature()
    sig2 = await sandbox.get_state_signature()
    assert len(sig1) == 16, f"Signature length must be exactly 16, got {len(sig1)}"
    assert sig1 == sig2, f"Signature not deterministic across identical state: {sig1} != {sig2}"
    print(f"  [PASS] State signature stability verified: S(t1) == S(t2) == {sig1}")

    # 2. Mutation audit: modifying DOM element must mutate signature S(t) != S(t-1)
    await sandbox.execute_action("fill", "#applicant_name", "सदानंद कदम")
    sig3 = await sandbox.get_state_signature()
    assert sig3 != sig1, f"Signature should mutate after filling input: {sig3} == {sig1}"
    print(f"  [PASS] State signature mutation verified: S(t3) [{sig3}] != S(t1) [{sig1}]")


async def test_primitive_actions(sandbox: BrowserSandbox):
    print("\n--- Test 5: Primitive Browser Actions Dispatcher ---")

    # 1. Navigate to Sanjay Gandhi Niradhar Pension portal
    success, detail = await sandbox.execute_action("navigate", "", "pension")
    assert success, f"Navigate action failed: {detail}"
    print(f"  [PASS] Navigate: {detail}")

    elements = await sandbox.extract_dom_elements(25)
    selectors = [e["selector"] for e in elements]
    assert "#beneficiary_name" in selectors, "Failed to navigate to pension portal"

    # 2. Fill beneficiary name
    success, detail = await sandbox.execute_action("fill", "#beneficiary_name", "गंगूबाई विठ्ठल कांबळे")
    assert success, f"Fill action failed: {detail}"
    print(f"  [PASS] Fill: {detail}")

    # 3. Click category button
    success, detail = await sandbox.execute_action("click", "#category_btn", "")
    assert success, f"Click action failed: {detail}"
    print(f"  [PASS] Click: {detail}")

    # 4. Click submit pension
    success, detail = await sandbox.execute_action("click", "#submit_pension", "")
    assert success, f"Click action failed: {detail}"
    print(f"  [PASS] Click: {detail}")

    # 5. Scroll viewport
    success, detail = await sandbox.execute_action("scroll", "", "")
    assert success, f"Scroll action failed: {detail}"
    print(f"  [PASS] Scroll: {detail}")

    # 6. Wait action
    success, detail = await sandbox.execute_action("wait", "", "")
    assert success, f"Wait action failed: {detail}"
    print(f"  [PASS] Wait: {detail}")

    # 7. Finish action
    success, detail = await sandbox.execute_action("finish", "", "")
    assert success, f"Finish action failed: {detail}"
    print(f"  [PASS] Finish: {detail}")


async def test_action_error_guards(sandbox: BrowserSandbox):
    print("\n--- Test 6: Safe Timeout Guards & Error Resilience ---")

    # 1. Unknown action
    success, detail = await sandbox.execute_action("invalid_action_xyz", "", "")
    assert not success, "Unknown action should fail safely"
    assert "Unknown primitive action" in detail
    print(f"  [PASS] Unknown action handled: {detail}")

    # 2. Missing selector for click
    success, detail = await sandbox.execute_action("click", "", "")
    assert not success, "Click without selector should fail safely"
    assert "Missing selector" in detail
    print(f"  [PASS] Missing click selector handled: {detail}")

    # 3. Missing selector for fill
    success, detail = await sandbox.execute_action("fill", "", "some_val")
    assert not success, "Fill without selector should fail safely"
    assert "Missing selector" in detail
    print(f"  [PASS] Missing fill selector handled: {detail}")

    # 4. Non-existent selector timeout guard
    start_t = time.time()
    success, detail = await sandbox.execute_action("click", "#selector_that_does_not_exist_at_all", "")
    dur = time.time() - start_t
    assert not success, "Non-existent selector should fail safely"
    assert "Action execution error" in detail or "Timeout" in detail
    print(f"  [PASS] Timeout guard trapped missing selector in {dur:.2f}s: {detail[:60]}...")


async def main():
    print("=======================================================")
    print("STARTING PHASE 2 BROWSER SANDBOX & CDP STREAM TESTS")
    print("=======================================================")
    sandbox = await test_sandbox_lifecycle()
    try:
        await test_mjpeg_stream_throughput(sandbox)
        await test_dom_extraction(sandbox)
        await test_state_signature_stability_and_mutation(sandbox)
        await test_primitive_actions(sandbox)
        await test_action_error_guards(sandbox)
        print("\n=======================================================")
        print("ALL PHASE 2 TESTS PASSED SUCCESSFULLY! (Sandbox & CDP Stream)")
        print("=======================================================")
    finally:
        await sandbox.close()
        assert not sandbox.is_running, "Sandbox should be marked as stopped after close"
        print("  [PASS] Browser sandbox session closed cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
