import unittest
from news_monitor import Posts, classify

class NewsTests(unittest.TestCase):
 def test_gold(self): self.assertTrue(classify('Giá vàng giao ngay tăng sau CPI Mỹ'))
 def test_irrelevant(self): self.assertIsNone(classify('Doanh số bán nhà tại Úc tăng 1,2%'))
 def test_weak_geopolitics(self): self.assertIsNone(classify('Iran có phát biểu về ngoại giao với nước láng giềng'))
 def test_critical(self): self.assertTrue(classify('Hai tàu chở dầu bốc cháy ở eo biển Hormuz'))
 def test_parser(self):
  h='<div class="tgme_widget_message_wrap"><div class="tgme_widget_message_text js-message_text">Giá vàng tăng <b>mạnh</b></div><a class="tgme_widget_message_date" href="https://t.me/vnwallstreet/123"><time datetime="2026-11-08T10:00:00+00:00">10:00</time></a></div>'
  p=Posts();p.feed(h);self.assertEqual(len(p.posts),1);self.assertIn('Giá vàng',p.posts[0]['text']);self.assertEqual(p.posts[0]['url'],'https://t.me/vnwallstreet/123')
if __name__=='__main__':unittest.main()
