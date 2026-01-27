"""
Financial Trading Agent with Human-in-the-Loop Approval

This agent proposes trades and requires human approval for trades
below a confidence threshold (80%).
"""

from dataclasses import dataclass
from typing import Any

from agenkit import Agent, Message


@dataclass
class Trade:
    """Represents a proposed financial trade."""

    symbol: str
    action: str  # "buy" or "sell"
    quantity: int
    price: float
    confidence: float
    market_cap: str | None = None
    volatility: str | None = None
    reason: str | None = None


class TradingAgent(Agent):
    """
    Mock trading agent that analyzes market conditions and proposes trades.

    The agent returns varying confidence levels based on trade risk:
    - Conservative trades: >80% confidence (auto-approved)
    - Moderate trades: 60-80% confidence (requires approval)
    - Aggressive trades: <60% confidence (requires approval)
    """

    @property
    def name(self) -> str:
        return "TradingAgent"

    @property
    def capabilities(self) -> list[str]:
        return ["trading", "market-analysis", "risk-assessment"]

    async def process(self, message: Message) -> Message:
        """
        Analyze trading request and return proposal with confidence score.

        Args:
            message: User request containing trading instructions

        Returns:
            Message with trade proposal and confidence score
        """
        content = str(message.content).lower()

        # Parse trading strategy from message
        if "conservative" in content or "safe" in content:
            trade = self._create_conservative_trade(content)
        elif "aggressive" in content or "risky" in content:
            trade = self._create_aggressive_trade(content)
        else:
            trade = self._create_moderate_trade(content)

        # Format response
        response_text = self._format_trade_proposal(trade)

        return Message(
            role="assistant",
            content=response_text,
            metadata={
                "confidence": trade.confidence,
                "trade": self._trade_to_dict(trade),
                "risk_level": self._assess_risk(trade.confidence),
            },
        )

    def _create_conservative_trade(self, content: str) -> Trade:
        """Create a low-risk, high-confidence trade."""
        return Trade(
            symbol="AAPL",
            action="buy",
            quantity=10,
            price=175.50,
            confidence=0.92,
            market_cap="Large Cap",
            volatility="Low",
            reason="Strong quarterly earnings, stable growth trajectory, low volatility",
        )

    def _create_moderate_trade(self, content: str) -> Trade:
        """Create a moderate-risk, medium-confidence trade."""
        return Trade(
            symbol="MSFT",
            action="sell",
            quantity=50,
            price=420.00,
            confidence=0.75,
            market_cap="Large Cap",
            volatility="Medium",
            reason="Taking profits after strong run-up, market showing signs of correction",
        )

    def _create_aggressive_trade(self, content: str) -> Trade:
        """Create a high-risk, low-confidence trade."""
        return Trade(
            symbol="TSLA",
            action="buy",
            quantity=100,
            price=850.00,
            confidence=0.45,
            market_cap="Large Cap",
            volatility="Very High",
            reason="Speculative position on upcoming product launch, high volatility risk",
        )

    def _format_trade_proposal(self, trade: Trade) -> str:
        """Format trade as human-readable proposal."""
        parts = [
            "📊 **Trade Proposal**\n",
            f"**Action**: {trade.action.upper()}",
            f"**Symbol**: {trade.symbol}",
            f"**Quantity**: {trade.quantity:,} shares",
            f"**Price**: ${trade.price:,.2f}",
            f"**Total Value**: ${trade.price * trade.quantity:,.2f}\n",
            f"**Confidence**: {trade.confidence:.1%}",
            f"**Market Cap**: {trade.market_cap or 'N/A'}",
            f"**Volatility**: {trade.volatility or 'N/A'}\n",
            f"**Analysis**: {trade.reason or 'No analysis provided'}",
        ]

        return "\n".join(parts)

    def _assess_risk(self, confidence: float) -> str:
        """Assess risk level based on confidence."""
        if confidence >= 0.8:
            return "low"
        elif confidence >= 0.6:
            return "medium"
        else:
            return "high"

    def _trade_to_dict(self, trade: Trade) -> dict[str, Any]:
        """Convert trade to dictionary for metadata."""
        return {
            "symbol": trade.symbol,
            "action": trade.action,
            "quantity": trade.quantity,
            "price": trade.price,
            "confidence": trade.confidence,
            "market_cap": trade.market_cap,
            "volatility": trade.volatility,
            "reason": trade.reason,
        }
