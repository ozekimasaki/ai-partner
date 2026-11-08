import { useState } from 'react';
import type { PartnerInfo } from '../api';

const ENV_SNIPPET = 'DASHSCOPE_API_KEY=sk-ここにキー\nDASHSCOPE_WORKSPACE_ID=llm-ここにワークスペースID';

export function SetupGuide({ info }: { info: PartnerInfo }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(ENV_SNIPPET);
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  }

  return (
    <section className="setup card" aria-labelledby="setup-title">
      <p className="eyebrow">はじめに</p>
      <h2 id="setup-title">APIキーを設定すると、{info.name}が話せるようになります</h2>
      <ol className="steps">
        <li>
          <strong>キーを作る</strong>
          <span>
            Model Studio で、リージョンを<b>シンガポール</b>にして API キーを作ります（本の STEP
            0）。キーは作ったときに一度だけ表示されるので、すぐ控えてください。
            <a
              href="https://www.alibabacloud.com/help/en/model-studio/get-api-key"
              target="_blank"
              rel="noreferrer"
            >
              作り方を見る
            </a>
          </span>
        </li>
        <li>
          <strong>.env に書く</strong>
          <span>
            次のファイルをテキストエディタで開き、2行を書き換えて保存します。
            <code className="path">{info.env_path}</code>
          </span>
          <div className="snippet">
            <pre>{ENV_SNIPPET}</pre>
            <button type="button" className="btn btn-quiet btn-sm" onClick={copy}>
              {copied ? 'コピーしました' : 'コピー'}
            </button>
          </div>
        </li>
        <li>
          <strong>起動し直す</strong>
          <span>
            start.py のウィンドウで <kbd>Ctrl</kbd> + <kbd>C</kbd> を押して止め、もう一度起動します。
          </span>
        </li>
      </ol>
      <p className="hint">
        キーなしで画面だけ試すなら <code>python3 start.py --mock</code>（Windows は{' '}
        <code>py start.py --mock</code>）。
      </p>
    </section>
  );
}
