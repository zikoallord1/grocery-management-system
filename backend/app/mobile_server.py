import json
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from sqlalchemy import select

from backend.app.core.database import get_session
from backend.app.core.models import Product
from backend.app.modules.reports.service import ReportService


class _MobileHandler(BaseHTTPRequestHandler):
    server_version = "GroceryMobile/1.0"

    def log_message(self, format, *args):
        return

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/mobile/health":
                self._send_json({"ok": True, "service": "grocery-management-system", "date": date.today().isoformat()})
                return
            if parsed.path == "/api/mobile/summary":
                self._summary()
                return
            if parsed.path == "/api/mobile/products":
                self._products(parse_qs(parsed.query))
                return
            self._send_json({"ok": False, "error": "not_found"}, 404)
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, 500)

    def _summary(self):
        session = get_session()
        try:
            today = date.today().isoformat()
            summary = ReportService(session).dashboard_summary(date_from=today, date_to=today)
            report = ReportService(session)
            self._send_json({
                "ok": True,
                "date": today,
                "sales": float(summary.sales_total or 0),
                "purchases": float(summary.purchases_total or 0),
                "expenses": float(summary.expenses_total or 0),
                "profit": float((summary.gross_profit or 0) - (summary.expenses_total or 0)),
                "receivables": float(summary.customer_receivables or 0),
                "payables": float(summary.supplier_payables or 0),
                "cash": float(summary.cash_balance or 0),
                "low_stock": int(report.low_stock_count() or 0),
            })
        finally:
            session.close()

    def _products(self, query):
        try:
            limit = min(max(int(query.get("limit", [100])[0]), 1), 500)
        except (TypeError, ValueError):
            limit = 100
        session = get_session()
        try:
            rows = session.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.name).limit(limit)).all()
            self._send_json({
                "ok": True,
                "count": len(rows),
                "items": [
                    {
                        "id": item.id,
                        "sku": item.sku,
                        "name": item.name,
                        "purchase_price": float(item.purchase_price or 0),
                        "sale_price": float(item.sale_price or 0),
                        "minimum_stock": float(item.minimum_stock or 0),
                    }
                    for item in rows
                ],
            })
        finally:
            session.close()


_server = None
_thread = None


def start_mobile_server(host="0.0.0.0", port=8765):
    global _server, _thread
    if _server is not None:
        return _server
    _server = ThreadingHTTPServer((host, port), _MobileHandler)
    _thread = threading.Thread(target=_server.serve_forever, name="mobile-sync-server", daemon=True)
    _thread.start()
    return _server


def stop_mobile_server():
    global _server, _thread
    if _server is not None:
        _server.shutdown()
        _server.server_close()
    _server = None
    _thread = None
