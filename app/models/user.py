from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable
from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base, SQLAlchemyBaseUserTable):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    role = Column(String, default="user")

    teams = relationship("UserTeam", back_populates="user")
    created_tasks = relationship("Task", back_populates="creator", foreign_keys="[Task.creator_id]")
    assigned_tasks = relationship("Task", back_populates="assignee", foreign_keys="[Task.assignee_id]")
    task_comments = relationship("TaskComment", back_populates="author")
    evaluations_received = relationship("Evaluation", back_populates="user", foreign_keys="[Evaluation.user_id]")
    evaluations_given = relationship("Evaluation", back_populates="evaluator", foreign_keys="[Evaluation.evaluator_id]")
    meetings = relationship("MeetingParticipant", back_populates="user")
    created_meetings = relationship("Meeting", back_populates="organizer", foreign_keys="[Meeting.organizer_id]")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
