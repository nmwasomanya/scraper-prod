import unittest
import os
import sys

# Adjust path so we can import 'email_crawler' as a package
sys.path.append(os.path.join(os.getcwd(), 'email_crawler'))

from email_crawler.utils.email_utils import EmailUtils

class TestEmailUtils(unittest.TestCase):
    def setUp(self):
        self.skip_rules = {
            "skip_domain_extensions": [".edu"],
            "skip_email_prefixes": ["noreply@"],
            "skip_email_domains": ["test.com"],
            "skip_email_patterns": ["user@"]
        }
        self.utils = EmailUtils(self.skip_rules)

    def test_extract_emails(self):
        text = "Contact us at info@example.com or support [at] domain [dot] com."
        emails = self.utils.extract_emails(text)
        self.assertIn("info@example.com", emails)
        self.assertIn("support@domain.com", emails)

    def test_extract_facebook(self):
        text = "Visit our page at https://www.facebook.com/mycompany and https://fb.com/short."
        fbs = self.utils.extract_facebook_urls(text)
        self.assertIn("https://www.facebook.com/mycompany", fbs)
        self.assertIn("https://fb.com/short", fbs)

    def test_normalize_facebook(self):
        url = "https://m.facebook.com/page/?ref=bookmarks"
        normalized = self.utils.normalize_facebook_url(url)
        self.assertEqual(normalized, "https://www.facebook.com/page")

    def test_should_skip(self):
        self.assertTrue(self.utils.should_skip("noreply@example.com")[0])
        self.assertTrue(self.utils.should_skip("student@college.edu")[0])
        self.assertTrue(self.utils.should_skip("someone@test.com")[0])
        self.assertFalse(self.utils.should_skip("contact@valid.com")[0])

    def test_valid_syntax(self):
        self.assertTrue(self.utils.is_valid_syntax("test@example.com"))
        self.assertFalse(self.utils.is_valid_syntax("test@"))

if __name__ == '__main__':
    unittest.main()
