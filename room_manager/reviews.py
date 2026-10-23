"""今回取得した商品だけをレビュー条件で絞る。レビューの真正性は判定しない。"""
import math

RATINGS = (4.0, 4.3, 4.5)
COUNTS = (30, 100, 300)


def review_number(value, maximum=None):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0 or (maximum is not None and number > maximum):
        return None
    return number


def filter_reviews(products, min_rating=4.3, min_count=100):
    selected = []
    for p in products:
        rating, count = review_number(p.get('rating'), 5), review_number(p.get('reviews'))
        if rating is not None and count is not None and count.is_integer() and rating >= min_rating and count >= min_count:
            selected.append(p)
    # 件数の多い順、同点は評価の高い順。価格は並び順に使わない。
    return sorted(selected, key=lambda p: (float(p['reviews']), float(p['rating'])), reverse=True)
