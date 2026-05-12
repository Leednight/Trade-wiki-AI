"""美股市场数据客户端 - 使用 yfinance 获取美股行情

无需 API Key，基于 Yahoo Finance 数据
"""

import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)

# 常用美股代码
DEFAULT_SYMBOLS = {
    "SPY": "标普500 ETF",
    "QQQ": "纳斯达克100 ETF",
    "AAPL": "苹果",
    "NVDA": "英伟达",
    "TSLA": "特斯拉",
    "MSFT": "微软",
    "GOOGL": "谷歌",
    "AMZN": "亚马逊",
    "META": "Meta",
}


class USStockClient:
    """美股数据客户端 (yfinance)"""

    def __init__(self):
        self._yf = None

    @property
    def yf(self):
        """懒加载 yfinance"""
        if self._yf is None:
            import yfinance as yf
            self._yf = yf
        return self._yf

    async def get_ticker_info(self, symbol: str = "SPY") -> dict:
        """
        获取股票基本信息和当前价格

        Args:
            symbol: 股票代码

        Returns:
            股票信息字典
        """
        try:
            ticker = self.yf.Ticker(symbol)
            info = ticker.info

            result = {
                "symbol": symbol,
                "name": info.get("shortName", symbol),
                "price": info.get("currentPrice") or info.get("regularMarketPrice", 0),
                "previous_close": info.get("previousClose", 0),
                "open": info.get("regularMarketOpen", 0),
                "day_high": info.get("dayHigh", 0),
                "day_low": info.get("dayLow", 0),
                "volume": info.get("volume", 0),
                "market_cap": info.get("marketCap", 0),
                "pe_ratio": info.get("trailingPE", 0),
                "52week_high": info.get("fiftyTwoWeekHigh", 0),
                "52week_low": info.get("fiftyTwoWeekLow", 0),
            }

            # 计算涨跌幅
            if result["previous_close"] and result["previous_close"] > 0:
                result["change_pct"] = (
                    (result["price"] - result["previous_close"]) / result["previous_close"] * 100
                )
            else:
                result["change_pct"] = 0

            logger.info("usstock_ticker_info", symbol=symbol, price=result["price"])
            return result

        except Exception as e:
            logger.error("usstock_ticker_info_error", symbol=symbol, error=str(e))
            return {"symbol": symbol, "error": str(e)}

    async def get_history(
        self,
        symbol: str = "SPY",
        period: str = "1mo",  # 1d/5d/1mo/3mo/6mo/1y/2y/5y/max
        interval: str = "1d",  # 1m/2m/5m/15m/30m/60m/90m/1h/1d/5d/1wk/1mo
    ) -> list[dict]:
        """
        获取历史K线数据

        Args:
            symbol: 股票代码
            period: 时间范围
            interval: K线间隔

        Returns:
            K线数据列表
        """
        try:
            ticker = self.yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)

            klines = []
            for index, row in hist.iterrows():
                klines.append({
                    "date": str(index),
                    "open": round(float(row["Open"]), 2),
                    "high": round(float(row["High"]), 2),
                    "low": round(float(row["Low"]), 2),
                    "close": round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                })

            logger.info("usstock_history", symbol=symbol, period=period, count=len(klines))
            return klines

        except Exception as e:
            logger.error("usstock_history_error", symbol=symbol, error=str(e))
            return []

    async def get_multi_ticker(self, symbols: dict | None = None) -> list[dict]:
        """
        批量获取多只股票行情

        Args:
            symbols: 股票代码字典 {code: name}

        Returns:
            行情数据列表
        """
        if symbols is None:
            symbols = DEFAULT_SYMBOLS

        results = []
        for symbol, name in symbols.items():
            info = await self.get_ticker_info(symbol)
            info["cn_name"] = name
            results.append(info)

        return results

    async def get_market_summary(self) -> dict:
        """
        获取美股市场概览 (主要指数+热门股)

        Returns:
            市场概览数据
        """
        # 主要指数
        indices = {"SPY": "标普500", "QQQ": "纳斯达克100", "DIA": "道琼斯"}
        tickers = await self.get_multi_ticker(indices)

        summary_lines = []
        for t in tickers:
            if "error" in t:
                continue
            change_icon = "🟢" if t.get("change_pct", 0) >= 0 else "🔴"
            summary_lines.append(
                f"{change_icon} {t.get('cn_name', t['symbol'])} ({t['symbol']}): "
                f"${t['price']:,.2f} ({t.get('change_pct', 0):+.2f}%)"
            )

        return {
            "tickers": tickers,
            "summary_text": "\n".join(summary_lines),
        }
