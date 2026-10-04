#!/usr/bin/env python3
"""
SEVA AI Printer & WhatsApp Tool
Thermal printer driver (ESC/POS) + WhatsApp Cloud API dispatcher.
"""

import asyncio
import base64
import json
import logging
import os
import tempfile
from typing import Any, Dict, Optional

import aiohttp
import win32print
import win32ui
from PIL import Image, ImageDraw, ImageFont
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


class ThermalPrinter:
    """ESC/POS thermal printer driver for Windows."""

    def __init__(self, printer_name: Optional[str] = None):
        self.printer_name = printer_name or self._get_default_printer()
        self.line_width = 32

    def _get_default_printer(self) -> str:
        try:
            return win32print.GetDefaultPrinter()
        except Exception:
            return "POS-58"

    def _get_printer_handle(self):
        return win32print.OpenPrinter(self.printer_name)

    def print_text(self, text: str, align: str = "left", bold: bool = False, size: int = 1) -> bool:
        try:
            hprinter = self._get_printer_handle()
            try:
                hdc = win32ui.CreateDC()
                hdc.CreatePrinterDC(self.printer_name)
                hdc.StartDoc("SEVA AI Receipt")
                hdc.StartPage()

                font_size = 16 * size
                font = win32ui.CreateFont({
                    "name": "Consolas",
                    "height": font_size,
                    "weight": 700 if bold else 400,
                })
                hdc.SelectObject(font)

                lines = text.split('\n')
                y = 20
                for line in lines:
                    if align == "center":
                        x = (hdc.GetDeviceCaps(8) - hdc.GetTextExtent(line)[0]) // 2
                    elif align == "right":
                        x = hdc.GetDeviceCaps(8) - hdc.GetTextExtent(line)[0] - 20
                    else:
                        x = 20
                    hdc.TextOut(x, y, line)
                    y += font_size + 4

                hdc.EndPage()
                hdc.EndDoc()
            finally:
                win32print.ClosePrinter(hprinter)
            return True
        except Exception as e:
            logger.error(f"Print failed: {e}")
            return False

    def print_image(self, image_path: str) -> bool:
        try:
            hprinter = self._get_printer_handle()
            try:
                hdc = win32ui.CreateDC()
                hdc.CreatePrinterDC(self.printer_name)
                hdc.StartDoc("SEVA AI Image")
                hdc.StartPage()

                img = Image.open(image_path)
                img_width, img_height = img.size
                ratio = min(hdc.GetDeviceCaps(8) / img_width, hdc.GetDeviceCaps(10) / img_height)
                new_size = (int(img_width * ratio), int(img_height * ratio))

                dib = ImageDraw.Draw(img)
                hdc.StretchBlt((0, 0), new_size, dib, (0, 0), img.size, win32ui.SRCCOPY)

                hdc.EndPage()
                hdc.EndDoc()
            finally:
                win32print.ClosePrinter(hprinter)
            return True
        except Exception as e:
            logger.error(f"Image print failed: {e}")
            return False

    def cut_paper(self) -> bool:
        try:
            hprinter = self._get_printer_handle()
            try:
                raw_data = bytes([0x1D, 0x56, 0x00])
                win32print.WritePrinter(hprinter, raw_data)
            finally:
                win32print.ClosePrinter(hprinter)
            return True
        except Exception:
            return False


class WhatsAppDispatcher:
    """WhatsApp Cloud API dispatcher for document delivery."""

    def __init__(self):
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
        self.api_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"

    async def send_document(self, phone_number: str, file_path: str, caption: str = "") -> Dict[str, Any]:
        if not self.access_token or not self.phone_number_id:
            return {"status": "FAILED", "error": "WhatsApp credentials not configured"}

        try:
            mime_type = "application/pdf"
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                mime_type = "image/jpeg"

            with open(file_path, 'rb') as f:
                file_data = f.read()

            media_id = await self._upload_media(file_data, mime_type)
            if not media_id:
                return {"status": "FAILED", "error": "Media upload failed"}

            payload = {
                "messaging_product": "whatsapp",
                "to": phone_number.replace('+', '').replace(' ', ''),
                "type": "document",
                "document": {
                    "id": media_id,
                    "caption": caption or "SEVA AI Document",
                    "filename": os.path.basename(file_path)
                }
            }

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=headers, json=payload) as resp:
                    result = await resp.json()
                    if resp.status == 200:
                        return {"status": "SUCCESS", "message_id": result.get("messages", [{}])[0].get("id")}
                    return {"status": "FAILED", "error": result}

        except Exception as e:
            logger.error(f"WhatsApp send failed: {e}")
            return {"status": "FAILED", "error": str(e)}

    async def _upload_media(self, file_data: bytes, mime_type: str) -> Optional[str]:
        upload_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/media"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = aiohttp.FormData()
        data.add_field('file', file_data, filename='document.pdf', content_type=mime_type)
        data.add_field('type', mime_type)
        data.add_field('messaging_product', 'whatsapp')

        async with aiohttp.ClientSession() as session:
            async with session.post(upload_url, headers=headers, data=data) as resp:
                result = await resp.json()
                if resp.status == 200:
                    return result.get("id")
        return None

    async def send_template(self, phone_number: str, template_name: str, language: str = "hi", params: list = None) -> Dict[str, Any]:
        if not self.access_token:
            return {"status": "FAILED", "error": "WhatsApp not configured"}

        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number.replace('+', '').replace(' ', ''),
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
            }
        }
        if params:
            payload["template"]["components"] = [{"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}]

        headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, headers=headers, json=payload) as resp:
                result = await resp.json()
                return {"status": "SUCCESS" if resp.status == 200 else "FAILED", "data": result}


_printer: Optional[ThermalPrinter] = None
_whatsapp: Optional[WhatsAppDispatcher] = None


def register_printer_tools(mcp: FastMCP):
    @mcp.tool()
    async def print_and_send_document(file_path: str, citizen_phone: str, print_paper: bool = True) -> str:
        """
        Sends document to thermal printer and dispatches PDF via WhatsApp.
        Returns JSON: {"print_status": "SUCCESS|FAILED", "whatsapp_status": "SUCCESS|FAILED", ...}
        """
        global _printer, _whatsapp

        if _printer is None:
            _printer = ThermalPrinter()
        if _whatsapp is None:
            _whatsapp = WhatsAppDispatcher()

        results = {"print_status": "SKIPPED", "whatsapp_status": "SKIPPED"}

        if print_paper:
            if file_path.lower().endswith('.pdf'):
                results["print_status"] = "SUCCESS" if _printer.print_text(_pdf_to_text(file_path)) else "FAILED"
            else:
                results["print_status"] = "SUCCESS" if _printer.print_image(file_path) else "FAILED"
            _printer.cut_paper()

        if citizen_phone:
            results["whatsapp_status"] = (await _whatsapp.send_document(citizen_phone, file_path))["status"]

        return json.dumps(results, ensure_ascii=False)

    @mcp.tool()
    async def print_receipt(transaction_data: dict, citizen_phone: str) -> str:
        """
        Generates and prints a formatted receipt for any transaction.
        """
        global _printer, _whatsapp

        if _printer is None:
            _printer = ThermalPrinter()
        if _whatsapp is None:
            _whatsapp = WhatsAppDispatcher()

        receipt = _generate_receipt(transaction_data)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(receipt)
            temp_path = f.name

        print_result = _printer.print_text(receipt, align="center")
        _printer.cut_paper()

        whatsapp_result = {"status": "SKIPPED"}
        if citizen_phone:
            pdf_path = await _text_to_pdf(receipt, transaction_data.get("service", "Service"))
            whatsapp_result = await _whatsapp.send_document(citizen_phone, pdf_path, "Your SEVA AI Receipt")

        return json.dumps({
            "print_status": "SUCCESS" if print_result else "FAILED",
            "whatsapp_status": whatsapp_result.get("status", "FAILED"),
            "receipt": receipt
        }, ensure_ascii=False)

    @mcp.tool()
    async def send_whatsapp_message(phone_number: str, template_name: str, language: str = "hi", params: list = None) -> str:
        """Sends a WhatsApp template message."""
        global _whatsapp
        if _whatsapp is None:
            _whatsapp = WhatsAppDispatcher()
        result = await _whatsapp.send_template(phone_number, template_name, language, params)
        return json.dumps(result, ensure_ascii=False)


def _generate_receipt(data: dict) -> str:
    lines = [
        "═" * 32,
        "   SEVA AI - ग्राम पंचायत रसीद   ",
        "═" * 32,
        f"सेवा: {data.get('service', 'N/A')}",
        f"आवेदक: {data.get('applicant', 'N/A')}",
        f"लेनदेन ID: {data.get('transaction_id', 'N/A')}",
        f"शुल्क: ₹{data.get('fee', 0):.2f}",
        f"स्थिति: {data.get('status', 'SUCCESS')}",
        f"दिनांक: {data.get('date', 'N/A')}",
        "─" * 32,
        "धन्यवाद! डिजिटल इंडिया",
        "═" * 32,
    ]
    return '\n'.join(lines)


def _pdf_to_text(pdf_path: str) -> str:
    try:
        import fitz
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception:
        return f"[Document: {os.path.basename(pdf_path)}]"


async def _text_to_pdf(text: str, title: str) -> str:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        path = f"C:\\Users\\Praka\\Downloads\\seva_receipt_{int(asyncio.get_event_loop().time())}.pdf"
        c = canvas.Canvas(path, pagesize=A4)
        width, height = A4
        y = height - 50
        for line in text.split('\n'):
            c.drawString(50, y, line)
            y -= 20
        c.save()
        return path
    except Exception:
        return ""