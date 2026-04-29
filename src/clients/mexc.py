"""
mexc_client.py — MEXC Futures REST API klient
Endpoint: https://contract.mexc.com
Auth: ApiKey + HMAC-SHA256 signatur
"""

import hmac, hashlib, time, json, logging
import requests

log = logging.getLogger("mexc_client")

BASE = "https://contract.mexc.com"

_session = requests.Session()
_session.headers.update({
    "Content-Type": "application/json",
    "User-Agent":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept":       "application/json",
    "Origin":       "https://futures.mexc.com",
    "Referer":      "https://futures.mexc.com/",
})

TIMEOUT = (5, 10)


class MexcClient:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key    = api_key
        self.api_secret = api_secret
        self._contract_cache: dict | None = None
        self._contract_cache_ts: float    = 0
        self._contract_cache_ttl: float   = 300  # 5 min

    # ── Signatur ──────────────────────────────────────────────────────────────
    def _sign(self, req_time: str, params: str) -> str:
        msg = self.api_key + req_time + params
        return hmac.new(
            self.api_secret.encode("utf-8"),
            msg.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _headers(self, params: str = "") -> dict:
        ts = str(int(time.time() * 1000))
        return {
            "ApiKey":       self.api_key,
            "Request-Time": ts,
            "Signature":    self._sign(ts, params),
        }

    # ── HTTP helpers ──────────────────────────────────────────────────────────
    def _get(self, path: str, params: dict = None, silent_404: bool = False) -> dict:
        qs = ""
        if params:
            qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        url = f"{BASE}{path}" + (f"?{qs}" if qs else "")
        try:
            resp = _session.get(url, headers=self._headers(qs), timeout=TIMEOUT)
            if not (silent_404 and resp.status_code == 404) and resp.status_code >= 400:
                log.error(f"GET {path} HTTP {resp.status_code}: {resp.text[:500]}")
                return {"success": False, "message": resp.text[:500]}
            return resp.json()
        except requests.exceptions.Timeout as e:
            log.error(f"GET {path} TIMEOUT: {e}")
            return {"success": False, "message": f"timeout: {e}"}
        except requests.exceptions.ConnectionError as e:
            log.error(f"GET {path} CONNECTION ERROR: {e}")
            return {"success": False, "message": f"connection error: {e}"}
        except Exception as e:
            log.error(f"GET {path} error: {e}")
            return {"success": False, "message": str(e)}

    def _post(self, path: str, body=None) -> dict:
        payload = json.dumps(body or {})
        try:
            resp = _session.post(
                f"{BASE}{path}",
                data=payload.encode(),
                headers=self._headers(payload),
                timeout=TIMEOUT,
            )
            if resp.status_code >= 400:
                log.error(f"POST {path} HTTP {resp.status_code}: {resp.text[:500]}")
                return {"success": False, "message": resp.text[:500]}
            return resp.json()
        except requests.exceptions.Timeout as e:
            log.error(f"POST {path} TIMEOUT: {e}")
            return {"success": False, "message": f"timeout: {e}"}
        except requests.exceptions.ConnectionError as e:
            log.error(f"POST {path} CONNECTION ERROR: {e}")
            return {"success": False, "message": f"connection error: {e}"}
        except Exception as e:
            log.error(f"POST {path} error: {e}")
            return {"success": False, "message": str(e)}

    def _delete(self, path: str, params: dict = None) -> dict:
        qs = ""
        if params:
            qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        url = f"{BASE}{path}" + (f"?{qs}" if qs else "")
        try:
            resp = _session.delete(url, headers=self._headers(qs), timeout=TIMEOUT)
            if resp.status_code >= 400:
                log.error(f"DELETE {path} HTTP {resp.status_code}: {resp.text[:500]}")
                return {"success": False, "message": resp.text[:500]}
            return resp.json()
        except requests.exceptions.Timeout as e:
            log.error(f"DELETE {path} TIMEOUT: {e}")
            return {"success": False, "message": f"timeout: {e}"}
        except requests.exceptions.ConnectionError as e:
            log.error(f"DELETE {path} CONNECTION ERROR: {e}")
            return {"success": False, "message": f"connection error: {e}"}
        except Exception as e:
            log.error(f"DELETE {path} error: {e}")
            return {"success": False, "message": str(e)}

    # ── Public endpoints ──────────────────────────────────────────────────────
    def get_klines(self, symbol: str, interval: str = "Min1", limit: int = 200) -> list:
        now   = int(time.time())
        start = now - limit * 60
        res   = self._get(f"/api/v1/contract/kline/{symbol}", {
            "interval": interval, "start": start, "end": now,
        })
        if not res.get("success") or not res.get("data"):
            return []
        d = res["data"]
        times  = d.get("time",  [])
        opens  = d.get("open",  [])
        highs  = d.get("high",  [])
        lows   = d.get("low",   [])
        closes = d.get("close", [])
        vols   = d.get("vol",   [])
        return [
            {"ts":    times[i],
             "open":  float(opens[i]),
             "high":  float(highs[i]),
             "low":   float(lows[i]),
             "close": float(closes[i]),
             "vol":   float(vols[i])}
            for i in range(len(times))
        ]

    def get_ticker(self, symbol: str) -> dict | None:
        res = self._get("/api/v1/contract/ticker", {"symbol": symbol})
        if res.get("success") and res.get("data"):
            d = res["data"]
            if isinstance(d, list):
                d = next((x for x in d if x.get("symbol") == symbol), None)
            return d
        return None

    def get_contract_info(self, symbol: str) -> dict | None:
        now = time.monotonic()
        if self._contract_cache is None or (now - self._contract_cache_ts) > self._contract_cache_ttl:
            res = self._get("/api/v1/contract/detail")
            if res.get("success") and res.get("data"):
                self._contract_cache    = {d["symbol"]: d for d in res["data"]}
                self._contract_cache_ts = now
            else:
                return None
        return self._contract_cache.get(symbol)

    # ── Account ───────────────────────────────────────────────────────────────
    def get_account(self) -> dict:
        return self._get("/api/v1/private/account/assets")

    def get_balance(self) -> float:
        res = self.get_account()
        if res.get("success") and res.get("data"):
            for asset in res["data"]:
                if asset.get("currency") == "USDT":
                    return float(asset.get("availableBalance", 0))
        return 0.0

    def get_positions(self, symbol: str = None) -> list:
        res = self._get("/api/v1/private/position/open_positions",
                        {"symbol": symbol} if symbol else {})
        if res.get("success"):
            return res.get("data", [])
        return []

    # ── Hävstång ──────────────────────────────────────────────────────────────
    def set_leverage(self, symbol: str, leverage: int) -> bool:
        res = self._post("/api/v1/private/position/change_leverage", {
            "symbol":   symbol,
            "leverage": leverage,
            "openType": 1,
        })
        return res.get("success", False)

    # ── Limit orders ──────────────────────────────────────────────────────────
    def place_limit_order(self, symbol: str, side: int, vol: float,
                          price: float, leverage: int = 5) -> dict:
        """
        Place a limit order.
        side: 1=open_long, 2=close_long, 3=open_short, 4=close_short
        """
        return self._post("/api/v1/private/order/submit", {
            "symbol":   symbol,
            "price":    price,
            "vol":      vol,
            "leverage": leverage,
            "side":     side,
            "type":     1,       # limit
            "openType": 1,       # isolated
        })

    def cancel_order(self, symbol: str, order_id: str) -> bool:
        res = self._delete("/api/v1/private/order/cancel",
                           {"symbol": symbol, "orderId": order_id})
        return res.get("success", False)

    def get_order(self, order_id: str) -> dict | None:
        res = self._get("/api/v1/private/order/get", {"orderId": order_id}, silent_404=True)
        if res.get("success") and res.get("data"):
            return res["data"]
        return None

    def get_open_orders(self, symbol: str = None) -> list:
        params = {"symbol": symbol} if symbol else {}
        res = self._get("/api/v1/private/order/list/open_orders/", params)
        if res.get("success"):
            data = res.get("data", {})
            if isinstance(data, list):
                return data
            return data.get("resultList", [])
        return []

    def close_position_market(self, symbol: str, side: int, vol: float) -> dict:
        """Stäng position med market order. side: 2=close_long, 4=close_short"""
        return self._post("/api/v1/private/order/submit", {
            "symbol":   symbol,
            "vol":      vol,
            "side":     side,
            "type":     5,       # market
            "openType": 1,
        })

    # ── Plan/Trigger orders (stop-market) ─────────────────────────────────────
    def place_stop_order(self, symbol: str, side: int, vol: float,
                         trigger_price: float, trigger_type: int) -> dict:
        """
        Place a stop-market trigger order.
        side:         2=close_long, 4=close_short
        trigger_type: 1 (>= for SHORT SL), 2 (<= for LONG SL)
        """
        return self._post("/api/v1/private/planorder/place", {
            "symbol":       symbol,
            "side":         side,
            "vol":          vol,
            "openType":     1,
            "type":         5,                   # market execution
            "triggerPrice": str(trigger_price),
            "triggerType":  trigger_type,        # 1=>=, 2=<=
            "executeCycle": 1,                   # GTC
            "trend":        trigger_type,        # mirrors triggerType
        })

    def cancel_plan_order(self, symbol: str, order_id: str) -> bool:
        """Cancel a plan/trigger order."""
        res = self._delete("/api/v1/private/planorder/cancel",
                           {"symbol": symbol, "orderId": order_id})
        return res.get("success", False)
