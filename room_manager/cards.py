"""カードの見た目だけを整える。商品名・URLの保存値は変更しない。"""
import html

TITLE_STYLE = '''<style>
h3.product-title{color:#9c5870;font-size:clamp(1.05rem,3.7vw,1.3rem);
line-height:1.5;font-weight:650;margin:0 0 14px;
display:-webkit-box!important;padding:0!important;-webkit-box-orient:vertical;-webkit-line-clamp:3;line-clamp:3;
overflow:hidden;max-height:4.5em;overflow-wrap:anywhere;word-break:normal}
</style>'''


def card_title_html(name):
    escaped = html.escape(name, quote=True)
    return f'<h3 class="product-title" title="{escaped}">{escaped}</h3>'
