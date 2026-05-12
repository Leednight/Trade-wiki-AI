"""币安 API 客户端 - 获取 BTC/ETH 等加密货币行情数据

文档: https://binance-docs.github.io/apidocs/
公开行情接口无需 API Key
"""

import structlog
import httpx

from src.config import get_settings

logger = structlog.get_logger(__name__)

# 常用交易对
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]

# K线间隔
KLINE_INTERVALS = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
    "1w": "1w",
}


class BinanceClient:
    """币安 API 客户端"""

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.binance.base_url
        self.api_key = settings.binance.api_key
        self.api_secret = settings.binance.api_secret
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {}
            if self.api_key:
                headers["X-MBX-APIKEY"] = self.api_key
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=10.0,
            )
        return self._client

    async def get_ticker_price(self, symbol: str = "BTCUSDT") -> dict:
        """
        获取最新价格

        Args:
            symbol: 交易对，如 BTCUSDT

        Returns:
            {"symbol": "BTCUSDT", "price": "104500.00"}
        """
        try:
            response = await self.client.get(
                "/api/v3/ticker/price",
                params={"symbol": symbol},
            )
            response.raise_for_status()
            data = response.json()
            logger.info("binance_ticker_price", symbol=symbol, price=data.get("price"))
            return data
        except Exception as e:
            logger.error("binance_ticker_price_error", symbol=symbol, error=str(e))
            return {"symbol": symbol, "price": "0", "error": str(e)}

    async def get_ticker_24h(self, symbol: str = "BTCUSDT") -> dict:
        """
        获取24小时价格变动统计

        Args:
            symbol: 交易对

        Returns:
            包含24h价格变动、成交量等统计数据
        """
        try:
            response = await self.client.get(
                "/api/v3/ticker/24hr",
                params={"symbol": symbol},
            )
            response.raise_for_status()
            data = response.json()
            # 提取关键字段
            result = {
                "symbol": data["symbol"],
                "price": float(data["lastPrice"]),
                "price_change": float(data["priceChange"]),
                "price_change_pct": float(data["priceChangePercent"]),
                "high": float(data["highPrice"]),
                "low": float(data["lowPrice"]),
                "volume": float(data["volume"]),
                "quote_volume": float(data["quoteVolume"]),
            }
            logger.info("binance_ticker_24h", symbol=symbol, price=result["price"])
            return result
        except Exception as e:
            logger.error("binance_ticker_24h_error", symbol=symbol, error=str(e))
            return {"symbol": symbol, "error": str(e)}

    async def get_klines(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "1d",
        limit: int = 30,
    ) -> list[dict]:
        """
        获取K线数据

        Args:
            symbol: 交易对
            interval: K线间隔 (1m/5m/15m/1h/4h/1d/1w)
            limit: 返回数量 (最大1000)

        Returns:
            K线数据列表
        """
        try:
            response = await self.client.get(
                "/api/v3/klines",
                params={
                    "symbol": symbol,
                    "interval": KLINE_INTERVALS.get(interval, "1d"),
                    "limit": min(limit, 1000),
                },
            )
            response.raise_for_status()
            raw_data = response.json()

            # 解析K线数据
            klines = []
            for k in raw_data:
                klines.append({
                    "open_time": k[0],
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "close_time": k[6],
                    "quote_volume": float(k[7]),
                    "trades": k[8],
                })

            logger.info("binance_klines", symbol=symbol, interval=interval, count=len(klines))
            return klines
        except Exception as e:
            logger.error("binance_klines_error", symbol=symbol, error=str(e))
            return []

    async def get_multi_ticker(self, symbols: list[str] | None = None) -> list[dict]:
        """
        批量获取多个交易对的行情

        Args:
            symbols: 交易对列表，默认主流币种

        Returns:
            行情数据列表
        """
        if symbols is None:
            symbols = DEFAULT_SYMBOLS

        results = []
        for symbol in symbols:
            ticker = await self.get_ticker_24h(symbol)
            results.append(ticker)

        return results

    async def check_price_alert(
        self,
        symbol: str,
        target_price: float,
        direction: str = "above",  # above / below
    ) -> bool:
        """
        检查价格是否触及目标价位

        Args:
            symbol: 交易对
            target_price: 目标价格
            direction: above=向上突破, below=向下跌破

        Returns:
            是否触及
        """
        ticker = await self.get_ticker_price(symbol)
        current_price = float(ticker.get("price", 0))

        if current_price == 0:
            return False

        if direction == "above" and current_price >= target_price:
            logger.info("price_alert_triggered", symbol=symbol, current=current_price, target=target_price, direction=direction)
            return True
        elif direction == "below" and current_price <= target_price:
            logger.info("price_alert_triggered", symbol=symbol, current=current_price, target=target_price, direction=direction)
            return True

        return False

    async def get_market_summary(self) -> dict:
        """
        获取加密货币市场概览 (主流币种行情汇总)

        Returns:
            市场概览数据
        """
        tickers = await self.get_multi_ticker()

        summary_lines = []
        total_volume = 0.0

        for t in tickers:
            if "error" in t:
                continue
            change_icon = "🟢" if t.get("price_change_pct", 0) >= 0 else "🔴"
            summary_lines.append(
                f"{change_icon} {t['symbol']}: ${t['price']:,.2f} "
                f"({t.get('price_change_pct', 0):+.2f}%) "
                f"Vol: ${t.get('quote_volume', 0):,.0f}"
            )
            total_volume += t.get("quote_volume", 0)

        return {
            "tickers": tickers,
            "summary_text": "\n".join(summary_lines),
            "total_volume_usd": total_volume,
        }

    async def close(self):
        """关闭HTTP客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
