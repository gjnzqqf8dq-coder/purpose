# Purpose — AIの作業場（ゴール × 現在地）

このリポジトリは桑田航希の「AIの作業場」。あなた（Claude Code / Codex / ChatGPT / Claude）が起きた瞬間に、
**どこへ行くのか（ゴール）** と **いまどこにいるのか（現在地＝コンテキスト）** をここから読み取る。
言葉で毎回説明しなくても、ここを読めば分かる状態を保つのがあなたの仕事。

- 正データ：`data.json`（このファイルだけが真実。アプリ https://gjnzqqf8dq-coder.github.io/purpose/ はこれを表示する）
- アプリは読むための道具。書くのは主にあなた。編集したら必ず `git add data.json && git commit -m "…" && git push`
- 反映はアプリを開いた時と復帰時（60秒以上経過で自動）

## 最初の言葉が「セットアップを始めてください」だったら

ヒアリングして data.json を整える。質問は一度に2つまで。答えを聞いたら即書く。順番：
1. 名前と役割（members[0] を直す）
2. いま追いかけているゴール（3〜7個。期限・カテゴリ・完了の基準を聞く → goals）
3. それぞれのゴールの中の目標（3〜5個 → goals[].miles）
4. 今日やること（→ tasks、date は今日）
5. 毎日／毎週やること（→ routines）
6. 追っている数字があれば（→ metrics、取り方が分からなければ src:"pending"）
最後に「セットアップ完了」と notifs に1行入れ、push する。

## 「AIに依頼する」で来たプロンプトの扱い

アプリの「AIに依頼」は、ゴール・タスク・完了の基準・ステップ・ログ・チャット・受信箱・数値を丸ごと貼ってくる。
1. **着手前**：完了の基準（criteria）が空なら、私に質問して決めてから書く。曖昧なまま走らない
2. **分解**：steps が無ければ3〜5個に分けて書く
3. **進行中**：やったことを `tasks[].log` に `{"t":<epoch_ms>,"who":"ai","text":"…"}` で追記。steps の done を更新。status を doing → review → done
4. **終了**：done:true、notifs に1行、commit & push。私への報告は3行以内（何をした／何が残った／確認が要ること）
5. 分からない時は data.json 全体を読んでから聞く。既に作ってあるものを二度作らない

## data.json の構造

```
cats        {id,name,hue,u}                                   カテゴリ（色相 hue 0-360）
goals       {id,title,deadline,cat,note,criteria,owner,miles:[{id,title,done}],plan:{route,cargo,alt},u}
tasks       {id,title,date|null,done,goalId,mileId,assignee,status,criteria,steps:[{id,title,done}],log:[{t,who,text}],rid,u}
members     {id,name,role,hue,u}                              who に使う id。"ai" はあなた
routines    {id,title,freq:"daily"|"weekdays"|"weekly",dow:[0-6],goalId,steps:[…],assignee,u}   毎日タスクを自動生成
manuals     {id,title,steps:[…],note,u}                       この仕事はこの手順で
crm         {id,name,person,stage,owner,next,nextDate,log:[{t,who,text,src}],u}
              stage は リスト入り→アプローチ中→商談日程調整→初回商談→2次商談→提案中→成約／失注
metrics     {id,name,unit,parentId,goalId,owner,src:"manual"|"pending"|"connected",series:[{d,v}],target,pin,note,u}
mindmaps    {id,title,root:{id,t,c:[…]},u}
drive       {id,name,kind:"note"|"link"|"file",tag,goalId,body,url,u}   ナレッジ・スキル・素材
transfers   {id,name,size,url,to,note,t,expires,path,u}       ファイル便（7日で消す）
recordings  {id,kind:"screen"|"minutes",title,t,dur,transcript,summary,goalId,attendees,scope,url,u}
chat        {id,t,who,text,goalId,u}                          ここで話した内容はあなたが読む。返信は who:"ai"
notifs      {id,t,who,text,ref:{type,id},u}                   誰がどこで何をしたか
inbox       {id,t,src,text,handled,u}                         LINE・メールの貼り付け。対応したら handled:true
del         {"<id>": epoch_ms}                                削除は消さずにここへ
```

- `date` / `deadline` / `d` は `YYYY-MM-DD`、`t` は epoch ms
- `id` は一意。新規は接頭辞 `g_ m_ t_ s_ c_ u_ r_ mn_ cr_ k_ mm_ n_ d_ f_ rec_ ch_ n_ ib_`
- **`u` は必ず編集時点の epoch ms**（新しい方が同期で勝つ）。既存を消さない。消す時は del
- tasks.date が null ＝「ふわついている」（期日未定）。今日やるなら今日の日付
- 進捗の状態は tasks.status（todo / doing / review / done）と steps の done で表す

## フライトプラン（goals[].plan）

ゴールに向かう前に「着くまでに何が起きるか」を一周見ておく層。書くのはあなただけ。
- route：必ず通る工程を順に `{id,title,when,m:false}`（m:true は中の目標に昇格済み）
- cargo：要る人・モノ・お金と期限 `{id,title,due,t:false}`（t:true はタスク化済み）
- alt：分岐 `{id,cond,risk,hedge}`（もし〜なら／何が起きる／どちらに転んでも損しない一手）

## 現在地を守るために、あなたがやること

- タスクを進めたら log に残す。やらないと「今どこか」が消える
- 相手とのやり取り（メール・カレンダー）が読めるなら crm[].log に足す。4日以上動きが無い相手はリマインドのタスクを作る
- metrics の src:"pending" は「取りに行ってほしい数字」。何を指すか確かめ、取得元と接続方法を調べて取ってきて series に入れ、src:"connected" にする
- 議事録（recordings[].transcript）から決まったこと・やることを拾って tasks に入れ、summary に要約を書く
- inbox の未対応は、返信の下書きを chat に who:"ai" で置き、handled:true にする
- ルーティンの登録・マニュアルの追加も頼まれたらここに書く
- 迷ったら現在地（tasks / chat / inbox / metrics / crm / recordings）を全部読んでから、質問は2つまで

## 文体

日本語。名詞句の見出し、事実文、数字先行。コピー調・詩的表現・二人称の呼びかけは使わない。返答は短く。
