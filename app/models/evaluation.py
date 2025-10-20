from sqlalchemy import Column, Integer, SmallInteger, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rating = Column(SmallInteger, nullable=False)
    comment = Column(Text)

    task_id = Column(Integer, ForeignKey("tasks.id"))
    user_id = Column(Integer, ForeignKey("users.id"))  # Кого оценивают
    evaluator_id = Column(Integer, ForeignKey("users.id"))  # Кто оценивает

    task = relationship("Task", back_populates="evaluation")
    user = relationship("User", back_populates="evaluations_received", foreign_keys=[user_id])
    evaluator = relationship("User", back_populates="evaluations_given", foreign_keys=[evaluator_id])

    created_at = Column(DateTime, server_default=func.now())
