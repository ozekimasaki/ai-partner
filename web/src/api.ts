export type Role = 'user' | 'assistant';

export interface Message {
  role: Role;
  content: string;
}

export interface PartnerInfo {
  name: string;
  model: string;
  ready: boolean;
  mock: boolean;
  image: boolean;
  image_version: number;
  memory: boolean;
  voice: boolean;
  env_path: string;
}

export interface ImageItem {
  id: string;
  file: string;
  prompt: string;
  negative_prompt: string;
  ratio: string;
  model: string;
  note: string;
  created_at: number;
}

export interface ImageOptions {
  presets: { label: string; prompt: string }[];
  negative_prompt: string;
  ratios: { id: string; label: string; size: string }[];
  model: string;
  fallback_model: string;
}

export type VideoStatus = 'pending' | 'running' | 'succeeded' | 'failed';

export interface VideoItem {
  id: string;
  prompt: string;
  duration: number;
  model: string;
  status: VideoStatus;
  error: string;
  file: string;
  poster: string;
  created_at: number;
  finished_at: number | null;
}

export interface VideoOptions {
  durations: number[];
  model: string;
}

export type StreamEvent =
  | { type: 'delta'; text: string }
  | { type: 'done' }
  | { type: 'error'; message: string };

const NETWORK_ERROR = 'サーバーに届きませんでした。start.py のウィンドウが開いたままか確かめてください。';

export class ApiError extends Error {}

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === 'string') return body.detail;
  } catch {
    // fall through to the status line
  }
  return `サーバーがエラーを返しました（${res.status}）`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      ...init,
      headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
    });
  } catch {
    throw new ApiError(NETWORK_ERROR);
  }
  if (!res.ok) throw new ApiError(await errorMessage(res));
  return res.json();
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) });

export const fetchPartner = () => request<PartnerInfo>('/api/partner');

export const portraitUrl = (info: PartnerInfo) => `/api/partner/image?v=${info.image_version}`;
export const imageUrl = (item: ImageItem) => `/media/images/${item.file}`;
export const videoUrl = (item: VideoItem) => `/media/videos/${item.file}`;
export const posterUrl = (item: VideoItem) => `/media/videos/${item.poster}`;

export const images = {
  options: () => request<ImageOptions>('/api/images/options'),
  list: () => request<ImageItem[]>('/api/images'),
  create: (body: { prompt: string; negative_prompt: string; ratio: string }) =>
    post<ImageItem>('/api/images', body),
  remove: (id: string) => request<unknown>(`/api/images/${id}`, { method: 'DELETE' }),
  setPortrait: (id: string) => post<PartnerInfo>(`/api/images/${id}/portrait`),
};

export const videos = {
  options: () => request<VideoOptions>('/api/videos/options'),
  list: () => request<VideoItem[]>('/api/videos'),
  get: (id: string) => request<VideoItem>(`/api/videos/${id}`),
  create: (body: { prompt: string; source: string; duration: number }) =>
    post<VideoItem>('/api/videos', body),
  remove: (id: string) => request<unknown>(`/api/videos/${id}`, { method: 'DELETE' }),
};

/** Split a newline-delimited JSON stream into events, keeping any partial line in the buffer. */
export function parseLines(buffer: string): { events: StreamEvent[]; rest: string } {
  const lines = buffer.split('\n');
  const rest = lines.pop() ?? '';
  const events = lines.filter((l) => l.trim()).map((l) => JSON.parse(l) as StreamEvent);
  return { events, rest };
}

export async function* streamChat(messages: Message[], signal?: AbortSignal): AsyncGenerator<StreamEvent> {
  let res: Response;
  try {
    res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages }),
      signal,
    });
  } catch (e) {
    if ((e as Error).name === 'AbortError') throw e;
    yield { type: 'error', message: NETWORK_ERROR };
    return;
  }
  if (!res.ok || !res.body) {
    yield { type: 'error', message: await errorMessage(res) };
    return;
  }
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    const parsed = parseLines(buffer + value);
    buffer = parsed.rest;
    yield* parsed.events;
  }
  if (buffer.trim()) yield* parseLines(buffer + '\n').events;
}

export const remember = (messages: Message[]) => post<unknown>('/api/memory', { messages });

export async function speak(text: string): Promise<Blob> {
  let res: Response;
  try {
    res = await fetch('/api/speak', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
  } catch {
    throw new ApiError(NETWORK_ERROR);
  }
  if (!res.ok) throw new ApiError(await errorMessage(res));
  return res.blob();
}

export function formatElapsed(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}
