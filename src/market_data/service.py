"""市场数据统一入口 - 聚合币安加密货币 + 美股数据"""

import structlog

from src.market_data.binance import BinanceClient
from src.market_data.usstock import USStockClient

logger = structlog.get_logger(__name__)


class MarketDataService:
    """市场数据统一服务 - 聚合加密货币和美股数据"""

    def __init__(self):
        self.binance = BinanceClient()
        self.usstock = USStockClient()

    async def get_full_market_summary(self) -> dict:
        """
        获取完整市场概览 (加密货币 + 美股)

        Returns:
            {
                "crypto": {...},
                "usstock": {...},
                "full_summary_text": "..."
            }
        """
        crypto_summary = await self.binance.get_market_summary()
        usstock_summary = await self.usstock.get_market_summary()

        full_text = "📊 === 市场概览 ===\n\n"
        full_text += "🪙 加密货币:\n"
        full_text += crypto_summary.get("summary_text", "暂无数据") + "\n\n"
        full_text += "📈 美股:\n"
        full_text += usstock_summary.get("summary_text", "暂无数据")

        return {
            "crypto": crypto_summary,
            "usstock": usstock_summary,
            "full_summary_text": full_text,
        }

    async def get_price(self, market: str, symbol: str) -> dict:
        """
        获取单个品种价格

        Args:
            market: "crypto" / "usstock"
            symbol: 交易对或股票代码

        Returns:
            价格信息
        """
        if market == "crypto":
            return await self.binance.get_ticker_24h(symbol)
        elif market == "usstock":
            return await self.usstock.get_ticker_info(symbol)
        else:
            return {"error": f"Unknown market: {market}"}

    async def check_alert(self, market: str, symbol: str, target_price: float, direction: str = "above") -> bool:
        """
        检查价格预警

        Args:
            market: "crypto" / "usstock"
            symbol: 交易对或股票代码
            target_price: 目标价格
            direction: "above" / "below"

        Returns:
            是否触及目标价位
        """
        if market == "crypto":
            return await self.binance.check_price_alert(symbol, target_price, direction)
        elif market == "usstock":
            info = await self.usstock.get_ticker_info(symbol)
            current_price = info.get("price", 0)
            if current_price == 0:
                return False
            if direction == "above" and current_price >= target_price:
                return True
            if direction == "below" and current_price <= target_price:
                return True
            return False
        else:
            return False

    async def close(self):
        """关闭所有客户端"""
        await self.binance.close()
