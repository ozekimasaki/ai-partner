import { useEffect, useState } from 'react';
import { fetchPartner, type PartnerInfo } from './api';
import { ChatTab } from './components/ChatTab';
import { ImageTab } from './components/ImageTab';
import { Portrait } from './components/Portrait';
import { SetupGuide } from './components/SetupGuide';
import { VideoTab } from './components/VideoTab';

const TABS = [
  { id: 'chat', label: 'チャット' },
  { id: 'image', label: '画像生成' },
  { id: 'video', label: '動画生成' },
] as const;
type TabId = (typeof TABS)[number]['id'];

function tabFromHash(): TabId {
  const id = location.hash.slice(1);
  return TABS.some((t) => t.id === id) ? (id as TabId) : 'chat';
}

function TabPanel({
  tab,
  info,
  onPartnerChange,
}: {
  tab: TabId;
  info: PartnerInfo;
  onPartnerChange: (i: PartnerInfo) => void;
}) {
  switch (tab) {
    case 'chat':
      return <ChatTab info={info} />;
    case 'image':
      return <ImageTab info={info} onPartnerChange={onPartnerChange} />;
    case 'video':
      return <VideoTab info={info} />;
    default: {
      const unreachable: never = tab;
      return unreachable;
    }
  }
}

export default function App() {
  const [info, setInfo] = useState<PartnerInfo | null>(null);
  const [loadError, setLoadError] = useState('');
  const [tab, setTab] = useState<TabId>(tabFromHash);

  useEffect(() => {
    fetchPartner()
      .then(setInfo)
      .catch((e: Error) => setLoadError(e.message));
    const onHash = () => setTab(tabFromHash());
    addEventListener('hashchange', onHash);
    return () => removeEventListener('hashchange', onHash);
  }, []);

  useEffect(() => {
    if (info) document.title = `${info.name} ・ AIパートナー`;
  }, [info]);

  function selectTab(id: TabId) {
    history.replaceState(null, '', `#${id}`);
    setTab(id);
  }

  return (
    <div className="app">
      <aside className="partner-card" aria-label="パートナー">
        <div className="partner-figure">
          <Portrait info={info} variant="hero" />
        </div>
        <div className="partner-meta">
          <p className="eyebrow">あなたのパートナー</p>
          <h1>{info?.name ?? '読み込み中…'}</h1>
          {info && (
            <div className="tags">
              <span className={`tag ${info.mock ? 'tag-mock' : ''}`}>
                {info.mock ? 'モック' : info.model}
              </span>
              {info.memory && <span className="tag">記憶</span>}
              {info.voice && <span className="tag">声</span>}
              {!info.ready && <span className="tag tag-warn">キー未設定</span>}
            </div>
          )}
        </div>
        <p className="partner-note">{info?.name ?? 'パートナー'}はAIが演じるキャラクターです。</p>
      </aside>

      <main className="main">
        <nav className="tabs" role="tablist" aria-label="機能">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={tab === t.id}
              className={tab === t.id ? 'is-selected' : ''}
              onClick={() => selectTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>

        {loadError && (
          <div className="alert alert-error" role="alert">
            サーバーに接続できません。start.py
            のウィンドウが開いたままか確かめて、ページを再読み込みしてください。（{loadError}）
          </div>
        )}
        {info && !info.ready && <SetupGuide info={info} />}
        {info && (
          <div className={`panel panel-${tab}`} role="tabpanel">
            <TabPanel tab={tab} info={info} onPartnerChange={setInfo} />
          </div>
        )}
      </main>
    </div>
  );
}
