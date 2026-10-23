"""商品名の表記による季節の参考並び替え。追加通信・仕様の推測はしない。"""
from datetime import datetime
import unicodedata
from .domain import JST

SEASONS = ('自動', '春', '夏', '秋', '冬', 'すべて')
TERMS = {
    '春': ('春', 'カーディガン', 'ブラウス', '薄手', '長袖', 'トレンチ'),
    '夏': ('夏', '半袖', 'ノースリーブ', 'タンクトップ', 'リネン', '麻'),
    '秋': ('秋', 'ニット', 'カーディガン', '長袖', 'スウェット', 'ジャケット'),
    '冬': ('冬', 'ニット', 'コート', 'ダウン', '裏起毛', '防寒', '厚手'),
}


def resolve_season(selection, at=None):
    if selection != '自動':
        return selection
    current = at or datetime.now(JST)
    if current.tzinfo is None:
        raise ValueError('自動季節の判定にはタイムゾーン付き日時が必要です。')
    month = current.astimezone(JST).month
    return '春' if 3 <= month <= 5 else '夏' if 6 <= month <= 8 else '秋' if 9 <= month <= 11 else '冬'


def prioritize_season(products, season):
    if season == 'すべて':
        return list(products)
    def score(product):
        name = unicodedata.normalize('NFKC', product.get('name') or '')
        points = sum(2 for term in TERMS.get(season, ()) if term in name)
        if season in ('秋', '冬'):
            points -= sum(4 for term in ('半袖', 'ノースリーブ', 'タンクトップ', 'キャミソール') if term in name)
        elif season == '夏':
            points -= sum(4 for term in ('裏起毛', '防寒', 'ダウン', '厚手') if term in name)
        return points
    # 同点はAPIの取得順。除外せず、重ね着用の商品も残す。
    return sorted(products, key=score, reverse=True)
