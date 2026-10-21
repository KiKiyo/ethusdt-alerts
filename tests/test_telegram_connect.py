import unittest
from telegram_connect import candidate_chat
from monitor import SafeError


class ConnectTests(unittest.TestCase):
    def message(self, chat=123, text='/start', date=100):
        return {'message':{'chat':{'type':'private','id':chat},'from':{'id':chat,'is_bot':False},'date':date,'text':text}}

    def test_one_unique_recent_sender(self):
        self.assertEqual(candidate_chat([self.message(),self.message()],101),123)

    def test_ambiguous_or_stale_or_not_start(self):
        for messages in [[self.message(),self.message(456)], [self.message(date=1)], [self.message(text='hello')]]:
            with self.assertRaises(SafeError):candidate_chat(messages,90000)
