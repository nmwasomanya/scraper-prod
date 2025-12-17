import re
import dns.resolver
from email_validator import validate_email, EmailNotValidError
from urllib.parse import urlparse, unquote
from typing import Set, Tuple, Optional, Dict, List

class EmailUtils:
    def __init__(self, skip_rules: Optional[Dict[str, List[str]]] = None):
        self.skip_rules = skip_rules or {}

    def extract_emails(self, text: str) -> Set[str]:
        """Extracts emails from text, including some obfuscations."""
        if not text:
            return set()

        # Standard email regex
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

        # Obfuscated patterns like "info [at] domain dot com"
        normalized_text = text.replace(' [at] ', '@').replace(' (at) ', '@').replace(' at ', '@')
        normalized_text = normalized_text.replace(' [dot] ', '.').replace(' (dot) ', '.').replace(' dot ', '.')

        candidates = set(re.findall(email_pattern, normalized_text))

        return {email.lower() for email in candidates}

    def extract_facebook_urls(self, text: str) -> Set[str]:
        """Extracts Facebook URLs."""
        if not text:
            return set()

        fb_pattern = r'https?://(?:www\.|m\.)?(?:facebook\.com|fb\.com)/[^"\s\'<>]+'

        raw_links = re.findall(fb_pattern, text)

        valid_links = set()
        for link in raw_links:
            # Clean up trailing punctuation
            link = link.rstrip('.,;!?>)]}')
            valid_links.add(link)

        return valid_links

    def normalize_facebook_url(self, url: str) -> str:
        """Normalizes Facebook URL."""
        try:
            parsed = urlparse(url)

            scheme = "https"
            netloc = parsed.netloc.lower().replace("m.facebook.com", "facebook.com").replace("fb.com", "facebook.com")
            if not netloc.startswith("www.") and netloc == "facebook.com":
                netloc = "www.facebook.com"

            path = parsed.path
            if path.endswith('/'):
                path = path[:-1]

            query = parsed.query
            if "id=" in query:
                pass
            else:
                query = ""

            return f"{scheme}://{netloc}{path}{'?' + query if query else ''}"
        except:
            return url

    def is_valid_syntax(self, email: str) -> bool:
        """Validates email syntax."""
        try:
            validate_email(email, check_deliverability=False)
            return True
        except EmailNotValidError:
            return False

    def check_mx_record(self, email: str) -> bool:
        """Checks MX record for the email domain."""
        try:
            domain = email.split('@')[-1]
            records = dns.resolver.resolve(domain, 'MX')
            return bool(records)
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout, Exception):
            return False

    def should_skip(self, email: str) -> Tuple[bool, Optional[str]]:
        """Checks if email should be skipped based on rules."""
        if not self.skip_rules:
            return False, None

        email = email.lower()
        if '@' not in email:
            return True, "Invalid format"

        local_part, domain = email.split('@')

        # Check domain extensions
        for ext in self.skip_rules.get("skip_domain_extensions", []):
            if domain.endswith(ext):
                return True, f"Domain extension {ext}"

        # Check email prefixes
        for prefix in self.skip_rules.get("skip_email_prefixes", []):
            if email.startswith(prefix):
                 return True, f"Prefix {prefix}"

        # Check email domains
        if domain in self.skip_rules.get("skip_email_domains", []):
            return True, f"Domain {domain}"

        # Check email patterns
        for pattern in self.skip_rules.get("skip_email_patterns", []):
            if pattern in email:
                 if pattern.endswith('@') and email.startswith(pattern):
                     return True, f"Pattern {pattern}"
                 elif pattern in email:
                     pass

        return False, None
