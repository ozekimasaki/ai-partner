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
  memory: boolean;
  voice: boolean;
}

export type StreamEvent =
  | { type: 'delta'; text: string }
  | { type: 'done' }
  | { type: 'error'; message: string };

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === 'string') return body.detail;
  } catch {
    // fall through to the status line
  }
  return `サーバーがエラーを返しました（${res.status}）`;
}

export async function fetchPartner(): Promise<PartnerInfo> {
  const res = await fetch('/api/partner');
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json();
}

/** Split a newline-delimited JSON stream into events, keeping any partial line in the buffer. */
export function parseLines(buffer: string): { events: StreamEvent[]; rest: string } {
  const lines = buffer.split('\n');
  const rest = lines.pop() ?? '';
  const events = lines.filter((l) => l.trim()).map((l) => JSON.parse(l) as StreamEvent);
  return { events, rest };
}

export async function* streamChat(messages: Message[], signal?: AbortSignal): AsyncGenerator<StreamEvent> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages }),
    signal,
  });
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

export async function remember(messages: Message[]): Promise<void> {
  const res = await fetch('/api/memory', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages }),
  });
  if (!res.ok) throw new Error(await errorMessage(res));
}

export async function speak(text: string): Promise<Blob> {
  const res = await fetch('/api/speak', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.blob();
}
