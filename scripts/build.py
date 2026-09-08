"""Build public issue content into a credential-free, static blog."""
import html
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


def shell(title, content, path='/', description='记录、叙述、回忆。这里是 JasperYux 的个人博客。'):
    esc = html.escape
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(description, quote=True)}">
<link rel="canonical" href="{BASE}{path}"><meta property="og:type" content="{'website' if path == '/' else 'article'}">
<meta property="og:title" content="{esc(title, quote=True)}"><meta property="og:description" content="{esc(description, quote=True)}"><meta property="og:url" content="{BASE}{path}">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/site.css">
<link rel="alternate" type="application/atom+xml" title="JasperYux's Blog" href="/feed.xml">
<script defer src="/assets/site.js"></script></head><body><a class="skip" href="#main">跳到正文</a><div class="shell">
<header class="topbar"><a class="brand" href="/">JasperYux<span>.</span></a><nav aria-label="主导航"><a href="/">文章</a><a href="/#archive">归档</a><a href="https://github.com/{OWNER}/{REPO}">GitHub ↗</a></nav></header>
{content}<footer><span>© {datetime.now(ZoneInfo('Asia/Shanghai')).year} JasperYux · 记录、叙述、回忆</span><a href="/feed.xml">RSS 订阅 ↗</a></footer></div></body></html>'''


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
        # Show the latest week's actual content on annual journal cards.
        excerpt_body = body
        if is_weekly:
            sections = re.split(r'(?m)^##\s+', body)
            candidates = []
            for section in sections:
                found = re.match(r'(20\d{2})年第(\d+)周', section)
                if found:
                    candidates.append((int(found[1]), int(found[2]), section))
            if candidates:
                excerpt_body = max(candidates)[2]
        excerpt = plain(excerpt_body)
        excerpt = excerpt[:150] + ('…' if len(excerpt) > 150 else '')
        search = html.escape((title + ' ' + plain(body)).lower(), quote=True)
        cards.append(f'''<article class="post-card" data-year="{year}" data-search="{search}">{meta}<h2><a href="{url}">{html.escape(title)}</a></h2><p>{html.escape(excerpt)}</p><a class="read-link" href="{url}">{"阅读周报" if is_weekly else "阅读全文"}<span aria-hidden="true">↗</span></a></article>''')
        rendered.append((post, article, url))
    archives = ''.join(f'<a class="archive-link" href="/posts/{items[0]["number"]}/" data-filter-year="{year}">{year}<span>{len(items)} 篇 ↗</span></a>' for year, items in sorted(years.items(), reverse=True))
    content = f'''<main id="main"><section class="hero"><div class="eyebrow">A PERSONAL JOURNAL</div><h1>记录、叙述、回忆。</h1><p>关于生活的片段，也关于一路走来的自己。</p></section>
<div class="home-layout"><section id="articles" aria-label="文章列表"><h2 class="section-heading">最近更新<span id="result-count" aria-live="polite">{len(posts)} 篇记录</span></h2>{''.join(cards)}<p class="empty" id="empty" hidden>没有找到相关记录，试试其他关键词。</p></section>
<aside class="sidebar"><section><label class="search-label" for="search">找一段回忆</label><input id="search" type="search" placeholder="搜索文章或正文" autocomplete="off"><button class="clear-filter" id="clear-filter" hidden>清除筛选</button><noscript><p>搜索需要启用 JavaScript，文章可直接阅读。</p></noscript></section><section id="archive"><h2>年度周报</h2>{archives}</section><section class="about"><h2>关于这里</h2><p>把日常写下来，<br>给未来的自己留一些回忆。</p><a class="read-link" href="https://github.com/{OWNER}">认识 JasperYux ↗</a></section></aside></div></main>'''
    write('index.html', shell("JasperYux's Blog · 记录、叙述、回忆", content))
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
    for url in ['/'] + [url for _, _, url in rendered]:
        ET.SubElement(ET.SubElement(sitemap, 'url'), 'loc').text = BASE + url
    write('sitemap.xml', ET.tostring(sitemap, encoding='unicode', xml_declaration=True))
    write('robots.txt', f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n')
    write('.nojekyll', '')
    print(f'Built {len(posts)} articles; {sum(p.stat().st_size for p in OUTPUT.rglob("*") if p.is_file()) / 1024:.1f} KiB total.')


if __name__ == '__main__':
    main()
