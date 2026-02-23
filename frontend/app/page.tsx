'use client';

import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';

type Track = { id: number; title: string; artist: string; filename: string };
type QueueItem = { id: number; position: number; added_by: string; track: Track };
type Playback = { is_playing: boolean; current_track_id: number | null; position_seconds: number; volume: number };

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export default function Home() {
  const [token, setToken] = useState('');
  const [username, setUsername] = useState('guest');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('guest');
  const [tracks, setTracks] = useState<Track[]>([]);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [playback, setPlayback] = useState<Playback>({ is_playing: false, current_track_id: null, position_seconds: 0, volume: 1 });
  const [search, setSearch] = useState('');
  const audioRef = useRef<HTMLAudioElement>(null);

  const headers = useMemo(() => (token ? { Authorization: `Bearer ${token}` } : {}), [token]);
  const currentTrack = tracks.find((t) => t.id === playback.current_track_id);

  const refreshTracks = async () => {
    const res = await fetch(`${API}/tracks?q=${encodeURIComponent(search)}`);
    setTracks(await res.json());
  };

  const refreshState = async () => {
    const res = await fetch(`${API}/queue`);
    const data = await res.json();
    setQueue(data.queue);
    setPlayback(data.playback);
  };

  useEffect(() => {
    refreshTracks();
    refreshState();
  }, [search]);

  useEffect(() => {
    const ws = new WebSocket(API.replace('http', 'ws') + '/ws');
    ws.onmessage = (msg) => {
      const data = JSON.parse(msg.data);
      if (data.event === 'state') {
        setQueue(data.payload.queue);
        setPlayback(data.payload.playback);
      }
    };
    return () => ws.close();
  }, []);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !currentTrack) return;
    audio.src = `${API}/media/${currentTrack.filename}`;
    audio.currentTime = playback.position_seconds ?? 0;
    audio.volume = playback.volume;
    if (playback.is_playing) audio.play().catch(() => undefined);
    else audio.pause();
  }, [currentTrack?.id, playback.is_playing]);

  const login = async (e: FormEvent) => {
    e.preventDefault();
    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) return alert('Login failed');
    const data = await res.json();
    setToken(data.access_token);
    setRole(data.role);
  };

  const patchPlayback = async (patch: Partial<Playback>) => {
    await fetch(`${API}/playback`, {
      method: 'PATCH',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    });
  };

  const addToQueue = async (trackId: number) => {
    await fetch(`${API}/queue/${trackId}`, { method: 'POST', headers });
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Jukebox Music Maker</h1>
      <p className="text-sm text-zinc-300">Private/self-hosted collaborative queue. Role: {role}</p>
      <form onSubmit={login} className="flex flex-wrap gap-2">
        <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="username" />
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password" />
        <button type="submit" className="bg-indigo-600">Login</button>
      </form>

      <div className="grid gap-6 md:grid-cols-2">
        <section className="space-y-3">
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-semibold">Library</h2>
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search" className="ml-auto" />
          </div>
          <ul className="space-y-2">
            {tracks.map((t) => (
              <li key={t.id} className="flex items-center justify-between rounded border border-zinc-800 p-2">
                <span>{t.title} — {t.artist}</span>
                <button onClick={() => addToQueue(t.id)} className="bg-emerald-700">Queue</button>
              </li>
            ))}
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">Shared Queue</h2>
          <ul className="space-y-2">
            {queue.map((item) => (
              <li key={item.id} className="rounded border border-zinc-800 p-2">#{item.position + 1} {item.track.title} ({item.added_by})</li>
            ))}
          </ul>
        </section>
      </div>

      <section className="space-y-2 rounded border border-zinc-800 p-4">
        <h2 className="text-xl font-semibold">Host Playback</h2>
        <audio ref={audioRef} controls className="w-full" onPause={() => patchPlayback({ is_playing: false })} onPlay={() => patchPlayback({ is_playing: true })} onSeeked={(e) => patchPlayback({ position_seconds: (e.target as HTMLAudioElement).currentTime })} />
        <div className="flex gap-2">
          <button onClick={() => patchPlayback({ is_playing: true })} className="bg-indigo-700">Play</button>
          <button onClick={() => patchPlayback({ is_playing: false })} className="bg-zinc-700">Pause</button>
          <button onClick={() => patchPlayback({ current_track_id: queue[0]?.track.id ?? null, position_seconds: 0 })} className="bg-amber-700">Load First</button>
        </div>
      </section>
    </div>
  );
}
