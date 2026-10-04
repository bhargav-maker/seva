#!/usr/bin/env python3
"""
SEVA AI Offline Tool
Offline scheme FAQ database & request queue engine for weak internet resilience.
"""

import asyncio
import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "seva_offline.db"
SCHEMES_JSON = Path(__file__).parent.parent.parent / "data" / "schemes.json"


@dataclass
class Scheme:
    id: str
    name: str
    category: str
    description: str
    eligibility: str
    documents: List[str]
    benefits: str
    application_process: str
    official_portal: str
    helpline: str
    language: str = "hi"


@dataclass
class QueuedRequest:
    id: str
    citizen_phone: str
    service: str
    parameters: Dict[str, Any]
    created_at: float
    status: str = "PENDING"
    attempts: int = 0
    last_error: str = ""


class OfflineDatabase:
    """Local SQLite database for offline schemes & request queue."""

    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._init_schema()
        self._load_schemes()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS schemes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                eligibility TEXT,
                documents TEXT,
                benefits TEXT,
                application_process TEXT,
                official_portal TEXT,
                helpline TEXT,
                language TEXT DEFAULT 'hi'
            );
            CREATE TABLE IF NOT EXISTS queued_requests (
                id TEXT PRIMARY KEY,
                citizen_phone TEXT NOT NULL,
                service TEXT NOT NULL,
                parameters TEXT NOT NULL,
                created_at REAL NOT NULL,
                status TEXT DEFAULT 'PENDING',
                attempts INTEGER DEFAULT 0,
                last_error TEXT DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_schemes_category ON schemes(category);
            CREATE INDEX IF NOT EXISTS idx_schemes_language ON schemes(language);
            CREATE INDEX IF NOT EXISTS idx_queue_status ON queued_requests(status);
        """)
        self.conn.commit()

    def _load_schemes(self):
        cursor = self.conn.execute("SELECT COUNT(*) FROM schemes")
        if cursor.fetchone()[0] > 0:
            return

        default_schemes = [
            Scheme(
                id="pm_kisan",
                name="PM-KISAN Samman Nidhi",
                category="कृषि",
                description="छोटे और सीमांत किसानों को प्रति वर्ष ₹6000 की आय सहायता",
                eligibility="2 हेक्टेयर तक की खेती योग्य भूमि वाले किसान परिवार",
                documents=["आधार कार्ड", "भूमि रिकॉर्ड (7/12)", "बैंक पासबुक", "मोबाइल नंबर"],
                benefits="₹2000 प्रति 4 महीने (₹6000/वर्ष) सीधे बैंक खाते में",
                application_process="pmkisan.gov.in पर ऑनलाइन पंजीकरण या CSC/सेतु केंद्र पर",
                official_portal="https://pmkisan.gov.in",
                helpline="155261 / 011-24300606",
                language="hi"
            ),
            Scheme(
                id="pm_kisan_mr",
                name="PM-किसान सम्मान निधि",
                category="शेती",
                description="लहान आणि सीमांत शेतकऱ्यांना वर्षी ₹6000 चे उत्पन्न मदत",
                eligibility="२ हेक्टरपर्यंत शेतयोग्य जमीन असलेले शेतकुटुंब",
                documents=["आधार कार्ड", "भूमी अभिलेख (७/१२)", "बँक पासबुक", "मोबाईल नंबर"],
                benefits="प्रत्येक ४ महिन्यांनंतर ₹२००० (₹६०००/वर्ष) थेट बँक खात्यात",
                application_process="pmkisan.gov.in वर ऑनलाईन नोंदणी किंवा CSC/सेतु केंद्रावर",
                official_portal="https://pmkisan.gov.in",
                helpline="155261 / 011-24300606",
                language="mr"
            ),
            Scheme(
                id="ayushman_bharat",
                name="Ayushman Bharat PM-JAY",
                category="आरोग्य",
                description="गरीब परिवारों के लिए ₹5 लाख तक का मुफ्त इलाज",
                eligibility="SECC 2011 डेटाबेस में शामिल परिवार, NFSA कार्डधारक",
                documents=["आधार कार्ड", "राशन कार्ड", "परिवार पहचान पत्र"],
                benefits="₹5 लाख प्रति परिवार प्रति वर्ष कैशलेस इलाज",
                application_process="नजदीकी आयुष्मान मित्र या CSC पर पंजीकरण",
                official_portal="https://pmjay.gov.in",
                helpline="14555",
                language="hi"
            ),
            Scheme(
                id="kisan_credit_card",
                name="Kisan Credit Card (KCC)",
                category="कृषि",
                description="किसानों को कम ब्याज पर अल्पकालिक ऋण",
                eligibility="कृषि योग्य भूमि वाले किसान, मौखिक पट्टेदार, बटाईदार",
                documents=["आधार कार्ड", "पैन कार्ड", "भूमि रिकॉर्ड", "पासपोर्ट फोटो", "बैंक पासबुक"],
                benefits="₹3 लाख तक ऋण @ 7% ब्याज (समय पर चुकाने पर 4%)",
                application_process="किसी भी बैंक शाखा या CSC पर आवेदन",
                official_portal="https://pmkisan.gov.in/kcc",
                helpline="1800-115-526",
                language="hi"
            ),
            Scheme(
                id="soil_health_card",
                name="Soil Health Card Scheme",
                category="कृषि",
                description="मिट्टी की गुणवत्ता जांच और उर्वरक सिफारिश",
                eligibility="सभी किसान जिनके पास कृषि भूमि है",
                documents=["आधार कार्ड", "भूमि रिकॉर्ड", "मोबाइल नंबर"],
                benefits="मुफ्त मिट्टी जांच, उर्वरक सिफारिश, फसल-विशिष्ट सलाह",
                application_process="कृषि विभाग या CSC पर नमूना जमा करें",
                official_portal="https://soilhealth.dac.gov.in",
                helpline="1800-180-1551",
                language="hi"
            ),
            Scheme(
                id="pma_urban",
                name="PMAY-Urban (Housing for All)",
                category="आवास",
                description="शहरी गरीबों के लिए पक्का घर",
                eligibility="EWS/LIG श्रेणी, कोई पक्का घर न हो, आधार लिंक",
                documents=["आधार कार्ड", "आय प्रमाण पत्र", "निवास प्रमाण", "बैंक पासबुक", "पासपोर्ट फोटो"],
                benefits="EWS: ₹2.5 लाख सब्सिडी, LIG/MIG: ब्याज सब्सिडी",
                application_process="pmaymis.gov.in पर ऑनलाइन या नगर निगम/CSC",
                official_portal="https://pmaymis.gov.in",
                helpline="1800-11-6446",
                language="hi"
            ),
            Scheme(
                id="ujjwala",
                name="Pradhan Mantri Ujjwala Yojana",
                category="ऊर्जा",
                description="BPL परिवारों को मुफ्त LPG कनेक्शन",
                eligibility="BPL परिवार की वयस्क महिला, कोई LPG कनेक्शन न हो",
                documents=["आधार कार्ड", "BPL राशन कार्ड", "बैंक पासबुक", "पासपोर्ट फोटो", "निवास प्रमाण"],
                benefits="मुफ्त LPG कनेक्शन + पहला सिलेंडर मुफ्त",
                application_process="नजदीकी गैस एजेंसी या CSC पर आवेदन",
                official_portal="https://pmuy.gov.in",
                helpline="1906 / 1800-2333-555",
                language="hi"
            ),
            Scheme(
                id="digital_india_land",
                name="Digital India Land Records Modernization",
                category="भू-अभिलेख",
                description="भू-अभिलेखों का डिजिटलीकरण (7/12, 8A, सातबारा)",
                eligibility="भूमि मालिक",
                documents=["आधार कार्ड", "पुराना 7/12", "संपत्ति कार्ड"],
                benefits="ऑनलाइन 7/12 निकाल, म्यूटेशन स्थिति, नक्शा देखें",
                application_process="mahabhumi.maharashtra.gov.in या राज्य पोर्टल",
                official_portal="https://mahabhumi.maharashtra.gov.in",
                helpline="1800-120-8040",
                language="hi"
            ),
            Scheme(
                id="ebkranti",
                name="e-Bhoomi / e-Kranti Land Records",
                category="भू-अभिलेख",
                description="कर्नाटक/अन्य राज्यों के ऑनलाइन भूमि रिकॉर्ड",
                eligibility="भूमि मालिक",
                documents=["आधार कार्ड", "पुराना RTC/पहानी"],
                benefits="ऑनलाइन RTC/पहानी, म्यूटेशन, नक्शा, फसल विवरण",
                application_process="राज्य e-भूमि पोर्टल या CSC",
                official_portal="https://landrecords.karnataka.gov.in",
                helpline="1800-425-0003",
                language="hi"
            ),
        ]

        for scheme in default_schemes:
            self.conn.execute("""
                INSERT OR REPLACE INTO schemes VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                scheme.id, scheme.name, scheme.category, scheme.description,
                scheme.eligibility, json.dumps(scheme.documents), scheme.benefits,
                scheme.application_process, scheme.official_portal, scheme.helpline,
                scheme.language
            ))
        self.conn.commit()
        logger.info(f"Loaded {len(default_schemes)} default schemes")

    def search_schemes(self, query: str, category: str = "", language: str = "hi", limit: int = 5) -> List[Scheme]:
        sql = "SELECT * FROM schemes WHERE language = ?"
        params = [language]
        if category:
            sql += " AND category = ?"
            params.append(category)
        if query:
            sql += " AND (name LIKE ? OR description LIKE ? OR eligibility LIKE ?)"
            params.extend([f"%{query}%"] * 3)
        sql += " LIMIT ?"
        params.append(limit)

        cursor = self.conn.execute(sql, params)
        results = []
        for row in cursor.fetchall():
            results.append(Scheme(
                id=row[0], name=row[1], category=row[2], description=row[3],
                eligibility=row[4], documents=json.loads(row[5]) if row[5] else [],
                benefits=row[6], application_process=row[7],
                official_portal=row[8], helpline=row[9], language=row[10]
            ))
        return results

    def get_scheme(self, scheme_id: str, language: str = "hi") -> Optional[Scheme]:
        cursor = self.conn.execute("SELECT * FROM schemes WHERE id = ? AND language = ?", (scheme_id, language))
        row = cursor.fetchone()
        if row:
            return Scheme(
                id=row[0], name=row[1], category=row[2], description=row[3],
                eligibility=row[4], documents=json.loads(row[5]) if row[5] else [],
                benefits=row[6], application_process=row[7],
                official_portal=row[8], helpline=row[9], language=row[10]
            )
        return None

    def queue_request(self, citizen_phone: str, service: str, parameters: Dict) -> str:
        req_id = f"req_{int(time.time() * 1000)}"
        self.conn.execute("""
            INSERT INTO queued_requests (id, citizen_phone, service, parameters, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (req_id, citizen_phone, service, json.dumps(parameters), time.time()))
        self.conn.commit()
        logger.info(f"Queued offline request: {req_id}")
        return req_id

    def get_pending_requests(self, limit: int = 50) -> List[QueuedRequest]:
        cursor = self.conn.execute("""
            SELECT * FROM queued_requests WHERE status = 'PENDING' ORDER BY created_at LIMIT ?
        """, (limit,))
        return [QueuedRequest(
            id=row[0], citizen_phone=row[1], service=row[2],
            parameters=json.loads(row[3]), created_at=row[4],
            status=row[5], attempts=row[6], last_error=row[7]
        ) for row in cursor.fetchall()]

    def update_request_status(self, req_id: str, status: str, error: str = ""):
        self.conn.execute("""
            UPDATE queued_requests SET status = ?, attempts = attempts + 1, last_error = ?
            WHERE id = ?
        """, (status, error, req_id))
        self.conn.commit()


_offline_db: Optional[OfflineDatabase] = None


def register_offline_tools(mcp: FastMCP):
    @mcp.tool()
    async def query_offline_schemes(scheme_name: str = "", category: str = "", language: str = "hi") -> str:
        """
        Answers government scheme eligibility queries from local offline database.
        Returns JSON with matching schemes.
        """
        global _offline_db
        if _offline_db is None:
            _offline_db = OfflineDatabase()
        schemes = _offline_db.search_schemes(scheme_name, category, language)
        return json.dumps([asdict(s) for s in schemes], ensure_ascii=False, indent=2)

    @mcp.tool()
    async def get_scheme_details(scheme_id: str, language: str = "hi") -> str:
        """Returns full details for a specific scheme."""
        global _offline_db
        if _offline_db is None:
            _offline_db = OfflineDatabase()
        scheme = _offline_db.get_scheme(scheme_id, language)
        return json.dumps(asdict(scheme) if scheme else {}, ensure_ascii=False)

    @mcp.tool()
    async def queue_offline_request(citizen_phone: str, service: str, parameters: dict) -> str:
        """
        Securely queues a transactional request for later execution when internet restores.
        Returns request ID.
        """
        global _offline_db
        if _offline_db is None:
            _offline_db = OfflineDatabase()
        req_id = _offline_db.queue_request(citizen_phone, service, parameters)
        return json.dumps({"request_id": req_id, "status": "QUEUED"})

    @mcp.tool()
    async def process_queued_requests() -> str:
        """
        Processes all pending queued requests (called when internet restores).
        Attempts to execute each via portal_tool and sends result via WhatsApp.
        """
        global _offline_db
        if _offline_db is None:
            _offline_db = OfflineDatabase()

        pending = _offline_db.get_pending_requests()
        results = []

        for req in pending:
            try:
                from friday_core.tools.portal_tool import open_government_portal
                from friday_core.tools.printer_tool import print_and_send_document

                portal_result = json.loads(await open_government_portal(req.service, req.parameters, headless=True))
                if portal_result.get("status") == "SUCCESS":
                    await print_and_send_document(portal_result.get("document_path", ""), req.citizen_phone)
                    _offline_db.update_request_status(req.id, "COMPLETED")
                    results.append({"id": req.id, "status": "SUCCESS"})
                else:
                    _offline_db.update_request_status(req.id, "FAILED", portal_result.get("error", "Unknown"))
                    results.append({"id": req.id, "status": "FAILED", "error": portal_result.get("error")})
            except Exception as e:
                _offline_db.update_request_status(req.id, "FAILED", str(e))
                results.append({"id": req.id, "status": "FAILED", "error": str(e)})

        return json.dumps({"processed": len(results), "results": results}, ensure_ascii=False)

    @mcp.tool()
    async def check_internet_connectivity() -> str:
        """Checks if internet is available."""
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://www.google.com", timeout=3) as resp:
                    return json.dumps({"online": resp.status == 200})
        except Exception:
            return json.dumps({"online": False})