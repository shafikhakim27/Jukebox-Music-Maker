from datetime import datetime
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    role: str
    username: str


class TrackOut(BaseModel):
    id: int
    title: str
    artist: str
    filename: str
    mime_type: str
    uploaded_at: datetime | None

    class Config:
        from_attributes = True


class QueueItemOut(BaseModel):
    id: int
    position: int
    added_by: str
    track: TrackOut

    class Config:
        from_attributes = True


class PlaybackStateOut(BaseModel):
    is_playing: bool
    current_track_id: int | None
    position_seconds: float
    volume: float


class QueueMoveRequest(BaseModel):
    item_id: int
    to_position: int


class PlaybackUpdateRequest(BaseModel):
    is_playing: bool | None = None
    current_track_id: int | None = None
    position_seconds: float | None = None
    volume: float | None = None
