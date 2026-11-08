# ai-partner

APIキーを入れるだけで、Qwen でAIパートナーとブラウザでチャットできるサンプルアプリです。立ち絵を描く「画像生成」と、立ち絵を動かす「動画生成」のタブも付いています。技術書典21 合同誌の章「AIパートナーを作ろう」のおまけです。

作例として、章に出てくる桜草メイの設定（`partner/partner.md`）を同梱しています。`partner.md` を書き換えれば、あなたのパートナーになります。

- 役を演じるのは Model Studio（シンガポール）の日本語向けモデル `qwen-plus-character-ja` です（`.env` の `PARTNER_MODEL` で `qwen-plus-character` などに替えられます）。呼び方は章の STEP 2 の `talk.py` と同じ、OpenAI 互換の SDK です。
- サーバーは Python（FastAPI）、画面は Vite+（React + TypeScript）です。APIキーはサーバーの中だけで使い、ブラウザには渡しません。
- 画像生成は章の STEP 4 と同じ `qwen-image-3.0-pro`（失敗したら `qwen-image-2.0-pro` で描き直し）、動画生成は `wan3.0-video` です。どちらもチャットと同じシンガポールのキーで動きます。
- 記憶（ReMe）と声（北京のボイスデザイン）は任意です。設定しなければ無効のまま動きます。

| チャット | 画像生成 | 動画生成 |
|---|---|---|
| 立ち絵と名前を左に出したまま、吹き出しで話します | プリセットから描いて「立ち絵に設定」 | 立ち絵を最初のフレームにして動かします |

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

3. 初回は `.env` が自動で作られ、キーが空のまま起動します。画面に「はじめに」の案内（キーの作り方、`.env` の場所、書く2行）が出るので、いったん Ctrl+C で止めて、`.env` を開いてキーとワークスペースIDを書きます。

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

決まった返事を返すモックで起動します。画像生成はシルエットの仮の画像（SVG）を、動画生成は数秒で「完成」になる仮のタスクを返します（動画ファイルはできません）。画面の見た目や動きを確かめたいときに使ってください。ほかに `--port 8001`（ポートを変える）、`--no-browser`（ブラウザを開かない）、`--dev`（画面を編集しながら確かめる開発モード）があります。

### Base URL について

`DASHSCOPE_WORKSPACE_ID` を入れると、章と同じ `https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com` の `/compatible-mode/v1`（チャット）と `/api/v1`（画像・動画）を使います。空のときは `https://dashscope-intl.aliyuncs.com` を使います。手元の `transformers serve` などへ向けたいときは、`DASHSCOPE_BASE_URL` に Base URL を丸ごと書きます（章の「手元のマシンで動かす」のコラム）。

## 自分のパートナーにする

`partner/` フォルダの中身を書き換えるだけです。書き換えたら、起動し直してください。

| ファイル | 中身 |
|---|---|
| `partner/partner.md` | キャラクターの設定。そのままシステムメッセージになります（章の STEP 1） |
| `partner/partner.png` | 立ち絵（任意）。画面の左に表示されます。画像生成タブの「立ち絵に設定」でも置けます。`.webp` `.jpg` も可 |
| `partner/partner_image.txt` | 立ち絵のプロンプト。画像生成タブの最初のプリセットになります（`scripts/draw.py` も使う） |
| `partner/image_presets.md` | 画像生成タブのプリセット（差分）。`## 見出し` ごとに1つ |
| `partner/partner_voice.txt` | 声の説明（声を使うときだけ） |

画面に出る名前は、`partner.md` の「# 人物」の最初の一文（作例なら「桜草メイ」）から取ります。うまく取れないときは `.env` の `PARTNER_NAME` に書きます。モデルは `.env` の `PARTNER_MODEL` で替えます。既定の `qwen-plus-character-ja` は日本語のキャラクター会話向けですが、コンテキストが 8,192 と短めです。長い会話や記憶を足して「長すぎる」というエラーが出るときは、`HISTORY_TURNS` を減らすか、`PARTNER_MODEL=qwen-plus-character`（シンガポールで 131,072）に替えてください。

会話の履歴はブラウザ（localStorage）に残り、モデルへは直近の `HISTORY_TURNS` 往復（既定10）だけを、`partner.md` を先頭にして渡します。「会話を消す」で履歴を消せます。返事の途中で「止める」を押すと、そこまでの返事を残して止まります。

## 画像生成タブ

- プリセット（`partner_image.txt` と `image_presets.md`）を選ぶか、日本語でプロンプトを書いて「描く」を押します。
- ネガティブプロンプト（描いてほしくないもの）と縦横比（4:7 = 本の作例の `1536*2688`、9:16、3:4、1:1、4:3、16:9）を選べます。
- `qwen-image-3.0-pro` が失敗したら、`qwen-image-2.0-pro` で自動的に描き直します（キーの誤りや内容審査で止められたときは描き直しません）。モデルは `.env` の `PARTNER_IMAGE_MODEL` / `PARTNER_IMAGE_FALLBACK_MODEL` で替えられます。
- 画像のURLは24時間で消えるので、できた画像は `data/images/` に保存します。一覧から「保存」でダウンロード、「立ち絵に設定」で `partner/partner.png` に置きます（それまでの立ち絵は `data/portrait-backup/` に移します）。

コマンドで描きたいときは `python scripts/draw.py`（`.venv` を有効にしてから）でも、`partner_image.txt` から `partner/partner.png` を描けます（章の STEP 4 の `draw.py`）。

## 動画生成タブ

- 最初のフレームにする画像（いまの立ち絵か、描いた画像）を選び、どう動くかを日本語で書いて「動画を作る」を押します。長さは 5 / 10 / 15 秒です。
- `wan3.0-video` は非同期のタスクです。サーバーがタスクを作り、画面は数秒おきに状態（順番待ち → 生成中 → 完成）を確かめます。数分かかることがあり、タブを離れても、アプリを起動し直しても続きを確かめられます。
- 完成したら画面で再生でき、「保存」でダウンロードできます。動画は `data/videos/` に保存します。
- 無料枠は合計30秒ぶんです。超えると課金されるので、Model Studio の Free Quota Only の設定も確かめてください。

## 任意機能

### 記憶（ReMe）

章の STEP 3 のとおり、ReMe を別のウィンドウで起動しておき、`.env` に書きます。

```text
REME_URL=http://127.0.0.1:2333
USER_NAME=（あなたの呼び名）
```

話しかけるたびに ReMe の `/search` で記憶を探し、見つかったものを `# 覚えていること` としてシステムメッセージの末尾に足します。画面の「今日の会話を覚えてもらう」を押すと、その日の会話を `/auto_memory` に渡します。ReMe が止まっていても、チャットはそのまま続きます。

ReMe の記憶にはあなたの個人情報が入ります。`.reme/` は Git に入れないでください（`.gitignore` 済み）。ReMe は `127.0.0.1` のまま使い、インターネットへ公開しないでください。

### 声（北京のボイスデザイン）

北京のワークスペースとAPIキーを作り、`.env` に書きます（章の STEP 4）。

```text
DASHSCOPE_API_KEY_BEIJING=sk-xxxxxxxx
DASHSCOPE_WORKSPACE_ID_BEIJING=llm-xxxxxxxx
```

返事の下に「▶ 声で聞く」が出て、押すと読み上げます。初回は `partner/partner_voice.txt` から声を作り、`voice_id` を `partner/.voice_id` に保存して使い回します（作り直したいときはこのファイルを消します）。

## 動作確認の状況

APIキーなしで次を確認しています。実際の Model Studio は呼んでいません。

- Linux（Python 3.12、Node 22）で、空の状態から `python3 start.py --mock` が `.venv` の作成、ライブラリの導入、Vite+ でのビルド、起動まで通ること。
- OpenAI 互換の偽サーバーを立て、実際の `openai` SDK のストリーミングで、`partner.md` がシステムメッセージとして先頭に入ること、履歴が直近だけに絞られること、キーの誤りが画面にわかる文で返ること（`server/tests/`）。
- ReMe の偽サーバーで、記憶の検索と書き出しのリクエストの形。声は偽の `dashscope` クライアントで、声を一度だけ作って使い回す流れ。
- 画像生成は偽の `dashscope` で、モデル・サイズ・ネガティブプロンプトの渡し方、`qwen-image-2.0-pro` へのフォールバック（キーの誤りでは描き直さないこと）、保存と「立ち絵に設定」。
- 動画生成は偽の `dashscope` で、`first_frame` に立ち絵のファイルを渡すこと、タスクを状態が変わるまで確かめ、完成したら保存すること、失敗の理由が画面に出ること。
- モックで、ブラウザ（Chrome）からチャット・画像生成・動画生成を操作できること。幅 1280px とスマホ幅（390px）の両方の表示。

まだ確かめていないこと:

- 実際のキーでの `qwen-plus-character-ja` / `qwen-plus-character` の返事（Base URL、モデルID、ストリーミング対応、エラー文の対応を含む）。
- Mac と Windows の実機での起動（`start.py` は両方を想定して書いていますが、動かしたのは Linux だけです）。
- 実際のキーでの `qwen-image-3.0-pro` / `qwen-image-2.0-pro` の呼び出し。とくに縦横比ごとのサイズ（`928*1664` など）を `qwen-image-3.0-pro` が受け付けるか。
- 実際のキーでの `wan3.0-video` の呼び出し。`media` の `first_frame` にローカルファイル（`file://`）を渡す形、`duration` に 5 / 10 / 15 を渡せるか、Windows のパスでのアップロード。
- ReMe の実物、北京のボイスデザインと読み上げ。

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
server/app.py         FastAPI。/api/chat・/api/images・/api/videos と、web/dist の配信
server/character.py   partner.md、立ち絵、画像のプリセットの読み込み
server/images.py      画像生成（Qwen-Image）
server/videos.py      動画生成（Wan、非同期タスク）
server/memory.py      ReMe（任意）
server/voice.py       声（任意）
scripts/draw.py       立ち絵をコマンドで描く
web/                  画面（Vite+ / React / TypeScript）
data/                 描いた画像と動画（自動で作られます。Git には入りません）
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
