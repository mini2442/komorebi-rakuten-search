import copy
import time
import unittest
from collections import deque
from unittest.mock import Mock, patch
import requests
from streamlit.testing.v1 import AppTest
from room_manager import providers
from room_manager.rakuten_settings import provider_from_secrets

SECRETS = {'RAKUTEN_APPLICATION_ID':'fake-private-id','RAKUTEN_ACCESS_KEY':'fake-private-key'}
ITEM = dict(itemCode='demo:one',itemName='モック商品',itemUrl='https://item.rakuten.co.jp/demo/one/?x=1',itemPrice=1000,reviewCount=3,reviewAverage=4,rank=2)

class PublicTests(unittest.TestCase):
    def setUp(self):
        block=patch('requests.sessions.Session.request',side_effect=AssertionError('No real HTTP'))
        block.start(); self.addCleanup(block.stop)
        timer=patch('room_manager.providers.time',Mock(monotonic=time.monotonic, sleep=Mock()))
        timer.start(); self.addCleanup(timer.stop)
        state=patch.multiple(providers,_request_times=deque(),_last_request=0.0,_cooldown_until=0.0)
        state.start(); self.addCleanup(state.stop)

    def reply(self,status=200,items=None):
        reply=Mock(status_code=status,headers={})
        reply.json.return_value={'items':[copy.deepcopy(ITEM)] if items is None else items}
        return reply

    def test_hard_stop_all_routes_and_ui(self):
        p=provider_from_secrets(SECRETS)
        for call in (lambda:p.search('商品'),p.ranking,lambda:p.item('demo:one')):
            with self.assertRaisesRegex(ValueError,'停止中'):call()
        with patch('streamlit.secrets',SECRETS):
            at=AppTest.from_file('app.py').run(timeout=10)
            self.assertFalse(at.exception)
            self.assertTrue(all(b.disabled for b in at.button))
            output=str(at)
            self.assertNotIn(SECRETS['RAKUTEN_ACCESS_KEY'],output)
            self.assertNotIn(SECRETS['RAKUTEN_APPLICATION_ID'],output)

    @patch('room_manager.providers.LIVE_API_ENABLED',True)
    @patch('room_manager.providers.requests.get')
    def test_search_ranking_ui_links_context_and_no_save(self,get):
        get.return_value=self.reply()
        with patch('streamlit.secrets',SECRETS):
            at=AppTest.from_file('app.py').run(timeout=10)
            at.button[0].click().run(timeout=10)
            self.assertFalse(at.exception)
            self.assertEqual(len(at.get('link_button')),1)
            self.assertEqual(at.get('link_button')[0].url,ITEM['itemUrl'])
            self.assertTrue(any('Supported by Rakuten Developers' in m.value for m in at.markdown))
            self.assertFalse(any('保存' in b.label for b in at.button))
            self.assertEqual(get.call_count,1)
            at.button[1].click().run(timeout=10)
            self.assertIn('ichibaranking',get.call_args.args[0])
            self.assertFalse(at.exception)
            at.text_input[0].set_value('変更').run(timeout=10)
            self.assertEqual(len(at.get('link_button')),0)

    @patch('room_manager.providers.LIVE_API_ENABLED',True)
    @patch('room_manager.providers.requests.get')
    def test_limits_errors_zero_and_no_secret_messages(self,get):
        p=provider_from_secrets(SECRETS)
        get.return_value=self.reply(items=[])
        self.assertEqual(p.search('商品'),[])
        for status in (400,401,403,500,503):
            get.return_value=self.reply(status)
            with self.assertRaises(ValueError) as error:p.search('商品')
            self.assertNotIn(SECRETS['RAKUTEN_ACCESS_KEY'],str(error.exception))
        get.side_effect=requests.Timeout('fake-private-key')
        with self.assertRaisesRegex(ValueError,'時間切れ'):p.ranking()
        get.side_effect=None;get.return_value=self.reply(429)
        with self.assertRaisesRegex(ValueError,'利用制限'):p.ranking()
        count=get.call_count
        with self.assertRaisesRegex(ValueError,'待機中'):p.ranking()
        self.assertEqual(count,get.call_count)

    @patch('room_manager.providers.LIVE_API_ENABLED',True)
    @patch('room_manager.providers.requests.get')
    def test_shared_rate_limit(self,get):
        get.return_value=self.reply()
        p=provider_from_secrets(SECRETS)
        with patch('room_manager.providers.time.monotonic',return_value=10000):
            for _ in range(10):p.search('商品')
            with self.assertRaisesRegex(ValueError,'取得上限'):provider_from_secrets(SECRETS).ranking()
        self.assertEqual(get.call_count,10)
        with patch('room_manager.providers.time.monotonic',return_value=10100):
            providers._request_times=deque([10000]*100)
            with self.assertRaisesRegex(ValueError,'取得上限'):p.ranking()
        self.assertEqual(get.call_count,10)

    @patch('streamlit.secrets',{})
    def test_unconfigured_ui(self):
        at=AppTest.from_file('app.py').run(timeout=10)
        self.assertFalse(at.exception)
        self.assertTrue(all(b.disabled for b in at.button))

    def test_url_and_dependency_boundary(self):
        from app import safe_product_link
        self.assertTrue(safe_product_link(ITEM['itemUrl']))
        for url in ('https://evil.example/','javascript:alert(1)','https://item.rakuten.co.jp@evil.example/'):
            self.assertFalse(safe_product_link(url))
        from pathlib import Path
        for path in [Path('app.py'),*Path('room_manager').glob('*.py')]:
            text=path.read_text()
            self.assertNotIn('supabase',text.lower())
            self.assertNotIn('sqlite',text.lower())
        self.assertFalse(providers.LIVE_API_ENABLED)
