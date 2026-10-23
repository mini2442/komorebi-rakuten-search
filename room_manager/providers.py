"""楽天公式APIのみ使用。認証値・リクエストURL・応答本文をログに出さない。"""
import time
import math
import threading
from collections import deque
import requests
from urllib.parse import urlsplit, parse_qs
from .domain import now, canonical_url
from .rakuten_settings import RakutenSettings

# 公開検索専用。停止する場合はFalseへ戻す。Secrets・画面操作では切り替えない。
LIVE_API_ENABLED = True

# 同じPythonプロセスのセッション間でも最低間隔と429の待機を共有。
_request_lock = threading.Lock()
_last_request = 0.0
_cooldown_until = 0.0
_request_times = deque()
MAX_PER_MINUTE = 10
MAX_PER_HOUR = 100

class RakutenProvider:
    def __init__(self, *, enabled=False, settings=None):
        self.enabled = enabled
        self.settings = settings or RakutenSettings()

    def configured(self):
        return bool(self.settings.application_id and self.settings.access_key)

    def permitted(self):
        return LIVE_API_ENABLED and self.enabled

    def search(self, keyword, *, genre_id=None, max_price=None, sort=None):
        if not keyword.strip():
            raise ValueError('検索キーワードを入力してください。')
        params = {'keyword': keyword.strip(), 'hits': 30, 'availability': 1}
        if sort is not None:
            if sort not in ('-reviewCount', '-reviewAverage', '-updateTimestamp'):
                raise ValueError('並び替え条件を確認してください。')
            params['sort'] = sort
        if genre_id:
            params['genreId'] = genre_id
        if max_price:
            params['maxPrice'] = max_price
        return self._fetch('IchibaItem/Search/20260701', params)

    def item(self, item_code):
        if not isinstance(item_code, str) or not __import__('re').fullmatch(r'[A-Za-z0-9_-]+:[A-Za-z0-9_.-]+', item_code):
            raise ValueError('楽天の商品識別子を確認してください。')
        return self._fetch('IchibaItem/Search/20260701', {'itemCode': item_code, 'hits': 1})

    def ranking(self, genre_id='0'):
        if not str(genre_id).isdigit():
            raise ValueError('ジャンルIDを確認してください。')
        params = {} if str(genre_id) == '0' else {'genreId': str(genre_id)}
        return self._fetch('IchibaItem/Ranking/20220601', params)

    def _fetch(self, endpoint, params):
        global _last_request, _cooldown_until
        if not LIVE_API_ENABLED:
            raise ValueError("クラウド版の楽天API通信は停止中です。公開前の利用条件確認と、別工程での有効化が必要です。")
        if not self.enabled:
            raise ValueError('API接続は停止中です。')
        if not self.configured():
            raise ValueError('API未設定です。Streamlit SecretsのApplication IDとAccess Keyを確認してください。')
        headers = {'accessKey': self.settings.access_key}
        referer = self.settings.referer
        if referer:
            canonical_url(referer)
            headers['Referer'] = referer
        app_id = self.settings.application_id
        affiliate_id = self.settings.affiliate_id
        params = dict(params, applicationId=app_id, format='json', formatVersion=2)
        if affiliate_id:
            params['affiliateId'] = affiliate_id
        url = 'https://openapi.rakuten.co.jp/' + ('ichibaranking' if 'Ranking' in endpoint else 'ichibams') + '/api/' + endpoint
        with _request_lock:
            current = time.monotonic()
            while _request_times and current - _request_times[0] >= 3600:
                _request_times.popleft()
            if len(_request_times) >= MAX_PER_HOUR or sum(current - t < 60 for t in _request_times) >= MAX_PER_MINUTE:
                raise ValueError('検索アプリ全体の取得上限です。時間を置いてお試しください。自動再試行はしません。')
            if time.monotonic() < _cooldown_until:
                raise ValueError('利用制限のため待機中です。しばらく待ってから再取得してください。')
            time.sleep(max(0, 1.1 - (time.monotonic() - _last_request)))
            _last_request = time.monotonic()
            _request_times.append(_last_request)
            try:
                response = requests.get(url, params=params, headers=headers, timeout=(5, 20), allow_redirects=False)
            except requests.Timeout:
                raise ValueError('楽天APIに接続できませんでした（時間切れ）。ネット接続を確認し、時間を置いて再取得してください。') from None
            except requests.exceptions.SSLError:
                raise ValueError('楽天APIの安全な接続を確認できませんでした。実行環境の日時・証明書・ネット接続を確認してください。') from None
            except requests.RequestException:
                raise ValueError('楽天APIに接続できませんでした。ネット接続・SSL環境を確認してください。') from None
            status = response.status_code
            if status == 429:
                try:
                    wait = max(60, min(3600, int(response.headers.get('Retry-After', 60))))
                except (ValueError, TypeError):
                    wait = 60
                _cooldown_until = time.monotonic() + wait
                raise ValueError(f'楽天APIの利用制限です。少なくとも{wait}秒待ってから再取得してください。自動再試行はしません。')
        if status in (401, 403):
            raise ValueError('楽天APIの認証・アクセス許可エラーです。Application ID・Access Key・楽天側の許可IP／登録サイト設定を確認してください。')
        if status == 400:
            raise ValueError('楽天APIが設定または検索条件を受け付けませんでした。認証設定・キーワード・ジャンルを確認してください。')
        if status == 404:
            return []
        if status in (500, 503):
            raise ValueError(f'楽天API側が一時的に利用できません（HTTP {status}）。時間を置いて再取得してください。自動再試行はしません。')
        if status != 200:
            raise ValueError(f'楽天API取得失敗（HTTP {status}）。時間を置いて再取得してください。')
        try:
            data = response.json()
            if not isinstance(data, dict) or data.get('error'):
                raise ValueError()
            items = data.get('Items', data.get('items'))
            if not isinstance(items, list):
                raise ValueError()
            result, seen = [], set()
            for raw in items:
                x = raw.get('Item', raw.get('item', raw))
                identifier, name, item_url = x['itemCode'], x['itemName'], x['itemUrl']
                if not all(isinstance(v, str) and v.strip() for v in (identifier, name, item_url)):
                    raise ValueError()
                canonical_url(item_url)
                if urlsplit(item_url).hostname == 'hb.afl.rakuten.co.jp':
                    target = parse_qs(urlsplit(item_url).query).get('pc', [None])[0]
                    if target and urlsplit(target).hostname == 'item.rakuten.co.jp':
                        item_url = target
                if identifier in seen:
                    continue
                seen.add(identifier)
                ranking = 'Ranking' in endpoint
                snapshot = dict(name=name, price=self._number(x.get('itemPrice')),
                    image_url=self._image_url(x), url=item_url, genre_id=x.get('genreId'),
                    reviews=self._number(x.get('reviewCount')), rating=self._number(x.get('reviewAverage')),
                    rank=self._number(x.get('rank')) if ranking else None,
                    api_rate=self._number(x.get('affiliateRate')), shop_name=x.get('shopName'))
                result.append(dict(id=identifier, **snapshot, base_rate=None, boost_rate=None,
                    boost_confirmed=False, reward_cap=None, sample=False, fetched_at=now(),
                    source='楽天公式API：' + endpoint, source_kind='rakuten_api',
                    affiliate_url=x.get('affiliateUrl'),
                    item_caption=x.get('itemCaption') if isinstance(x.get('itemCaption'), str) else None,
                    acquisition={'endpoint': endpoint, 'genre_id': params.get('genreId'),
                                 'keyword': params.get('keyword'), 'ranking_title': data.get('title')},
                    api_data=snapshot, analyses={'competition': {}, 'reward': {}, 'popularity': {}, 'target': {}},
                    season='未取得', trend=None, fit=None, competition=None))
            return result
        except (ValueError, KeyError, TypeError, AttributeError):
            raise ValueError('APIの応答形式を確認できません。データは保存していません。') from None

    @staticmethod
    def _number(value):
        if value is None or value == '':
            return None
        number = float(value)
        if not math.isfinite(number) or number < 0:
            raise ValueError()
        return int(number) if number.is_integer() else number

    @staticmethod
    def _image_url(item):
        images = item.get('mediumImageUrls') or item.get('smallImageUrls') or []
        if not images:
            return None
        first = images[0]
        return first.get('imageUrl') if isinstance(first, dict) else first
