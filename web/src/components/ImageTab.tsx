import { useEffect, useState } from 'react';
import { formatElapsed, imageUrl, images, type ImageItem, type ImageOptions, type PartnerInfo } from '../api';
import { useNow } from '../useNow';

interface Props {
  info: PartnerInfo;
  onPartnerChange: (info: PartnerInfo) => void;
}

function aspect(ratio: string): string {
  const [w, h] = ratio.split(':');
  return `${w} / ${h}`;
}

export function ImageTab({ info, onPartnerChange }: Props) {
  const [options, setOptions] = useState<ImageOptions | null>(null);
  const [items, setItems] = useState<ImageItem[]>([]);
  const [prompt, setPrompt] = useState('');
  const [negative, setNegative] = useState('');
  const [ratio, setRatio] = useState('4:7');
  const [preset, setPreset] = useState(0);
  const [busySince, setBusySince] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const now = useNow(busySince !== null);

  useEffect(() => {
    images
      .options()
      .then((o) => {
        setOptions(o);
        setNegative(o.negative_prompt);
        if (o.presets[0]) setPrompt(o.presets[0].prompt);
      })
      .catch((e: Error) => setError(e.message));
    images
      .list()
      .then(setItems)
      .catch((e: Error) => setError(e.message));
  }, []);

  function choosePreset(i: number) {
    if (!options) return;
    setPreset(i);
    setPrompt(options.presets[i].prompt);
  }

  async function generate() {
    setError('');
    setNotice('');
    setBusySince(Date.now() / 1000);
    try {
      const item = await images.create({ prompt, negative_prompt: negative, ratio });
      setItems((prev) => [item, ...prev]);
      if (item.note) setNotice(item.note);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusySince(null);
    }
  }

  async function setAsPortrait(item: ImageItem) {
    setError('');
    try {
      onPartnerChange(await images.setPortrait(item.id));
      setNotice(`立ち絵を変えました。チャット画面の${info.name}にも反映されています。`);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function remove(item: ImageItem) {
    if (!confirm('この画像を消しますか？')) return;
    try {
      await images.remove(item.id);
      setItems((prev) => prev.filter((i) => i.id !== item.id));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const busy = busySince !== null;

  return (
    <div className="studio">
      <section className="card form-card" aria-labelledby="image-form-title">
        <div className="card-head">
          <h2 id="image-form-title">立ち絵や差分を描く</h2>
          <span className="tag">{info.mock ? 'モック' : options?.model}</span>
        </div>

        {options && options.presets.length > 0 && (
          <div className="field">
            <span className="label">プリセット</span>
            <div className="chips">
              {options.presets.map((p, i) => (
                <button
                  key={p.label}
                  type="button"
                  className={`chip ${i === preset ? 'is-selected' : ''}`}
                  onClick={() => choosePreset(i)}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        )}

        <label className="field">
          <span className="label">プロンプト（日本語で書けます）</span>
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={7} />
        </label>

        <details className="field">
          <summary className="label">ネガティブプロンプト（描いてほしくないもの）</summary>
          <textarea value={negative} onChange={(e) => setNegative(e.target.value)} rows={2} />
        </details>

        <div className="field">
          <span className="label">縦横比</span>
          <div className="ratio-picker" role="radiogroup" aria-label="縦横比">
            {options?.ratios.map((r) => (
              <button
                key={r.id}
                type="button"
                role="radio"
                aria-checked={ratio === r.id}
                className={`ratio ${ratio === r.id ? 'is-selected' : ''}`}
                onClick={() => setRatio(r.id)}
                title={`${r.label}（${r.size.replace('*', '×')}）`}
              >
                <i style={{ aspectRatio: aspect(r.id) }} />
                <span>{r.id}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="form-foot">
          <p className="muted small">
            {options && !info.mock && `失敗したときは ${options.fallback_model} で描き直します。`}
            画像のURLは24時間で消えるので、できた画像はこのアプリの data フォルダに保存します。
          </p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={generate}
            disabled={busy || !prompt.trim() || !info.ready}
          >
            {busy ? `描いています… ${formatElapsed(now - (busySince ?? now))}` : '描く'}
          </button>
        </div>
      </section>

      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}
      {notice && <div className="alert alert-info">{notice}</div>}

      <section aria-labelledby="gallery-title">
        <div className="section-head">
          <h2 id="gallery-title">描いた画像</h2>
          <span className="muted small">{items.length} 枚</span>
        </div>
        {items.length === 0 && !busy ? (
          <p className="empty-state">まだありません。プリセットを選んで「描く」を押してみましょう。</p>
        ) : (
          <div className="gallery">
            {busy && (
              <figure className="tile">
                <div className="skeleton" style={{ aspectRatio: aspect(ratio) }}>
                  <span>描いています… {formatElapsed(now - (busySince ?? now))}</span>
                </div>
              </figure>
            )}
            {items.map((item) => (
              <figure key={item.id} className="tile">
                <a href={imageUrl(item)} target="_blank" rel="noreferrer" className="tile-media">
                  <img
                    src={imageUrl(item)}
                    alt={item.prompt}
                    loading="lazy"
                    style={{ aspectRatio: aspect(item.ratio) }}
                  />
                </a>
                <figcaption>
                  <p className="tile-prompt" title={item.prompt}>
                    {item.prompt}
                  </p>
                  <p className="muted xsmall">
                    {item.ratio} ・ {item.model}
                  </p>
                  <div className="tile-actions">
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={() => setAsPortrait(item)}
                    >
                      立ち絵に設定
                    </button>
                    <a className="btn btn-quiet btn-sm" href={imageUrl(item)} download>
                      保存
                    </a>
                    <button
                      type="button"
                      className="btn btn-quiet btn-sm"
                      onClick={() => setPrompt(item.prompt)}
                    >
                      プロンプトを使う
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => remove(item)}
                      aria-label="削除"
                    >
                      削除
                    </button>
                  </div>
                </figcaption>
              </figure>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
