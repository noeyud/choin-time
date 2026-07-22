# -*- coding: utf-8 -*-
"""현자타임 갤러리: 개념글 + 추천받은 최근 글 -> quotes.json"""
import json, re, time, sys
from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup

GALL = 'hyunjatime'
BASE = 'https://gall.dcinside.com'
LIST_URL = BASE + '/mgallery/board/lists/?id=' + GALL
VIEW_URL = BASE + '/mgallery/board/view/?id=' + GALL + '&no={no}'
KST = timezone(timedelta(hours=9))
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9',
    'Referer': LIST_URL,
}
SKIP_SUBJECT = {'공지', '설문', 'AD', '뉴스', '이슈'}
MIN_REC_NORMAL = 2
TAG_KEYWORDS = [
    ('수면', ['잠', '수면', '일찍 자']),
    ('환경', ['환경', '휴대폰', '폰을', '방을', '트리거', '차단']),
    ('복귀', ['리셋', '복귀', '실패', '다시 시작']),
    ('충동', ['충동', '욕구', '참기', '참는']),
    ('습관', ['습관', '루틴', '기록']),
    ('위기', ['위기', '고비', '위험']),
    ('지루함', ['심심', '지루']),
]

def clean(t):
    t = re.sub(r'\s+', ' ', t or '').strip()
    t = re.sub(r'- dc official App', '', t).strip()
    return t

def parse_rows(soup, min_rec):
    out = []
    for row in soup.select('tr.ub-content'):
        num = row.select_one('.gall_num')
        tit = row.select_one('.gall_tit a')
        subj = row.select_one('.gall_subject')
        writer = row.select_one('.gall_writer')
        date = row.select_one('.gall_date')
        rec = row.select_one('.gall_recommend')
        if not num or not tit:
            continue
        no = num.get_text(strip=True)
        if not no.isdigit():
            continue
        if subj and subj.get_text(strip=True) in SKIP_SUBJECT:
            continue
        try:
            rc = int(rec.get_text(strip=True)) if rec else 0
        except ValueError:
            rc = 0
        if rc < min_rec:
            continue
        nick = writer.get('data-nick') if writer and writer.get('data-nick') else (writer.get_text(strip=True) if writer else '')
        d = (date.get('title') or date.get_text(strip=True)) if date else ''
        out.append({'no': int(no), 'title': clean(tit.get_text()), 'nick': clean(nick), 'date': d[:10].replace('-', '.'), 'rec': rc})
    return out

def main():
    s = requests.Session()
    s.headers.update(HEADERS)
    posts = {}
    sources = [
        (LIST_URL + '&exception_mode=recommend', 0),
        (LIST_URL + '&page=1', MIN_REC_NORMAL),
        (LIST_URL + '&page=2', MIN_REC_NORMAL),
    ]
    for url, min_rec in sources:
        try:
            r = s.get(url, timeout=20)
            if r.status_code != 200:
                continue
            for p in parse_rows(BeautifulSoup(r.text, 'html.parser'), min_rec):
                posts[p['no']] = p
            time.sleep(0.6)
        except Exception as e:
            print('list skip', url, e, file=sys.stderr)
    ordered = sorted(posts.values(), key=lambda p: p['no'], reverse=True)[:16]
    if not ordered:
        print('no posts parsed', file=sys.stderr)
        sys.exit(1)
    items = []
    for p in ordered:
        if len(items) >= 10:
            break
        try:
            time.sleep(0.8)
            rv = s.get(VIEW_URL.format(no=p['no']), timeout=20)
            if rv.status_code != 200:
                continue
            vs = BeautifulSoup(rv.text, 'html.parser')
            body = vs.select_one('.write_div')
            if not body:
                continue
            for junk in body.select('script, style, img, iframe, video'):
                junk.decompose()
            text = clean(body.get_text(' '))
            if len(text) < 30:
                continue
            if len(text) > 160:
                cut = text[:160]
                sp = cut.rfind(' ')
                text = (cut[:sp] if sp > 100 else cut) + '…'
            tags = [tag for tag, kws in TAG_KEYWORDS if any(k in (text + p['title']) for k in kws)][:2]
            items.append({
                'id': p['no'],
                'text': text,
                'title': p['title'][:40],
                'date': p['date'],
                'nick': p['nick'][:20],
                'url': VIEW_URL.format(no=p['no']),
                'tags': tags,
            })
        except Exception as e:
            print('skip', p['no'], e, file=sys.stderr)
    if len(items) < 3:
        print('too few items (%d) — keeping previous quotes.json' % len(items), file=sys.stderr)
        sys.exit(0)
    out = {'updated': datetime.now(KST).strftime('%Y-%m-%d %H:%M'), 'source': '현자타임 갤러리', 'items': items}
    with open('quotes.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print('wrote quotes.json with', len(items), 'items')

if __name__ == '__main__':
    main()
