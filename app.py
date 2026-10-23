"""公開検索専用。DB・投稿・ログイン情報は読み込まない。"""
import streamlit as st
from urllib.parse import urlsplit
from room_manager.rakuten_settings import provider_from_secrets
from room_manager.seasons import SEASONS, resolve_season, prioritize_season
from room_manager.reviews import RATINGS, COUNTS, filter_reviews
from room_manager.cards import TITLE_STYLE, card_title_html

CATEGORIES = {
    'プチプラファッション': ('100371', 'レディース', 5000),
    '韓国コスメ・美容': ('100939', '韓国', None),
    '子供服・育児グッズ': ('100533', 'ベビー', None),
    '暮らし・便利グッズ': ('215783', '便利', None),
}
CREDIT = '''<!-- Rakuten Web Services Attribution Snippet FROM HERE -->
<a href="https://developers.rakuten.com/" target="_blank">Supported by Rakuten Developers</a>
<!-- Rakuten Web Services Attribution Snippet TO HERE -->'''


def safe_product_link(url):
    try:
        p = urlsplit(url)
        return (p.scheme == 'https' and p.hostname in ('item.rakuten.co.jp', 'hb.afl.rakuten.co.jp')
                and not p.username and not p.password and p.port in (None, 443))
    except (ValueError, TypeError):
        return False



def safe_image_url(url):
    try:
        p = urlsplit(url)
        if (p.scheme == 'https' and p.hostname == 'thumbnail.image.rakuten.co.jp'
                and not p.username and not p.password and p.port in (None, 443)):
            return url
    except (ValueError, TypeError):
        pass
    return None


def show_value(value, suffix=''):
    return '未取得' if value is None or value == '' else str(value) + suffix


def main():
    st.set_page_config(page_title='こもれび 商品さがし', page_icon='🌷', layout='centered')
    st.markdown('<style>.stButton button,.stLinkButton a{min-height:48px;border-radius:14px}.block-container{max-width:850px}h1,h2,h3{color:#9c5870}</style>', unsafe_allow_html=True)
    st.markdown(TITLE_STYLE, unsafe_allow_html=True)
    st.title('🌷 こもれび 商品さがし')
    st.caption('楽天市場の商品検索・ランキング。楽天グループが運営するサービスではありません。')
    st.caption('個人の投稿・下書きは扱いません。検索欄に個人情報を入力しないでください。')
    provider = provider_from_secrets(st.secrets)
    ready = provider.configured() and provider.permitted()
    if not provider.permitted():
        st.warning('公開前の準備中です。楽天APIへの実通信は停止しています。')
    elif not provider.configured():
        st.warning('接続準備中です。時間を置いてご利用ください。')
    category = st.selectbox('ジャンル', list(CATEGORIES))
    genre, default_keyword, price = CATEGORIES[category]
    keyword = st.text_input('探したい商品', default_keyword, max_chars=128, key='keyword_'+category)
    season = 'すべて'
    new_mode, min_rating, min_count = False, 4.3, 100
    fashion = category == 'プチプラファッション'
    if category == 'プチプラファッション':
        selection = st.selectbox('季節', SEASONS, key='fashion_season')
        season = resolve_season(selection)
        st.caption(('日本時間の月で自動選択：' + season + '。' if selection == '自動' else '') + '季節判定は商品名の表記からの推定です。今回取得した範囲で、ニット・カーディガン・季節の羽織りなどを参考に並べ替えます。完全除外はせず、季節への適合を保証するものではありません。ランキングは公式の順番を維持します。')
    if fashion:
        new_mode = st.checkbox('新着商品モード', key='fashion_new_mode')
        min_rating = st.selectbox('レビュー評価', RATINGS, index=1, format_func=lambda v: f'★{v:.1f}以上', disabled=new_mode, key='min_rating')
        min_count = st.selectbox('レビュー件数', COUNTS, index=1, format_func=lambda v: f'{v}件以上', disabled=new_mode, key='min_count')
        if new_mode:
            st.caption('最低レビュー条件を外し、商品情報の更新が新しい順で最大30件取得します。発売日・初出品日が新しい商品とは限りません。レビュー0件・未取得の商品も表示対象です。')
        else:
            st.caption('APIのレビュー件数順で最大30件取得し、その中で評価・件数を絞ります。季節優先の中では件数→評価の順。価格順には並べません。レビューの真正性・品質を保証する判定ではありません。')
        st.caption('ファッション検索の価格条件は従来どおり5,000円以下です。レビュー条件・新着モードは商品検索だけに適用し、公式ランキングには適用しません。')
    context = (category, keyword, season, new_mode, min_rating, min_count)
    if not ready or st.session_state.get('result_context') != context:
        st.session_state.pop('public_results', None)
    st.caption('検索は各テーマのキーワードで絞ります。ランキングは公式ジャンル全体で、韓国製・価格帯などを保証しません。')
    search = st.button('🔎 商品を検索', disabled=not ready, use_container_width=True)
    ranking = st.button('🌷 ランキングを見る', disabled=not ready, use_container_width=True)
    if search or ranking:
        st.session_state.pop('public_results', None)
        st.session_state['result_context'] = context
        try:
            with st.spinner('商品を確認しています…'):
                if search:
                    sort = ('-updateTimestamp' if new_mode else '-reviewCount') if fashion else None
                    result = provider.search(keyword, genre_id=genre, max_price=price, sort=sort)
                else:
                    result = provider.ranking(genre)
            received_count = len(result)
            if search and fashion and not new_mode:
                result = filter_reviews(result, min_rating, min_count)
            if search and season != 'すべて':
                result = prioritize_season(result, season)
            st.session_state['public_results'] = result
            st.session_state['public_result_kind'] = 'search' if search else 'ranking'
            st.session_state['received_count'] = received_count
            if not result:
                st.info('今回取得した範囲では表示条件に合う商品が0件でした。条件を緩めるか新着商品モードをお試しください。追加取得は自動で行いません。' if received_count else '該当商品は0件でした。検索条件を変えてお試しください。')
        except ValueError as error:
            st.error(str(error))
    if st.session_state.get('result_context') == context and 'public_results' in st.session_state:
        st.caption(f"今回取得した{st.session_state.get('received_count', 0)}件のうち{len(st.session_state['public_results'])}件を表示。楽天市場の全商品を調べた結果ではありません。")
    if st.session_state.get('public_results') and st.session_state.get('public_result_kind') == 'search' and season != 'すべて':
        st.caption(season + '向けの表記がある商品を優先しています（今回の取得結果内での参考順）。')
    for product in st.session_state.get('public_results', []):
        with st.container(border=True):
            st.markdown(card_title_html(product['name']), unsafe_allow_html=True)
            image_url = safe_image_url(product.get('image_url'))
            if image_url:
                st.image(image_url, width=128)
            else:
                st.caption('🌷 商品画像は未取得です。楽天の商品ページで確認できます')
            st.write('価格：' + show_value(product.get('price'), '円（取得時点）'))
            st.write('レビュー：' + show_value(product.get('reviews'), '件') + ' ／ 評価：' + show_value(product.get('rating')))
            st.write('ランキング順位：' + show_value(product.get('rank'), '位'))
            link = product.get('affiliate_url') or product['url']
            if safe_product_link(link):
                st.link_button('楽天の商品ページを見る', link, use_container_width=True)
            else:
                st.warning('商品リンクの形式を確認できません。表示を見合わせています。')
            st.caption('出典：' + product['source'] + ' ／ 取得日時：' + product['fetched_at'])
            st.caption('正式な商品名・価格・在庫・送料・仕様は楽天の商品ページでご確認ください。')
    st.caption('自動取得・自動再試行はありません。1プロセス全体で10回/分・100回/時まで、最低1.1秒間隔です。再起動で上限記録はリセットされます。')
    st.caption('検索結果をDBやファイルに保存する機能・一括出力機能はありません。')
    if st.session_state.get('result_context') == context and 'public_results' in st.session_state:
        st.markdown(CREDIT, unsafe_allow_html=True)


if __name__ == '__main__':
    main()
