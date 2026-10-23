import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from room_manager.reviews import filter_reviews
import test_public

class ReviewTests(unittest.TestCase):
    def test_boundaries_invalid_stable_order_and_urls(self):
        products=[dict(name='boundary',rating=4.3,reviews=100,url='https://example.com/?x=1'),
                  dict(name='many',rating=4.3,reviews=300),dict(name='high',rating=4.5,reviews=100),
                  dict(name='few',rating=5,reviews=99),dict(name='low',rating=4.29,reviews=300)]
        self.assertEqual([p['name'] for p in filter_reviews(products)],['many','high','boundary'])
        self.assertEqual(filter_reviews(products)[-1]['url'],products[0]['url'])
        self.assertEqual(len(products),5)
        for rating,count in ((None,100),(4.5,None),(float('nan'),100),(6,100),(4.5,-1),(True,100),(4.5,100.5)):
            self.assertEqual(filter_reviews([dict(rating=rating,reviews=count)]),[])
        for rating in (4.0,4.3,4.5):
            for count in (30,100,300):
                self.assertEqual(len(filter_reviews([dict(rating=rating,reviews=count)],rating,count)),1)

class ReviewUITests(unittest.TestCase):
    setUp = test_public.PublicTests.setUp
    reply = test_public.PublicTests.reply

    @patch('streamlit.secrets',test_public.SECRETS)
    @patch('room_manager.providers.requests.get')
    def test_defaults_filter_count_zero_mode_and_ranking(self,get):
        get.return_value=self.reply(items=[dict(test_public.ITEM,itemCode='demo:ok',itemName='ニット'),
                                         dict(test_public.ITEM,itemCode='demo:new',itemName='新商品か不明',reviewCount=0,reviewAverage=0)])
        at=AppTest.from_file('app.py').run(timeout=10)
        self.assertEqual(next(s for s in at.selectbox if s.label=='レビュー評価').value,4.3)
        self.assertEqual(next(s for s in at.selectbox if s.label=='レビュー件数').value,100)
        get.assert_not_called()
        at.button[0].click().run()
        self.assertEqual([h.value for h in at.subheader],['ニット'])
        self.assertEqual(get.call_args.kwargs['params']['sort'],'-reviewCount')
        self.assertTrue(any('2件のうち1件' in c.value for c in at.caption))
        next(s for s in at.selectbox if s.label=='レビュー件数').set_value(300).run()
        self.assertFalse(at.subheader)
        self.assertEqual(get.call_count,1)
        at.button[0].click().run()
        self.assertTrue(any('0件' in i.value for i in at.info))
        self.assertFalse(at.subheader)
        self.assertTrue(any('Supported by Rakuten Developers' in m.value for m in at.markdown))
        at.checkbox[0].check().run()
        self.assertTrue(next(s for s in at.selectbox if s.label=='レビュー評価').disabled)
        self.assertTrue(next(s for s in at.selectbox if s.label=='レビュー件数').disabled)
        self.assertEqual(get.call_count,2)
        at.button[0].click().run()
        self.assertEqual(get.call_args.kwargs['params']['sort'],'-updateTimestamp')
        self.assertEqual(len(at.subheader),2)
        self.assertTrue(any('発売日' in c.value for c in at.caption))
        at.button[1].click().run()
        self.assertIn('ichibaranking',get.call_args.args[0])
        self.assertNotIn('sort',get.call_args.kwargs['params'])
        self.assertEqual(len(at.subheader),2)
        self.assertEqual(get.call_count,4)
        self.assertFalse(at.exception)
