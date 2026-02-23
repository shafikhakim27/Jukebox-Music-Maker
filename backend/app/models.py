from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default='user')


class Track(Base):
    __tablename__ = 'tracks'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    artist = Column(String, default='Unknown')
    filename = Column(String, unique=True, nullable=False)
    mime_type = Column(String, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class QueueItem(Base):
    __tablename__ = 'queue_items'

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, ForeignKey('tracks.id'), nullable=False)
    added_by = Column(String, nullable=False)
    position = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    track = relationship('Track')


class PlaybackState(Base):
    __tablename__ = 'playback_state'

    id = Column(Integer, primary_key=True, default=1)
    is_playing = Column(Boolean, default=False, nullable=False)
    current_track_id = Column(Integer, ForeignKey('tracks.id'), nullable=True)
    position_seconds = Column(Float, default=0, nullable=False)
    volume = Column(Float, default=1, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
