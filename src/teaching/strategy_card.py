"""策略卡片管理 - CRUD 操作"""

import structlog
from datetime import datetime

from src.knowledge.store.relational import RelationalStore, StrategyCardORM
from src.config.models import StrategyCard

logger = structlog.get_logger(__name__)


class StrategyCardManager:
    """策略卡片管理器"""

    def __init__(self, db: RelationalStore | None = None):
        self.db = db or RelationalStore()

    async def create(self, card: StrategyCard) -> str:
        """创建策略卡片"""
        from src.common.utils import generate_id

        card.id = card.id or generate_id("strat")
        card.created_at = datetime.now()
        card.updated_at = datetime.now()

        session = self.db.get_session()
        try:
            orm = StrategyCardORM(
                id=card.id,
                name=card.name,
                category=card.category,
                description=card.description,
                conditions=[c.model_dump() for c in card.conditions],
                actions=[a.model_dump() for a in card.actions],
                risk_management=card.risk_management.model_dump(),
                reasoning=card.reasoning,
                trade_off=card.trade_off,
                style_traits=card.style_traits.model_dump(),
                source_type=card.source_type,
                source_conversation_id=card.source_conversation_id,
                confidence=card.confidence,
                verified=card.verified,
                tags=card.tags,
                created_at=card.created_at,
                updated_at=card.updated_at,
            )
            session.add(orm)
            session.commit()
            logger.info("strategy_card_created", id=card.id, name=card.name)
            return card.id
        except Exception as e:
            session.rollback()
            logger.error("strategy_card_create_error", error=str(e))
            raise
        finally:
            session.close()

    async def get(self, card_id: str) -> StrategyCard | None:
        """获取策略卡片"""
        session = self.db.get_session()
        try:
            orm = session.query(StrategyCardORM).filter(StrategyCardORM.id == card_id).first()
            if not orm:
                return None
            return self._orm_to_model(orm)
        finally:
            session.close()

    async def list_all(self, category: str | None = None) -> list[StrategyCard]:
        """列出所有策略卡片"""
        session = self.db.get_session()
        try:
            query = session.query(StrategyCardORM)
            if category:
                query = query.filter(StrategyCardORM.category == category)
            orms = query.order_by(StrategyCardORM.updated_at.desc()).all()
            return [self._orm_to_model(orm) for orm in orms]
        finally:
            session.close()

    async def update(self, card_id: str, updates: dict) -> bool:
        """更新策略卡片"""
        session = self.db.get_session()
        try:
            orm = session.query(StrategyCardORM).filter(StrategyCardORM.id == card_id).first()
            if not orm:
                return False
            for key, value in updates.items():
                if hasattr(orm, key):
                    setattr(orm, key, value)
            orm.updated_at = datetime.now()
            session.commit()
            logger.info("strategy_card_updated", id=card_id)
            return True
        except Exception as e:
            session.rollback()
            logger.error("strategy_card_update_error", error=str(e))
            return False
        finally:
            session.close()

    async def delete(self, card_id: str) -> bool:
        """删除策略卡片"""
        session = self.db.get_session()
        try:
            orm = session.query(StrategyCardORM).filter(StrategyCardORM.id == card_id).first()
            if not orm:
                return False
            session.delete(orm)
            session.commit()
            logger.info("strategy_card_deleted", id=card_id)
            return True
        except Exception as e:
            session.rollback()
            logger.error("strategy_card_delete_error", error=str(e))
            return False
        finally:
            session.close()

    def _orm_to_model(self, orm: StrategyCardORM) -> StrategyCard:
        """ORM 转业务模型"""
        from src.config.models import StrategyCondition, StrategyAction, RiskManagement, StyleTraits

        return StrategyCard(
            id=orm.id,
            name=orm.name,
            category=orm.category or "",
            description=orm.description or "",
            conditions=[StrategyCondition(**c) for c in (orm.conditions or [])],
            actions=[StrategyAction(**a) for a in (orm.actions or [])],
            risk_management=RiskManagement(**(orm.risk_management or {})),
            reasoning=orm.reasoning or "",
            trade_off=orm.trade_off or "",
            style_traits=StyleTraits(**(orm.style_traits or {})),
            source_type=orm.source_type or "teaching",
            source_conversation_id=orm.source_conversation_id or "",
            confidence=orm.confidence or 0.0,
            verified=orm.verified or False,
            tags=orm.tags or [],
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
