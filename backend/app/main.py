from collections import defaultdict, deque
from pathlib import Path
import shutil

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .auth import create_token, hash_password, require_role, verify_password
from .config import settings
from .database import Base, SessionLocal, engine, get_db
from .models import PlaybackState, QueueItem, Track, User
from .realtime import manager
from .schemas import LoginRequest, PlaybackStateOut, PlaybackUpdateRequest, QueueItemOut, QueueMoveRequest, TokenResponse, TrackOut

app = FastAPI(title=settings.app_name)
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)
app.mount('/media', StaticFiles(directory=settings.uploads_dir), name='media')

rate_limiter: dict[str, deque] = defaultdict(deque)


def build_state(db: Session):
    queue = db.query(QueueItem).order_by(QueueItem.position.asc()).all()
    state = db.query(PlaybackState).first()
    if not state:
        state = PlaybackState(id=1)
        db.add(state)
        db.commit()
        db.refresh(state)
    return {
        'queue': [QueueItemOut.model_validate(q).model_dump() for q in queue],
        'playback': PlaybackStateOut(
            is_playing=state.is_playing,
            current_track_id=state.current_track_id,
            position_seconds=state.position_seconds,
            volume=state.volume,
        ).model_dump(),
    }


@app.on_event('startup')
def startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == settings.admin_username).first():
            db.add(User(username=settings.admin_username, password_hash=hash_password(settings.admin_password), role='admin'))
        if not db.query(PlaybackState).first():
            db.add(PlaybackState(id=1))
        db.commit()
    finally:
        db.close()


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.post('/auth/login', response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    role = 'guest'
    user = db.query(User).filter(User.username == payload.username).first()
    if user and verify_password(payload.password, user.password_hash):
        role = user.role
    elif payload.username == 'host' and payload.password == settings.host_password:
        role = 'host'
    elif payload.password == settings.shared_user_password:
        role = 'user'
    else:
        raise HTTPException(status_code=401, detail='Invalid credentials')

    token = create_token({'sub': payload.username, 'role': role})
    return TokenResponse(access_token=token, role=role, username=payload.username)


@app.get('/tracks', response_model=list[TrackOut])
def list_tracks(q: str = '', db: Session = Depends(get_db)):
    qry = db.query(Track)
    if q:
        like = f'%{q.lower()}%'
        qry = qry.filter((Track.title.ilike(like)) | (Track.artist.ilike(like)))
    return qry.order_by(Track.uploaded_at.desc()).all()


@app.post('/tracks/upload', response_model=TrackOut)
def upload_track(
    title: str,
    artist: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_role('admin')),
):
    if file.content_type not in {'audio/mpeg', 'audio/wav', 'audio/x-wav'}:
        raise HTTPException(status_code=400, detail='Only mp3/wav supported')
    safe_name = f"{title.strip().replace(' ', '_')}_{file.filename}"
    target = Path(settings.uploads_dir) / safe_name
    with target.open('wb') as output:
        shutil.copyfileobj(file.file, output)
    track = Track(title=title.strip(), artist=artist.strip() or 'Unknown', filename=safe_name, mime_type=file.content_type)
    db.add(track)
    db.commit()
    db.refresh(track)
    return track


@app.delete('/tracks/{track_id}')
def delete_track(track_id: int, db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail='Not found')
    file_path = Path(settings.uploads_dir) / track.filename
    if file_path.exists():
        file_path.unlink()
    db.query(QueueItem).filter(QueueItem.track_id == track_id).delete()
    db.delete(track)
    db.commit()
    return {'ok': True}


@app.get('/queue')
def get_queue(db: Session = Depends(get_db)):
    return build_state(db)


@app.post('/queue/{track_id}')
async def add_to_queue(track_id: int, db: Session = Depends(get_db), user=Depends(require_role('admin', 'host', 'user'))):
    now_bucket = rate_limiter[user['username']]
    now = __import__('time').time()
    window = settings.queue_rate_limit_seconds
    while now_bucket and now - now_bucket[0] > window:
        now_bucket.popleft()
    if len(now_bucket) >= settings.queue_rate_limit_count:
        raise HTTPException(status_code=429, detail='Rate limit exceeded')
    now_bucket.append(now)

    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail='Track not found')
    max_pos = db.query(QueueItem).count()
    item = QueueItem(track_id=track_id, position=max_pos, added_by=user['username'])
    db.add(item)
    db.commit()
    await manager.broadcast('state', build_state(db))
    return {'ok': True}


@app.delete('/queue/{item_id}')
async def remove_queue_item(item_id: int, db: Session = Depends(get_db), user=Depends(require_role('admin', 'host', 'user'))):
    item = db.query(QueueItem).filter(QueueItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail='Not found')
    db.delete(item)
    db.commit()
    for idx, q in enumerate(db.query(QueueItem).order_by(QueueItem.position.asc()).all()):
        q.position = idx
    db.commit()
    await manager.broadcast('state', build_state(db))
    return {'ok': True}


@app.post('/queue/reorder')
async def reorder_queue(payload: QueueMoveRequest, db: Session = Depends(get_db), user=Depends(require_role('admin', 'host', 'user'))):
    items = db.query(QueueItem).order_by(QueueItem.position.asc()).all()
    moving = next((x for x in items if x.id == payload.item_id), None)
    if not moving:
        raise HTTPException(status_code=404, detail='Item not found')
    items.remove(moving)
    new_pos = max(0, min(payload.to_position, len(items)))
    items.insert(new_pos, moving)
    for idx, item in enumerate(items):
        item.position = idx
    db.commit()
    await manager.broadcast('state', build_state(db))
    return {'ok': True}


@app.patch('/playback')
async def update_playback(payload: PlaybackUpdateRequest, db: Session = Depends(get_db), user=Depends(require_role('admin', 'host'))):
    state = db.query(PlaybackState).first()
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(state, field, value)
    db.commit()
    await manager.broadcast('state', build_state(db))
    return {'ok': True}


@app.websocket('/ws')
async def ws_endpoint(websocket: WebSocket):
    db = SessionLocal()
    await manager.connect(websocket)
    await websocket.send_json({'event': 'state', 'payload': build_state(db)})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        db.close()
