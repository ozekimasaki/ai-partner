import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { remember, speak, streamChat, type Message, type PartnerInfo } from '../api';
import { Portrait } from './Portrait';

const HISTORY_KEY = 'ai-partner:history';
const STARTERS = ['ただいま', '今日ちょっと疲れちゃった', 'おすすめのハーブティーある？'];

function loadHistory(): Message[] {
  try {
    const saved = JSON.parse(localStorage.getItem(HISTORY_KEY) ?? '[]');
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

export function ChatTab({ info }: { info: PartnerInfo }) {
  const [messages, setMessages] = useState<Message[]>(loadHistory);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [failedText, setFailedText] = useState('');
  const [notice, setNotice] = useState('');
  const [speaking, setSpeaking] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const name = info.name;

  useEffect(() => {
    if (!busy) localStorage.setItem(HISTORY_KEY, JSON.stringify(messages));
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, busy]);

  async function send(text: string) {
    const before = messages;
    const history: Message[] = [...before, { role: 'user', content: text }];
    setMessages([...history, { role: 'assistant', content: '' }]);
    setInput('');
    setError('');
    setFailedText('');
    setNotice('');
    setBusy(true);
    const controller = new AbortController();
    abortRef.current = controller;
    let reply = '';
    let failed = '';
    try {
      for await (const ev of streamChat(history, controller.signal)) {
        if (ev.type === 'delta') {
          reply += ev.text;
          setMessages([...history, { role: 'assistant', content: reply }]);
        } else if (ev.type === 'error') {
          failed = ev.message;
        }
      }
    } catch (e) {
      if ((e as Error).name !== 'AbortError') failed = `返事を受け取れませんでした: ${(e as Error).message}`;
    }
    abortRef.current = null;
    if (reply && controller.signal.aborted) {
      setMessages([...history, { role: 'assistant', content: `${reply}…` }]);
    } else if (failed || !reply) {
      setMessages(before);
      if (!controller.signal.aborted) {
        setError(failed || '返事が空でした。もう一度送ってみてください。');
        setFailedText(text);
      } else {
        setInput(text);
      }
    }
    setBusy(false);
    inputRef.current?.focus();
  }

  function submit(text: string) {
    const t = text.trim();
    if (t && !busy && info.ready) void send(t);
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    submit(input);
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit(input);
    }
  }

  function reset() {
    if (messages.length && !confirm('この画面の会話を消しますか？（記憶サーバーに渡した内容は消えません）'))
      return;
    setMessages([]);
    setError('');
    setNotice('');
  }

  async function saveMemory() {
    setError('');
    try {
      await remember(messages);
      setNotice('今日の会話を記憶に渡しました。書き出しには少し時間がかかります。');
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function play(index: number) {
    setSpeaking(index);
    setError('');
    try {
      const url = URL.createObjectURL(await speak(messages[index].content));
      const audio = new Audio(url);
      audio.onended = () => URL.revokeObjectURL(url);
      await audio.play();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSpeaking(null);
    }
  }

  const streamingIndex = busy ? messages.length - 1 : -1;

  return (
    <div className="chat">
      <div className="chat-toolbar">
        <span className="muted small">
          {messages.length ? `${Math.ceil(messages.length / 2)} 往復` : '新しい会話'}
        </span>
        <div className="toolbar-actions">
          {info.memory && (
            <button
              type="button"
              className="btn btn-quiet btn-sm"
              onClick={saveMemory}
              disabled={busy || !messages.length}
            >
              今日の会話を覚えてもらう
            </button>
          )}
          <button
            type="button"
            className="btn btn-quiet btn-sm"
            onClick={reset}
            disabled={busy || !messages.length}
          >
            会話を消す
          </button>
        </div>
      </div>

      <div className="messages" ref={listRef} aria-live="polite">
        {messages.length === 0 && (
          <div className="welcome">
            <Portrait info={info} variant="avatar" />
            <p className="welcome-title">{name}に話しかけてみましょう</p>
            <div className="chips">
              {STARTERS.map((s) => (
                <button
                  key={s}
                  type="button"
                  className="chip"
                  onClick={() => submit(s)}
                  disabled={!info.ready}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg msg-${m.role}`}>
            {m.role === 'assistant' && <Portrait info={info} variant="avatar" />}
            <div className="msg-body">
              {m.role === 'assistant' && <span className="msg-name">{name}</span>}
              <div className={`bubble ${i === streamingIndex ? 'is-streaming' : ''}`}>
                {m.content ? (
                  m.content
                ) : (
                  <span className="typing" aria-label={`${name}が入力中`}>
                    <i />
                    <i />
                    <i />
                  </span>
                )}
              </div>
              {m.role === 'assistant' && info.voice && m.content && i !== streamingIndex && (
                <button
                  type="button"
                  className="btn btn-quiet btn-xs"
                  onClick={() => play(i)}
                  disabled={speaking !== null}
                >
                  {speaking === i ? '読み上げ準備中…' : '▶ 声で聞く'}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          <span>{error}</span>
          {failedText && (
            <button type="button" className="btn btn-quiet btn-sm" onClick={() => submit(failedText)}>
              もう一度送る
            </button>
          )}
        </div>
      )}
      {notice && <div className="alert alert-info">{notice}</div>}

      <form className="composer" onSubmit={onSubmit}>
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={info.ready ? `${name}へのメッセージ` : 'APIキーを設定すると話せます'}
          rows={1}
          disabled={!info.ready}
          aria-label="メッセージ"
        />
        {busy ? (
          <button type="button" className="btn btn-quiet" onClick={() => abortRef.current?.abort()}>
            止める
          </button>
        ) : (
          <button type="submit" className="btn btn-primary" disabled={!input.trim() || !info.ready}>
            送信
          </button>
        )}
      </form>
      <p className="composer-hint">
        {busy ? `${name}が返事を書いています…` : 'Enter で送信 ・ Shift + Enter で改行'}
      </p>
    </div>
  );
}
