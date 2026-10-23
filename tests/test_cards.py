import html
import unittest
from room_manager.cards import card_title_html, TITLE_STYLE
from room_manager.seasons import prioritize_season

class CardTests(unittest.TestCase):
    def test_escaped_full_title_not_data_mutation(self):
        name='【セール】'*40+'<script>alert("x")</script>&ニット'
        product={'name':name,'url':'https://item.rakuten.co.jp/demo/one/?scid=x&sc2id=y'}
        before=dict(product)
        rendered=card_title_html(product['name'])
        self.assertNotIn('<script>',rendered)
        self.assertIn(html.escape(name,quote=True),rendered)
        self.assertIn('-webkit-line-clamp:3',TITLE_STYLE)
        self.assertIn('overflow:hidden',TITLE_STYLE)
        self.assertEqual(product,before)

    def test_autumn_clothes_over_uv_and_summer_without_removal(self):
        items=[{'name':'UV対策 長袖 パーカー 春夏秋'}, {'name':'秋 カーディガン 長袖'},
               {'name':'秋 ニット 長袖'}, {'name':'秋 羽織 ジャケット'},
               {'name':'サマーニット 半袖'}, {'name':'小物'}]
        result=prioritize_season(items,'秋')
        self.assertEqual(set(p['name'] for p in result[:3]),set(p['name'] for p in items[1:4]))
        self.assertEqual(len(result),len(items))
        self.assertEqual(result[-1],items[4])
        self.assertEqual(prioritize_season(items,'すべて'),items)
        self.assertEqual(items[0]['name'],'UV対策 長袖 パーカー 春夏秋')
