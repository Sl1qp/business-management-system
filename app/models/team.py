from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    invite_code = Column(String, unique=True)

    members = relationship("UserTeam", back_populates="team", lazy="selectin")
    tasks = relationship("Task", back_populates="team")
    meetings = relationship("Meeting", back_populates="team")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class UserTeam(Base):
    __tablename__ = "user_teams"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    team_id = Column(Integer, ForeignKey("teams.id"))
    role = Column(String, default="member")

    user = relationship("User", back_populates="teams")
    team = relationship("Team", back_populates="members")

    created_at = Column(DateTime, server_default=func.now())
