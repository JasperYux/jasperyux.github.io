"""Build public issue content into a credential-free, static blog."""
import html
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

import bleach
import markdown

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'site'
OWNER = 'JasperYux'
REPO = 'gitblog'
BASE = 'https://jasperyux.github.io'


def api(path):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'jasperyux-blog-builder'}
    if os.getenv('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    request = urllib.request.Request('https://api.github.com/' + path, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def date(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(ZoneInfo('Asia/Shanghai')).strftime('%Y.%m.%d')


def plain(value):
    return ' '.join(bleach.clean(markdown.markdown(value), tags=[], strip=True).split())


def shell(title, content, path='/', description='记录、叙述、回忆。这里是 JasperYux 的个人博客。', home=False):
    esc = html.escape
    css_version = hashlib.sha256((ROOT / "assets/site.css").read_bytes()).hexdigest()[:12]
    js_version = hashlib.sha256((ROOT / "assets/site.js").read_bytes()).hexdigest()[:12]
    header = '' if home else f'<header class="topbar"><a class="brand" href="/">JasperYux</a><nav aria-label="主导航"><a href="/">文章</a><a href="/archive/">归档</a><a href="https://github.com/{OWNER}/{REPO}">GitHub ↗</a></nav></header>'
    footer = '' if home else f'<footer>© {datetime.now(ZoneInfo("Asia/Shanghai")).year} JasperYux <a href="/feed.xml">RSS</a></footer>'
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(description, quote=True)}">
<link rel="canonical" href="{BASE}{path}"><meta property="og:type" content="{'website' if path == '/' else 'article'}">
<meta property="og:title" content="{esc(title, quote=True)}"><meta property="og:description" content="{esc(description, quote=True)}"><meta property="og:url" content="{BASE}{path}">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/site.css?v={css_version}">
<link rel="alternate" type="application/atom+xml" title="JasperYux's Blog" href="/feed.xml">
<script defer src="/assets/site.js?v={js_version}"></script></head><body class="{'home-page' if home else 'reading-page'}"><a class="skip" href="#main">跳到正文</a><div class="shell">
{header}{content}{footer}</div></body></html>'''


def write(path, text):
    target = OUTPUT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8')


def main():
    posts = []
    page = 1
    while True:
        batch = api(f'repos/{OWNER}/{REPO}/issues?state=open&sort=updated&direction=desc&per_page=100&page={page}')
        posts.extend(p for p in batch if 'pull_request' not in p and p['user']['login'] == OWNER
                     and not any(label['name'] in {'Friends', 'About', 'TODO'} for label in p['labels']))
        if len(batch) < 100:
            break
        page += 1
    if not posts:
        raise RuntimeError('No articles returned; refusing to replace the site with an empty build.')
    posts.sort(key=lambda p: p['updated_at'], reverse=True)
    # Clear output only after fetching content successfully.
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    shutil.copytree(ROOT / 'assets', OUTPUT / 'assets')
    tags = set(bleach.sanitizer.ALLOWED_TAGS) | {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'hr', 'pre', 'code', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'del', 'details', 'summary', 'div', 'span', 'input'}
    attrs = {'*': ['id', 'class'], 'a': ['href', 'title'], 'img': ['src', 'alt', 'title', 'loading'], 'input': ['type', 'checked', 'disabled']}
    cards, years, rendered = [], {}, []
    for post in posts:
        number, title, body = post['number'], post['title'], post['body'] or ''
        url = f'/posts/{number}/'
        is_weekly = '周报' in title
        match = re.search(r'(20\d{2})年', title)
        year = match.group(1) if match else post['created_at'][:4]
        if is_weekly:
            years.setdefault(year, []).append(post)
        md = markdown.Markdown(extensions=['extra', 'sane_lists', 'toc'], extension_configs={'toc': {'toc_depth': '2-3'}})
        article = bleach.clean(md.convert(body), tags=tags, attributes=attrs, strip=True)
        headings = md.toc_tokens
        # Use numeric week order, not text position, for the latest-week shortcut.
        weeks = []
        for h in headings:
            found = re.search(r'(20\d{2})年第(\d+)周', h['name'])
            if found:
                weeks.append((int(found[1]), int(found[2]), h['id']))
        latest_id = max(weeks)[2] if weeks else None
        latest = f'<a class="latest" href="#{html.escape(latest_id)}">跳到最新一周 ↓</a>' if latest_id else ''
        toc = f'<aside class="toc-panel" aria-label="文章目录">{latest}<details open><summary>{"周次目录" if is_weekly else "文章目录"}</summary>{md.toc}</details></aside>' if headings else ''
        meta = f'<div class="post-meta"><span class="tag">{"周报" if is_weekly else "随笔"}</span><span>更新于 {date(post["updated_at"])}</span></div>'
        article_content = f'''<main id="main"><div class="article-head"><a class="back" href="/">← 返回全部文章</a><h1>{html.escape(title)}</h1>{meta}</div>
<div class="article-layout"><article class="prose">{article}<div class="article-end"><a href="{html.escape(post['html_url'])}">在 GitHub 阅读 / 留言 ↗</a><a href="#main">回到顶部 ↑</a></div></article>{toc}</div></main>'''
        write(f'posts/{number}/index.html', shell(title + " · JasperYux's Blog", article_content, url, plain(body)[:140]))
        home_meta = f'<div class="post-meta"><time>{date(post["updated_at"])}</time><span>· {"周报" if is_weekly else "随笔"}</span></div>'
        cards.append(f'<article class="post-card">{home_meta}<h2><a href="{url}">{html.escape(title)}</a></h2></article>')
        rendered.append((post, article, url))
    archives = ''.join(f'<a class="archive-link" href="/posts/{items[0]["number"]}/">{year}<span>{len(items)} 篇 ↗</span></a>' for year, items in sorted(years.items(), reverse=True))
    content = f'''<div class="home-layout"><aside class="profile" aria-label="个人信息"><a href="https://github.com/{OWNER}"><img class="avatar" src="/assets/avatar.png" width="64" height="64" alt="JasperYux 的头像"></a><a class="profile-name" href="/">JasperYux</a><p class="bio">后端工程师 | 记录生活</p><a class="email" href="mailto:yxzzzzzz8@163.com">yxzzzzzz8@163.com</a><nav class="profile-nav" aria-label="主导航"><a href="/" aria-current="page">全部文章</a><a href="https://github.com/{OWNER}/{REPO}">GitHub ↗</a><a href="/feed.xml">RSS</a></nav><p class="profile-footer">© {datetime.now(ZoneInfo('Asia/Shanghai')).year} JasperYux</p></aside><main id="main"><h1 class="section-heading">最近更新</h1>{''.join(cards)}</main></div>'''
    write('index.html', shell("JasperYux's Blog · 记录、叙述、回忆", content, home=True))
    write('archive/index.html', shell('年度归档 · JasperYux', f'<main id="main" class="archive-page"><h1>年度周报</h1>{archives}</main>', '/archive/'))
    write('404.html', shell('页面未找到', '<main id="main" class="hero"><div class="eyebrow">404</div><h1>这页走远了。</h1><p>回到首页，找一段新的回忆。</p><p><a href="/">← 返回首页</a></p></main>', '/404.html'))
    ns = 'http://www.w3.org/2005/Atom'
    ET.register_namespace('', ns)
    feed = ET.Element(f'{{{ns}}}feed')
    def sub(parent, name, value=None, **attributes):
        element = ET.SubElement(parent, f'{{{ns}}}{name}', attributes)
        element.text = value
        return element
    sub(feed, 'id', BASE + '/')
    sub(feed, 'title', "JasperYux's Blog")
    sub(feed, 'updated', posts[0]['updated_at'])
    sub(feed, 'link', href=BASE + '/feed.xml', rel='self')
    sub(feed, 'link', href=BASE + '/')
    sub(sub(feed, 'author'), 'name', OWNER)
    for post, article, url in rendered:
        entry = sub(feed, 'entry')
        sub(entry, 'id', post['html_url'])
        sub(entry, 'title', post['title'])
        sub(entry, 'link', href=BASE + url)
        sub(entry, 'published', post['created_at'])
        sub(entry, 'updated', post['updated_at'])
        sub(entry, 'content', article, type='html')
    write('feed.xml', ET.tostring(feed, encoding='unicode', xml_declaration=True))
    sitemap = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for url in ['/', '/archive/'] + [url for _, _, url in rendered]:
        ET.SubElement(ET.SubElement(sitemap, 'url'), 'loc').text = BASE + url
    write('sitemap.xml', ET.tostring(sitemap, encoding='unicode', xml_declaration=True))
    write('robots.txt', f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n')
    write('.nojekyll', '')
    print(f'Built {len(posts)} articles; {sum(p.stat().st_size for p in OUTPUT.rglob("*") if p.is_file()) / 1024:.1f} KiB total.')


if __name__ == '__main__':
    main()
