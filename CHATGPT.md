# Purpose — ChatGPT編集ガイド

このリポジトリの `data.json` がアプリ https://gjnzqqf8dq-coder.github.io/purpose/ の正データ。
ここを編集してコミットすれば、アプリに反映される（アプリは起動時と同期ボタンで読み込む）。

## スキーマ
```json
{
  "goals": [
    {"id":"g_xxx","title":"電通に受かる","deadline":"2027-06-30","note":"作戦メモ","u":1756600000000,
     "miles":[{"id":"m_xxx","title":"インターンに通る","done":false}]}
  ],
  "tasks": [
    {"id":"t_xxx","title":"ES下書き","date":"2026-09-01","done":false,"goalId":"g_xxx","mileId":"m_xxx","u":1756600000000}
  ],
  "del": {}
}
```

構造は3層：**ゴール → マイルストーン(miles、3〜5個目安) → タスク**。
タスクは `goalId` と（あれば）`mileId` で紐づく。マイルストーンの達成は `done:true`。

## ルール
- `id` はユニークな文字列（新規は `g_` / `m_` / `t_` プレフィックス推奨）
- `u` は必ず編集時点のepoch ms（これが新しい方が同期で勝つ）
- 既存エントリを消さない。削除したい時は `del` に `{"<id>": <epoch_ms>}` を追加する
- `date` / `deadline` は `YYYY-MM-DD`。`goalId` でタスクをゴールに紐づける
