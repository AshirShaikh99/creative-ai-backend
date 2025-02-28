from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.sql import func
from app.db.database import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="pending")
    collection_name = Column(String, nullable=False, unique=True)
    document_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Create unique constraint on uuid and title combination
    __table_args__ = (
        UniqueConstraint('uuid', 'title', name='uix_uuid_title'),
        Index('idx_uuid_title', 'uuid', 'title'),
    )
