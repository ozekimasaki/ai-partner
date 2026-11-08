import { useEffect, useState } from 'react';
import {
  formatElapsed,
  imageUrl,
  images,
  portraitUrl,
  posterUrl,
  videoUrl,
  videos,
  type ImageItem,
  type PartnerInfo,
  type VideoItem,
  type VideoOptions,
  type VideoStatus,
} from '../api';
import { useNow } from '../useNow';

const POLL_MS = 4000;
const MOTIONS = [
  '慌てて振り返り、襟元の鈴がチリンと鳴る',
  'こちらに気づいて、にっこり笑って小さく手を振る',
  '鉢植えを胸に抱えて、ゆっくりおじぎをする',
];
const STATUS_LABEL: Record<VideoStatus, string> = {
  pending: '順番待ち',
  running: '生成中',
  succeeded: '完成',
  failed: '失敗',
};

const isActive = (v: VideoItem) => v.status === 'pending' || v.status === 'running';

export function VideoTab({ info }: { info: PartnerInfo }) {
  const [options, setOptions] = useState<VideoOptions | null>(null);
  const [sources, setSources] = useState<ImageItem[]>([]);
  const [items, setItems] = useState<VideoItem[]>([]);
  const [source, setSource] = useState(info.image ? 'portrait' : '');
  const [prompt, setPrompt] = useState(MOTIONS[0]);
  const [duration, setDuration] = useState(5);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const anyActive = items.some(isActive);
  const now = useNow(anyActive);

  useEffect(() => {
    videos
      .options()
      .then(setOptions)
      .catch((e: Error) => setError(e.message));
    videos
      .list()
      .then(setItems)
      .catch((e: Error) => setError(e.message));
    images
      .list()
      .then((list) => {
        setSources(list);
        setSource((s) => s || list[0]?.id || '');
      })
      .catch(() => setSources([]));
  }, []);

  useEffect(() => {
    if (!anyActive) return;
    const id = setInterval(async () => {
      const active = items.filter(isActive);
      const updated = await Promise.all(active.map((v) => videos.get(v.id).catch(() => v)));
      setItems((prev) => prev.map((v) => updated.find((u) => u.id === v.id) ?? v));
    }, POLL_MS);
    return () => clearInterval(id);
  }, [anyActive, items]);

  async function create() {
    setError('');
    setSubmitting(true);
    try {
      const item = await videos.create({ prompt, source, duration });
      setItems((prev) => [item, ...prev]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  async function remove(item: VideoItem) {
    if (!confirm('この動画を消しますか？')) return;
    try {
      await videos.remove(item.id);
      setItems((prev) => prev.filter((v) => v.id !== item.id));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const hasSource = Boolean(source);

  return (
    <div className="studio">
      <section className="card form-card" aria-labelledby="video-form-title">
        <div className="card-head">
          <h2 id="video-form-title">立ち絵を動かす</h2>
          <span className="tag">{info.mock ? 'モック' : options?.model}</span>
        </div>

        <div className="field">
          <span className="label">最初のフレームにする画像</span>
          {!info.image && sources.length === 0 ? (
            <p className="empty-state">
              まだ画像がありません。「画像生成」タブで描いて、「立ち絵に設定」してください。
            </p>
          ) : (
            <div className="source-picker" role="radiogroup" aria-label="元の画像">
              {info.image && (
                <button
                  type="button"
                  role="radio"
                  aria-checked={source === 'portrait'}
                  className={`source ${source === 'portrait' ? 'is-selected' : ''}`}
                  onClick={() => setSource('portrait')}
                >
                  <img src={portraitUrl(info)} alt="" />
                  <span>いまの立ち絵</span>
                </button>
              )}
              {sources.slice(0, 8).map((img) => (
                <button
                  key={img.id}
                  type="button"
                  role="radio"
                  aria-checked={source === img.id}
                  className={`source ${source === img.id ? 'is-selected' : ''}`}
                  onClick={() => setSource(img.id)}
                >
                  <img src={imageUrl(img)} alt="" loading="lazy" />
                  <span>{img.ratio}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <label className="field">
          <span className="label">どう動くか（日本語で書けます）</span>
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={3} />
        </label>
        <div className="chips">
          {MOTIONS.map((m) => (
            <button
              key={m}
              type="button"
              className={`chip ${prompt === m ? 'is-selected' : ''}`}
              onClick={() => setPrompt(m)}
            >
              {m}
            </button>
          ))}
        </div>

        <div className="field">
          <span className="label">長さ</span>
          <div className="segmented" role="radiogroup" aria-label="長さ">
            {(options?.durations ?? [5]).map((d) => (
              <button
                key={d}
                type="button"
                role="radio"
                aria-checked={duration === d}
                className={duration === d ? 'is-selected' : ''}
                onClick={() => setDuration(d)}
              >
                {d}秒
              </button>
            ))}
          </div>
        </div>

        <div className="form-foot">
          <p className="muted small">
            動画は数分かかることがあります。作り始めたらこのタブを離れても大丈夫です。無料枠は合計30秒ぶんです。
          </p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={create}
            disabled={submitting || !prompt.trim() || !hasSource || !info.ready}
          >
            {submitting ? '依頼しています…' : '動画を作る'}
          </button>
        </div>
      </section>

      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}

      <section aria-labelledby="videos-title">
        <div className="section-head">
          <h2 id="videos-title">作った動画</h2>
          <span className="muted small">{items.length} 本</span>
        </div>
        {items.length === 0 ? (
          <p className="empty-state">まだありません。動きを書いて「動画を作る」を押してみましょう。</p>
        ) : (
          <div className="video-list">
            {items.map((v) => (
              <article key={v.id} className="card video-card">
                <div className="video-media">
                  {v.status === 'succeeded' && v.file ? (
                    <video src={videoUrl(v)} poster={posterUrl(v)} controls playsInline preload="metadata" />
                  ) : (
                    <img src={posterUrl(v)} alt="" className={isActive(v) ? 'is-waiting' : ''} />
                  )}
                  {isActive(v) && (
                    <div className="video-overlay">
                      <span className="spinner" aria-hidden />
                      <span>
                        {STATUS_LABEL[v.status]} ・ {formatElapsed(now - v.created_at)}
                      </span>
                    </div>
                  )}
                </div>
                <div className="video-body">
                  <div className="video-status">
                    <span className={`status status-${v.status}`}>{STATUS_LABEL[v.status]}</span>
                    <span className="muted xsmall">
                      {v.duration}秒 ・ {v.model}
                    </span>
                  </div>
                  <p className="video-prompt">{v.prompt}</p>
                  {isActive(v) && (
                    <div className="progress" aria-label="生成中">
                      <i />
                    </div>
                  )}
                  {v.status === 'failed' && (
                    <p className="error-text">{v.error || '動画を作れませんでした。'}</p>
                  )}
                  {v.status === 'succeeded' && !v.file && (
                    <p className="muted small">
                      モックなので動画ファイルはありません（実際のキーなら、ここで再生できます）。
                    </p>
                  )}
                  <div className="tile-actions">
                    {v.file && (
                      <a className="btn btn-primary btn-sm" href={videoUrl(v)} download>
                        保存
                      </a>
                    )}
                    {!isActive(v) && (
                      <button type="button" className="btn btn-ghost btn-sm" onClick={() => remove(v)}>
                        削除
                      </button>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
