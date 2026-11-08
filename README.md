# ai-partner

APIキーを入れるだけで、Qwen でAIパートナーとブラウザでチャットできるサンプルアプリです。技術書典21 合同誌の章「AIパートナーを作ろう」のおまけです。

作例として、章に出てくる桜草メイの設定（`partner/partner.md`）を同梱しています。`partner.md` を書き換えれば、あなたのパートナーになります。

- 役を演じるのは Model Studio（シンガポール）の日本語向けモデル `qwen-plus-character-ja` です（`.env` の `PARTNER_MODEL` で `qwen-plus-character` などに替えられます）。呼び方は章の STEP 2 の `talk.py` と同じ、OpenAI 互換の SDK です。
- サーバーは Python（FastAPI）、画面は Vite+（React + TypeScript）です。APIキーはサーバーの中だけで使い、ブラウザには渡しません。
- 記憶（ReMe）と声（北京のボイスデザイン）と立ち絵は任意です。設定しなければ無効のまま、チャットだけで動きます。

## 必要なもの

| もの | 入れ方 |
|---|---|
| Python 3.10 以上 | Mac も Windows も <https://www.python.org/downloads/> のインストーラーが迷いません。Windows では「Add python.exe to PATH」にチェックを入れます |
| Node.js 20 以上（LTS） | <https://nodejs.org/> の LTS 版のインストーラー |
| Model Studio のAPIキー | 章の STEP 0 のとおり、シンガポールで作ったキー |

Vite+ は `web/` の依存として自動で入るので、別に入れる必要はありません。

## 起動する（ワンコマンド）

1. このリポジトリを取得します（Code → Download ZIP を展開するか、`git clone https://github.com/ozekimasaki/ai-partner`）。
2. フォルダの中で、次の1行を打ちます。Mac はターミナル、Windows は PowerShell です。

   **Mac**

   ```bash
   python3 start.py
   ```

   **Windows**

   ```powershell
   py start.py
   ```

   ダブルクリックで起動したいときは、Mac は `start.command`、Windows は `start.bat` を使います（Mac で「開けません」と出たら、右クリック → 開く）。

3. 初回は `.env` が自動で作られ、キーが空のまま起動します。画面に「APIキーが設定されていません」と出るので、いったん Ctrl+C で止めて、`.env` を開いてキーとワークスペースIDを書きます。

   ```text
   DASHSCOPE_API_KEY=sk-xxxxxxxx
   DASHSCOPE_WORKSPACE_ID=llm-xxxxxxxx
   ```

4. もう一度 `python3 start.py`（Windows は `py start.py`）を打つと、ブラウザで <http://127.0.0.1:8000> が開きます。「ただいま」と話しかけてみてください。

`start.py` は初回だけ、`.venv`（Python の仮想環境）の作成、Python と Node のライブラリの導入、画面のビルドを自動で行います。2回目からはすぐ起動します。止めるときは Ctrl+C です。

### キーなしで画面だけ見る

```bash
python3 start.py --mock
```

決まった返事を返すモックで起動します。画面の見た目や動きを確かめたいときに使ってください。ほかに `--port 8001`（ポートを変える）、`--no-browser`（ブラウザを開かない）、`--dev`（画面を編集しながら確かめる開発モード）があります。

### Base URL について

`DASHSCOPE_WORKSPACE_ID` を入れると、章と同じ `https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1` を使います。空のときは `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` を使います。手元の `transformers serve` などへ向けたいときは、`DASHSCOPE_BASE_URL` に Base URL を丸ごと書きます（章の「手元のマシンで動かす」のコラム）。

## 自分のパートナーにする

`partner/` フォルダの中身を書き換えるだけです。書き換えたら、起動し直してください。

| ファイル | 中身 |
|---|---|
| `partner/partner.md` | キャラクターの設定。そのままシステムメッセージになります（章の STEP 1） |
| `partner/partner.png` | 立ち絵（任意）。置くと画面の左に表示されます。`.webp` `.jpg` も可 |
| `partner/partner_image.txt` | 立ち絵を描くときのプロンプト（`scripts/draw.py` が使う） |
| `partner/partner_voice.txt` | 声の説明（声を使うときだけ） |

画面に出る名前は、`partner.md` の「# 人物」の最初の一文（作例なら「桜草メイ」）から取ります。うまく取れないときは `.env` の `PARTNER_NAME` に書きます。モデルは `.env` の `PARTNER_MODEL` で替えます。既定の `qwen-plus-character-ja` は日本語のキャラクター会話向けですが、コンテキストが 8,192 と短めです。長い会話や記憶を足して「長すぎる」というエラーが出るときは、`HISTORY_TURNS` を減らすか、`PARTNER_MODEL=qwen-plus-character`（シンガポールで 131,072）に替えてください。

会話の履歴はブラウザ（localStorage）に残り、モデルへは直近の `HISTORY_TURNS` 往復（既定10）だけを、`partner.md` を先頭にして渡します。「リセット」で履歴を消せます。

## 任意機能

### 立ち絵を描く

```bash
pip install -r server/requirements-extra.txt   # .venv を有効にしてから
python scripts/draw.py
```

`partner/partner_image.txt` から `qwen-image-3.0-pro` で描いて、`partner/partner.png` に保存します（章の STEP 4 の `draw.py`）。自分で描いた絵を `partner/partner.png` として置いてもかまいません。

### 記憶（ReMe）

章の STEP 3 のとおり、ReMe を別のウィンドウで起動しておき、`.env` に書きます。

```text
REME_URL=http://127.0.0.1:2333
USER_NAME=（あなたの呼び名）
```

話しかけるたびに ReMe の `/search` で記憶を探し、見つかったものを `# 覚えていること` としてシステムメッセージの末尾に足します。画面の「今日の会話を覚えてもらう」を押すと、その日の会話を `/auto_memory` に渡します。ReMe が止まっていても、チャットはそのまま続きます。

ReMe の記憶にはあなたの個人情報が入ります。`.reme/` は Git に入れないでください（`.gitignore` 済み）。ReMe は `127.0.0.1` のまま使い、インターネットへ公開しないでください。

### 声（北京のボイスデザイン）

北京のワークスペースとAPIキーを作り、`.env` に書きます。北京のキーを書くと、`start.py` が声用のライブラリ（`dashscope`）も自動で入れます。

```text
DASHSCOPE_API_KEY_BEIJING=sk-xxxxxxxx
DASHSCOPE_WORKSPACE_ID_BEIJING=llm-xxxxxxxx
```

返事の横に ▶ が出て、押すと読み上げます。初回は `partner/partner_voice.txt` から声を作り、`voice_id` を `partner/.voice_id` に保存して使い回します（作り直したいときはこのファイルを消します）。

## 動作確認の状況

APIキーなしで次を確認しています。実際の Model Studio は呼んでいません。

- Linux（Python 3.12、Node 22）で、空の状態から `python3 start.py --mock` が `.venv` の作成、ライブラリの導入、Vite+ でのビルド、起動まで通ること。
- OpenAI 互換の偽サーバーを立て、実際の `openai` SDK のストリーミングで、`partner.md` がシステムメッセージとして先頭に入ること、履歴が直近だけに絞られること、キーの誤りが画面にわかる文で返ること（`server/tests/`）。
- ReMe の偽サーバーで、記憶の検索と書き出しのリクエストの形。声は偽の `dashscope` クライアントで、声を一度だけ作って使い回す流れ。
- モックで、ブラウザから送信して返事がストリーミングで表示されること。

まだ確かめていないこと:

- 実際のキーでの `qwen-plus-character-ja` / `qwen-plus-character` の返事（Base URL、モデルID、ストリーミング対応、エラー文の対応を含む）。
- Mac と Windows の実機での起動（`start.py` は両方を想定して書いていますが、動かしたのは Linux だけです）。
- ReMe の実物、北京のボイスデザインと読み上げ、`scripts/draw.py` の実物の呼び出し。声は `dashscope` 2.0.4 の関数の形（`voice_design.create(prefix=..., language_hints=...)`、戻り値の `voice_id`）に合わせて書いていて、章の `speak.py` とは引数名が少し違います。

## テスト

```bash
# サーバー
python3 -m venv .venv && . .venv/bin/activate   # Windows は .venv\Scripts\Activate.ps1
pip install -r server/requirements-dev.txt
python -m pytest server/tests

# 画面
cd web && npm install && npm test && npm run check
```

## フォルダ構成

```text
start.py              ワンコマンド起動（start.command / start.bat はそのラッパー）
.env.example          設定の見本（.env にコピーして使う）
partner/              パートナーの設定（partner.md など）
server/app.py         FastAPI。/api/chat でモデルを呼び、web/dist を配信する
server/character.py   partner.md と立ち絵の読み込み
server/memory.py      ReMe（任意）
server/voice.py       声（任意）
scripts/draw.py       立ち絵を描く（任意）
web/                  画面（Vite+ / React / TypeScript）
```

## 参考リンク

章「AIパートナーを作ろう」で参照したページの全リストです（2026年11月8日時点）。

1. [Model Studio: How to obtain an API key](https://www.alibabacloud.com/help/en/model-studio/get-api-key)
2. [Model Studio: OpenAI compatible Chat](https://www.alibabacloud.com/help/en/model-studio/qwen-api-via-openai-chat-completions)
3. [Model Studio: Role-playing (Qwen-Character)](https://www.alibabacloud.com/help/en/model-studio/role-play)
4. [Model Studio: qwen-plus-character-ja](https://www.alibabacloud.com/help/en/model-studio/qwen-plus-character-ja)
5. [Model Studio: qwen3.8-omni-flash](https://www.alibabacloud.com/help/en/model-studio/qwen3-8-omni-flash)
6. [Qwen: Qwen3.8-27B model card](https://huggingface.co/Qwen/Qwen3.8-27B)
7. [Hugging Face: Transformers Serving](https://huggingface.co/docs/transformers/serving)
8. [Model Studio: Free quota for new users](https://www.alibabacloud.com/help/en/model-studio/new-free-quota)
9. [Model Studio: Model pricing](https://www.alibabacloud.com/help/en/model-studio/model-pricing)
10. [Model Studio: Wan3.0 Video Generation](https://www.alibabacloud.com/help/en/model-studio/wan3-video-generation-guide)
11. [Model Studio: ロールプレイ（日本語版）](https://www.alibabacloud.com/help/ja/model-studio/role-play)
12. [ReMe（GitHub）](https://github.com/agentscope-ai/ReMe)
13. [ReMe: Configuration](https://reme.agentscope.io/en/configuration)
14. [ReMe: Auto Memory](https://reme.agentscope.io/en/auto_memory)
15. [Model Studio: qwen3.8-flash](https://www.alibabacloud.com/help/en/model-studio/qwen3-8-flash)
16. [Model Studio: List models](https://docs.modelstudio.console.alibabacloud.com/en/model-studio/list-models)
17. [Model Studio: Qwen-Image API reference](https://www.alibabacloud.com/help/en/model-studio/qwen-image-api)
18. [Model Studio: Voice Design](https://www.alibabacloud.com/help/en/model-studio/qwen-tts-voice-design)
19. [Alibaba Cloud: Roadmap on Full-Stack AI Strategy（2026-09-22）](https://www.alibabacloud.com/en/press-room/alibaba-unveils-roadmap-on-full-stack-ai-strategy)
20. [Qwen: Qwen3.8-Flash-Next model card](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)

## ライセンスと注意

- 自分だけのパートナーとして遊ぶ前提のサンプルです。誰かに使ってもらうなら、相手がAIと話しているとわかる表示（画面下に出しています）や、つらい相談への応え方も考えてください。
- `.env`（APIキー）は Git に入れないでください（`.gitignore` 済み）。
