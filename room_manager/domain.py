from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit, urlunsplit
JST = timezone(timedelta(hours=9))
def now():
    return datetime.now(JST).isoformat(timespec="seconds")

def canonical_url(url):
    if not url:
        return ''
    p = urlsplit(url.strip())
    if p.scheme not in ('http', 'https') or not p.netloc or p.username or p.password:
        raise ValueError('URLは http:// または https:// から始まる形式で入力してください。')
    # アフィリエイトの転送先はクエリで区別されるため削除しない。
    query = p.query if p.hostname == 'hb.afl.rakuten.co.jp' else ''
    return urlunsplit(('https', p.netloc.lower(), p.path.rstrip('/'), query, ''))
