import asyncio
from agent import KioskBrowserAgent

async def test_run():
    agent = KioskBrowserAgent(headless=True)
    print("Launching Chromium...")
    if await agent.start():
        print("Navigating to portal...")
        await agent.navigate_to("https://example.com")
        frame = await agent.capture_frame()
        if frame:
            print(f"Success! Captured frame size: {len(frame)} bytes")
        await agent.stop()
    else:
        print("Failed to start browser.")

if __name__ == "__main__":
    asyncio.run(test_run())
