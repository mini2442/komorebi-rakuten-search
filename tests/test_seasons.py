import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from room_manager.cards import card_title_html

def card_titles(at):
    return [m.value for m in at.markdown if m.value.startswith('<h3 class="product-title"')]

from room_manager.seasons import resolve_season, prioritize_season
import test_public
SECRETS, ITEM = test_public.SECRETS, test_public.ITEM

class SeasonTests(unittest.TestCase):
    def test_japan_month_boundaries(self):
        self.assertEqual(resolve_season('自動', datetime(2026, 8, 31, 16, tzinfo=timezone.utc)), '秋')
        self.assertEqual(resolve_season('自動', datetime(2026, 11, 30, 16, tzinfo=timezone.utc)), '冬')
        for month, expected in ((2,'冬'),(3,'春'),(5,'春'),(6,'夏'),(8,'夏'),(9,'秋'),(11,'秋'),(12,'冬')):
            self.assertEqual(resolve_season('自動',datetime(2026,month,15,tzinfo=timezone.utc)),expected)
        self.assertEqual(resolve_season('すべて'),'すべて')

    def test_priority_preserves_items_urls_and_stable_order(self):
        products=[{'name':'半袖Tシャツ','url':'https://example.com/?x=1'}, {'name':'長袖ニット'}, {'name':'小物A'}, {'name':'小物B'}]
        original=[dict(p) for p in products]
        result=prioritize_season(products,'秋')
        self.assertEqual(result[0]['name'],'長袖ニット')
        self.assertEqual(result[-1],products[0])
        self.assertEqual([p['name'] for p in result[1:3]],['小物A','小物B'])
        self.assertEqual(products,original)
        self.assertEqual(prioritize_season(products,'すべて'),products)
        self.assertEqual(prioritize_season(products,'夏')[0],products[0])

# Reuse the existing network blockade, mock clock and response fixture only.
class SeasonUITests(unittest.TestCase):
    setUp = test_public.PublicTests.setUp
    reply = test_public.PublicTests.reply
    @patch('streamlit.secrets',SECRETS)
    @patch('room_manager.providers.requests.get')
    def test_season_change_search_once_and_ranking_official_order(self,get):
        get.return_value=self.reply(items=[dict(ITEM,itemCode='demo:short',itemName='半袖'),dict(ITEM,itemCode='demo:knit',itemName='長袖ニット')])
        at=AppTest.from_file('app.py').run(timeout=10)
        next(s for s in at.selectbox if s.label=='季節').set_value('秋').run()
        get.assert_not_called()
        at.button[0].click().run()
        self.assertFalse(at.exception)
        self.assertEqual(card_titles(at),[card_title_html(name) for name in ['長袖ニット','半袖']])
        self.assertEqual(get.call_count,1)
        next(s for s in at.selectbox if s.label=='季節').set_value('冬').run()
        self.assertFalse(card_titles(at))
        self.assertEqual(get.call_count,1)
        at.button[1].click().run()
        self.assertEqual(card_titles(at),[card_title_html(name) for name in ['半袖','長袖ニット']])
        self.assertEqual(get.call_count,2)
        at.selectbox[0].set_value('韓国コスメ・美容').run()
        self.assertFalse(any(s.label=='季節' for s in at.selectbox))
        self.assertEqual(get.call_count,2)
