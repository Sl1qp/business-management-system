from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    organizer_id = Column(Integer, ForeignKey("users.id"))
    team_id = Column(Integer, ForeignKey("teams.id"))
    organizer = relationship("User", back_populates="created_meetings", foreign_keys=[organizer_id])
    team = relationship("Team", back_populates="meetings")
    participants = relationship("MeetingParticipant", back_populates="meeting")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    user_id = Column(Integer, ForeignKey("users.id"))

    meeting = relationship("Meeting", back_populates="participants")
    user = relationship("User", back_populates="meetings")

    created_at = Column(DateTime, server_default=func.now())
