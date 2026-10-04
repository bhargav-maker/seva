#!/usr/bin/env python3
"""
SEVA AI Mobile Tool
Android ADB bridge for e-Pik Pahani and other mobile-only government apps.
Supports both direct REST API (Tier A) and USB ADB bridge (Tier B).
"""

import asyncio
import json
import logging
import subprocess
import time
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


class MobileAppController:
    """Controls Android apps via ADB or direct REST API."""

    def __init__(self):
        self.adb_path = "adb"
        self.device_id: Optional[str] = None
        self.connected = False

    async def initialize(self) -> bool:
        try:
            result = await self._run_adb("devices")
            lines = result.strip().split('\n')[1:]
            devices = [line.split('\t')[0] for line in lines if '\tdevice' in line]
            if devices:
                self.device_id = devices[0]
                self.connected = True
                logger.info(f"ADB device connected: {self.device_id}")
                return True
            logger.warning("No ADB device found")
            return False
        except Exception as e:
            logger.error(f"ADB initialization failed: {e}")
            return False

    async def _run_adb(self, args: str, timeout: int = 10) -> str:
        cmd = f"{self.adb_path} {args}"
        if self.device_id:
            cmd = f"{self.adb_path} -s {self.device_id} {args}"
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode != 0:
            raise RuntimeError(f"ADB command failed: {stderr.decode()}")
        return stdout.decode()

    async def execute_action(self, app_package: str, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.connected:
            await self.initialize()
            if not self.connected:
                return {"status": "FAILED", "error": "No ADB device connected"}

        try:
            if action == "launch":
                return await self._launch_app(app_package)
            elif action == "tap":
                return await self._tap_coordinates(payload.get("x", 0), payload.get("y", 0))
            elif action == "text":
                return await self._input_text(payload.get("text", ""))
            elif action == "swipe":
                return await self._swipe(payload.get("x1", 0), payload.get("y1", 0), payload.get("x2", 0), payload.get("y2", 0))
            elif action == "keyevent":
                return await self._keyevent(payload.get("keycode", 66))
            elif action == "screencap":
                return await self._screencap()
            elif action == "rest_api":
                return await self._rest_api_call(payload)
            else:
                return {"status": "FAILED", "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"Mobile action failed: {e}")
            return {"status": "FAILED", "error": str(e)}

    async def _launch_app(self, package: str) -> Dict[str, Any]:
        await self._run_adb(f"shell monkey -p {package} -c android.intent.category.LAUNCHER 1")
        await asyncio.sleep(2)
        return {"status": "SUCCESS", "transaction_id": f"launch_{int(time.time())}"}

    async def _tap_coordinates(self, x: int, y: int) -> Dict[str, Any]:
        await self._run_adb(f"shell input tap {x} {y}")
        await asyncio.sleep(0.5)
        return {"status": "SUCCESS", "transaction_id": f"tap_{int(time.time())}"}

    async def _input_text(self, text: str) -> Dict[str, Any]:
        escaped = text.replace(' ', '%s').replace('&', '\\&').replace('(', '\\(').replace(')', '\\)')
        await self._run_adb(f"shell input text '{escaped}'")
        await asyncio.sleep(0.3)
        return {"status": "SUCCESS", "transaction_id": f"text_{int(time.time())}"}

    async def _swipe(self, x1: int, y1: int, x2: int, y2: int) -> Dict[str, Any]:
        await self._run_adb(f"shell input swipe {x1} {y1} {x2} {y2} 300")
        await asyncio.sleep(0.5)
        return {"status": "SUCCESS", "transaction_id": f"swipe_{int(time.time())}"}

    async def _keyevent(self, keycode: int) -> Dict[str, Any]:
        await self._run_adb(f"shell input keyevent {keycode}")
        await asyncio.sleep(0.3)
        return {"status": "SUCCESS", "transaction_id": f"key_{int(time.time())}"}

    async def _screencap(self) -> Dict[str, Any]:
        path = f"/sdcard/seva_screencap_{int(time.time())}.png"
        await self._run_adb(f"shell screencap -p {path}")
        local_path = f"C:\\Users\\Praka\\Downloads\\{path.split('/')[-1]}"
        await self._run_adb(f"pull {path} {local_path}")
        return {"status": "SUCCESS", "transaction_id": f"screencap_{int(time.time())}", "file_path": local_path}

    async def _rest_api_call(self, payload: Dict) -> Dict[str, Any]:
        import aiohttp
        url = payload.get("url")
        method = payload.get("method", "POST")
        headers = payload.get("headers", {})
        data = payload.get("data", {})

        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, json=data) as resp:
                result = await resp.json()
                return {"status": "SUCCESS", "transaction_id": f"api_{int(time.time())}", "data": result}


_mobile_controller: Optional[MobileAppController] = None


def register_mobile_tools(mcp: FastMCP):
    @mcp.tool()
    async def control_mobile_app(app_package: str, action: str, payload: dict) -> str:
        """
        Operates Android apps (e.g., e-Pik Pahani) via USB ADB or direct REST API.
        Returns JSON: {"status": "SUCCESS|FAILED", "transaction_id": str, ...}
        """
        global _mobile_controller
        if _mobile_controller is None:
            _mobile_controller = MobileAppController()
        result = await _mobile_controller.execute_action(app_package, action, payload)
        return json.dumps(result, ensure_ascii=False)

    @mcp.tool()
    async def check_adb_connection() -> str:
        """Checks if ADB device is connected."""
        global _mobile_controller
        if _mobile_controller is None:
            _mobile_controller = MobileAppController()
        connected = await _mobile_controller.initialize()
        return json.dumps({"connected": connected, "device_id": _mobile_controller.device_id})

    @mcp.tool()
    async def e_pik_pahani_workflow(survey_number: str, taluka: str, village: str, crop: str, season: str, owner_name: str) -> str:
        """
        Complete e-Pik Pahani workflow via ADB.
        Automates: launch app -> select survey -> select crop -> submit.
        """
        global _mobile_controller
        if _mobile_controller is None:
            _mobile_controller = MobileAppController()

        await _mobile_controller.initialize()
        if not _mobile_controller.connected:
            return json.dumps({"status": "FAILED", "error": "No Android device connected for e-Pik Pahani"})

        try:
            await _mobile_controller.execute_action("com.maharashtra.epikpahani", "launch", {})
            await asyncio.sleep(3)

            await _mobile_controller.execute_action("com.maharashtra.epikpahani", "tap", {"x": 500, "y": 300})
            await _mobile_controller.execute_action("com.maharashtra.epikpahani", "text", survey_number)
            await _mobile_controller.execute_action("com.maharashtra.epikpahani", "keyevent", {"keycode": 66})

            await _mobile_controller.execute_action("com.maharashtra.epikpahani", "tap", {"x": 500, "y": 400})
            await _mobile_controller.execute_action("com.maharashtra.epikpahani", "text", taluka)

            await _mobile_controller.execute_action("com.maharashtra.epikpahani", "tap", {"x": 500, "y": 500})
            await _mobile_controller.execute_action("com.maharashtra.epikpahani", "text", village)

            await _mobile_controller.execute_action("com.maharashtra.epikpahani", "tap", {"x": 500, "y": 600})
            await _mobile_controller.execute_action("com.maharashtra.epikpahani", "text", crop)

            await _mobile_controller.execute_action("com.maharashtra.epikpahani", "tap", {"x": 500, "y": 700})
            await _mobile_controller.execute_action("com.maharashtra.epikpahani", "text", season)

            await _mobile_controller.execute_action("com.maharashtra.epikpahani", "tap", {"x": 500, "y": 800})
            await _mobile_controller.execute_action("com.maharashtra.epikpahani", "text", owner_name)

            await _mobile_controller.execute_action("com.maharashtra.epikpahani", "tap", {"x": 540, "y": 900})

            await _mobile_controller.execute_action("com.maharashtra.epikpahani", "screencap", {})

            return json.dumps({
                "status": "SUCCESS",
                "transaction_id": f"epik_{int(time.time())}",
                "summary": f"e-Pik Pahani submitted for Survey {survey_number}, {crop} ({season})"
            })
        except Exception as e:
            return json.dumps({"status": "FAILED", "error": str(e)})