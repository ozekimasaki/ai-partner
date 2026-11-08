import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { fetchPartner, remember, speak, streamChat, type Message, type PartnerInfo } from './api';

const HISTORY_KEY = 'ai-partner:history';

function loadHistory(): Message[] {
  try {
    const saved = JSON.parse(localStorage.getItem(HISTORY_KEY) ?? '[]');
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

function Avatar({ info, size }: { info: PartnerInfo | null; size: 'sm' | 'lg' }) {
  if (info?.image) {
    return <img className={`avatar avatar-${size}`} src="/api/partner/image" alt={info.name} />;
  }
  return (
    <div className={`avatar avatar-${size} avatar-initial`} aria-hidden>
      {info?.name.slice(0, 1) ?? '…'}
    </div>
  );
}

export default function App() {
  const [info, setInfo] = useState<PartnerInfo | null>(null);
  const [messages, setMessages] = useState<Message[]>(loadHistory);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [speaking, setSpeaking] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    fetchPartner()
      .then((p) => {
        setInfo(p);
        document.title = `${p.name} とおしゃべり`;
      })
      .catch((e: Error) => setError(`サーバーに接続できません: ${e.message}`));
  }, []);

  useEffect(() => {
    if (!busy) localStorage.setItem(HISTORY_KEY, JSON.stringify(messages));
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, busy]);

  async function send(text: string) {
    const history: Message[] = [...messages, { role: 'user', content: text }];
    setMessages([...history, { role: 'assistant', content: '' }]);
    setInput('');
    setError('');
    setNotice('');
    setBusy(true);
    let reply = '';
    let failed = '';
    try {
      for await (const ev of streamChat(history)) {
        if (ev.type === 'delta') {
          reply += ev.text;
          setMessages([...history, { role: 'assistant', content: reply }]);
        } else if (ev.type === 'error') {
          failed = ev.message;
        }
      }
    } catch (e) {
      failed = `送信できませんでした: ${(e as Error).message}`;
    }
    if (failed || !reply) {
      setMessages(messages);
      setInput(text);
      setError(failed || '返事が空でした。もう一度送ってみてください。');
    }
    setBusy(false);
    inputRef.current?.focus();
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (text && !busy && info?.ready) void send(text);
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) onSubmit(e);
  }

  function reset() {
    if (messages.length && !confirm('会話の履歴を消しますか？（記憶サーバーに保存した内容は消えません）'))
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

  const name = info?.name ?? '';

  return (
    <div className={`layout ${info?.image ? 'with-portrait' : ''}`}>
      {info?.image && (
        <aside className="portrait">
          <img src="/api/partner/image" alt={`${name}の立ち絵`} />
        </aside>
      )}
      <main className="chat">
        <header className="chat-header">
          <Avatar info={info} size="sm" />
          <div className="title">
            <h1>{name || '読み込み中…'}</h1>
            {info && (
              <p className="meta">
                {info.mock ? (
                  <span className="badge badge-mock">モック</span>
                ) : (
                  <span className="badge">{info.model}</span>
                )}
                {info.memory && <span className="badge">記憶あり</span>}
                {info.voice && <span className="badge">声あり</span>}
              </p>
            )}
          </div>
          <div className="actions">
            {info?.memory && (
              <button type="button" onClick={saveMemory} disabled={busy || messages.length === 0}>
                今日の会話を覚えてもらう
              </button>
            )}
            <button type="button" className="ghost" onClick={reset} disabled={busy}>
              リセット
            </button>
          </div>
        </header>

        {info && !info.ready && (
          <div className="banner banner-setup">
            APIキーが設定されていません。<code>.env</code> に <code>DASHSCOPE_API_KEY</code>{' '}
            を書いて、起動し直してください。
          </div>
        )}

        <section className="messages" aria-live="polite">
          {messages.length === 0 && info?.ready && (
            <div className="empty">
              <Avatar info={info} size="lg" />
              <p>
                {name}に話しかけてみましょう。
                <br />
                たとえば「ただいま」。
              </p>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`row row-${m.role}`}>
              {m.role === 'assistant' && <Avatar info={info} size="sm" />}
              <div className="bubble">
                {m.content || (
                  <span className="typing" aria-label="入力中">
                    <i />
                    <i />
                    <i />
                  </span>
                )}
                {m.role === 'assistant' &&
                  info?.voice &&
                  m.content &&
                  !(busy && i === messages.length - 1) && (
                    <button
                      type="button"
                      className="speak"
                      onClick={() => play(i)}
                      disabled={speaking !== null}
                      aria-label="読み上げる"
                      title="読み上げる"
                    >
                      {speaking === i ? '…' : '▶'}
                    </button>
                  )}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </section>

        {error && (
          <div className="banner banner-error" role="alert">
            {error}
          </div>
        )}
        {notice && <div className="banner banner-notice">{notice}</div>}

        <form className="composer" onSubmit={onSubmit}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={
              info?.ready
                ? `${name}へのメッセージ（Enterで送信、Shift+Enterで改行）`
                : 'APIキーの設定を待っています'
            }
            rows={2}
            disabled={!info?.ready}
            autoFocus
          />
          <button type="submit" disabled={busy || !input.trim() || !info?.ready}>
            送信
          </button>
        </form>
        <p className="footnote">{name || 'パートナー'}はAIが演じるキャラクターです。</p>
      </main>
    </div>
  );
}
