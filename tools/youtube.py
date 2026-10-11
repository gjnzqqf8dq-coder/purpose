#!/usr/bin/env python3
"""Purpose の YouTube 欄。指定チャンネルの新着を見つけ、字幕を取り、要約を youtube.json に書いて push する。
要約そのものは Claude（毎日の定期タスク purpose-youtube）が書く。このスクリプトは AI 以外の全部。

  youtube.py scan [--days N]     新着を探して字幕を取り、待ち行列に入れる（既定：前回の scan 以降。初回は3日）
  youtube.py pending             要約待ちの一覧（字幕ファイルのパス付き）を JSON で出す
  youtube.py done <id> <json>    要約を置く {one, claim, points:[{h,b}], take}（並列で書いても壊れない）
  youtube.py skip <id> [理由]     要約しない（字幕なし・中身なし等）
  youtube.py publish             置かれた要約を youtube.json に入れて commit → push
  youtube.py channels            チャンネル一覧
  youtube.py add-channel <id|URL>  チャンネルを足す（アイコンも取る）
"""
import json, re, subprocess, sys, time, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
YJ = REPO / 'youtube.json'
WORK = REPO.parent / 'youtube'          # ~/Downloads/Purpose/_作業/youtube（公開リポジトリの外）
Q = WORK / 'queue'                      # <id>.json（メタ）/ <id>.txt（字幕）/ <id>.sum.json（要約）
YT = ['yt-dlp', '--no-update', '--no-warnings', '--extractor-args', 'youtube:lang=ja']
PER_CH = 8                              # 1チャンネルあたり見る最新本数


def load():
    if YJ.exists():
        return json.loads(YJ.read_text())
    return {'v': 1, 'channels': [], 'msgs': [], 'seen': [], 'last_scan': 0}


def save(d):
    d['u'] = int(time.time() * 1000)
    YJ.write_text(json.dumps(d, ensure_ascii=False, indent=1) + '\n')


def git(*a, check=True):
    return subprocess.run(['git', '-C', str(REPO), *a], capture_output=True, text=True, check=check)


def info(url):
    r = subprocess.run([*YT, '-j', '--skip-download', url], capture_output=True, text=True, timeout=120)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None


def transcript(d):
    sb, ac = d.get('subtitles') or {}, d.get('automatic_captions') or {}
    for tr in (sb.get('ja'), ac.get('ja-orig'), ac.get('ja'), sb.get('en'), ac.get('en-orig')):
        u = [x['url'] for x in (tr or []) if x.get('ext') == 'json3']
        if not u:
            continue
        try:
            j = json.load(urllib.request.urlopen(u[0], timeout=30))
        except Exception:
            continue
        t = ''.join(s.get('utf8', '') for e in j.get('events', []) for s in (e.get('segs') or []))
        t = re.sub(r'\[(音楽|拍手|笑い|Music|Applause|Laughter)\]', '', t)
        t = re.sub(r'\n{2,}', '\n', t).strip()
        if len(t) > 200:
            return t
    return ''


def latest(ch):
    r = subprocess.run([*YT, '--flat-playlist', '-I', f'1:{PER_CH}', '--print', '%(id)s',
                        f'https://www.youtube.com/channel/{ch}/videos'], capture_output=True, text=True, timeout=120)
    return [x for x in r.stdout.split() if re.fullmatch(r'[\w-]{11}', x)]


def scan(days=None):
    d = load()
    Q.mkdir(parents=True, exist_ok=True)
    since = time.time() - days * 86400 if days else (d.get('last_scan') or time.time() - 3 * 86400) - 6 * 3600
    known = set(d['seen']) | {m['id'] for m in d['msgs']} | {p.stem for p in Q.glob('*.json') if '.' not in p.stem}
    new = 0
    for c in d['channels']:
        for vid in latest(c['id']):
            if vid in known:
                continue
            v = info(f'https://www.youtube.com/watch?v={vid}')
            if not v:
                continue
            ts = v.get('timestamp') or 0
            if ts < since or v.get('live_status') in ('is_live', 'is_upcoming') or (v.get('duration') or 0) <= 70:
                d['seen'].append(vid)      # 古い・配信中・ショートは二度と見ない
                continue
            txt = transcript(v)
            (Q / f'{vid}.txt').write_text(txt)
            (Q / f'{vid}.json').write_text(json.dumps({
                'id': vid, 'ch': c['id'], 'chName': c['name'], 't': ts * 1000, 'title': v.get('title', ''),
                'dur': v.get('duration') or 0, 'desc': (v.get('description') or '')[:1500],
                'chars': len(txt)}, ensure_ascii=False, indent=1))
            new += 1
            print(f"+ {c['name']} | {v.get('title','')[:50]} | 字幕{len(txt)}字", flush=True)
    d['seen'] = d['seen'][-3000:]
    d['last_scan'] = time.time()
    save(d)
    print(f'新着 {new} 本')


def pending():
    out = []
    for p in sorted(Q.glob('*.json')):
        if '.' in p.stem:
            continue
        if (Q / f'{p.stem}.sum.json').exists():
            continue
        m = json.loads(p.read_text())
        m['transcript_path'] = str(Q / f'{p.stem}.txt')
        out.append(m)
    print(json.dumps(out, ensure_ascii=False, indent=1))


def done(vid, js):
    s = json.loads(js)
    assert s.get('one') and s.get('points'), 'one と points は必須'
    (Q / f'{vid}.sum.json').write_text(json.dumps(s, ensure_ascii=False, indent=1))
    print('ok', vid)


def skip(vid, why=''):
    (Q / f'{vid}.sum.json').write_text(json.dumps({'skip': why or 'skip'}, ensure_ascii=False))
    print('skip', vid)


def publish():
    git('pull', '-q', '--rebase', '--autostash', check=False)
    d = load()
    have = {m['id'] for m in d['msgs']}
    n = 0
    for p in sorted(Q.glob('*.sum.json')):
        vid = p.name[:-len('.sum.json')]
        meta = Q / f'{vid}.json'
        s = json.loads(p.read_text())
        if meta.exists() and vid not in have and not s.get('skip'):
            m = json.loads(meta.read_text())
            d['msgs'].append({'id': vid, 'ch': m['ch'], 't': m['t'], 'title': m['title'], 'dur': m['dur'],
                              'at': int(time.time() * 1000), **{k: s[k] for k in ('one', 'claim', 'points', 'take') if k in s}})
            n += 1
        if vid not in d['seen']:
            d['seen'].append(vid)
        for f in (p, meta, Q / f'{vid}.txt'):
            f.unlink(missing_ok=True)
    d['msgs'].sort(key=lambda m: m['t'])
    d['msgs'] = d['msgs'][-400:]
    save(d)
    if n:
        git('add', 'youtube.json')
        git('commit', '-q', '-m', f'YouTube: {n} 本の要約')
        r = git('push', '-q', check=False)
        if r.returncode:
            git('pull', '-q', '--rebase', check=False)
            git('push', '-q')
    print(f'公開 {n} 本')


def add_channel(x):
    cid = x if re.fullmatch(r'UC[\w-]{22}', x) else None
    url = f'https://www.youtube.com/channel/{cid}' if cid else x
    r = subprocess.run([*YT, '-J', '--flat-playlist', '-I', '0', url], capture_output=True, text=True, timeout=120)
    j = json.loads(r.stdout)
    cid = j.get('channel_id') or cid
    th = [t for t in j.get('thumbnails', []) if 'avatar' in (t.get('id') or '')] or j.get('thumbnails', [])
    av = next((t['url'] for t in th if (t.get('width') or 0) <= 200 and t.get('width')), th[0]['url'] if th else '')
    d = load()
    d['channels'] = [c for c in d['channels'] if c['id'] != cid]
    d['channels'].append({'id': cid, 'name': j.get('channel') or j.get('title', ''), 'handle': j.get('uploader_id') or '', 'avatar': av})
    save(d)
    print('added', cid, j.get('channel'))


if __name__ == '__main__':
    a = sys.argv[1:] or ['help']
    if a[0] == 'scan':
        scan(int(a[2]) if len(a) > 2 and a[1] == '--days' else None)
    elif a[0] == 'pending':
        pending()
    elif a[0] == 'done':
        done(a[1], a[2])
    elif a[0] == 'skip':
        skip(a[1], ' '.join(a[2:]))
    elif a[0] == 'publish':
        publish()
    elif a[0] == 'channels':
        print('\n'.join(f"{c['id']}  {c['name']}" for c in load()['channels']))
    elif a[0] == 'add-channel':
        add_channel(a[1])
    else:
        print(__doc__)
