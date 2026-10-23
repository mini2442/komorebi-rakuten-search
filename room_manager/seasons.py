"""商品名の表記による季節の参考並び替え。追加通信・仕様の推測はしない。"""
from datetime import datetime
import unicodedata
from .domain import JST

SEASONS = ('自動', '春', '夏', '秋', '冬', 'すべて')
TERMS = {
    '春': {'春': 3, 'カーディガン': 6, 'ブラウス': 4, '薄手': 2, '長袖': 2, 'トレンチ': 6, '羽織': 4},
    '夏': {'夏': 3, '半袖': 5, 'ノースリーブ': 5, 'タンクトップ': 5, 'リネン': 3, '麻': 2, 'UV': 4, '冷感': 4},
    '秋': {'秋': 3, 'ニット': 8, 'カーディガン': 8, '長袖': 2, 'スウェット': 4, 'ジャケット': 6, '羽織': 6, 'ブルゾン': 6},
    '冬': {'冬': 3, 'ニット': 6, 'コート': 8, 'ダウン': 8, '裏起毛': 6, '防寒': 6, '厚手': 4},
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
        points = sum(weight for term, weight in TERMS.get(season, {}).items() if term in name)
        if season in ('秋', '冬'):
            points -= sum(8 for term in ('半袖', 'ノースリーブ', 'タンクトップ', 'キャミソール') if term in name)
            if any(term in name for term in ('UV', 'uv', '紫外線', '日焼け', 'サマー', '接触冷感', 'ひんやり')):
                points -= 8
        elif season == '夏':
            points -= sum(4 for term in ('裏起毛', '防寒', 'ダウン', '厚手') if term in name)
        return points
    # 同点はAPIの取得順。除外せず、重ね着用の商品も残す。
    return sorted(products, key=score, reverse=True)
