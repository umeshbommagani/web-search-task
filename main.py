import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from urllib.parse import urljoin
import logging
import unittest
from unittest.mock import patch, MagicMock

logging.basicConfig(level=logging.INFO)


class WebCrawler:
    def __init__(self):
        self.index = defaultdict(str)
        self.visited = set()

    def crawl(self, url, base_url=None):
        if url in self.visited:
            return
        self.visited.add(url)

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            self.index[url] = soup.get_text(separator=" ", strip=True)

            for link in soup.find_all('a'):
                href = link.get('href')
                if href:
                    href = urljoin(base_url or url, href)
                    if href.startswith(base_url or url):
                        self.crawl(href, base_url=base_url or url)

        except requests.exceptions.RequestException as e:
            logging.error(f"Error crawling {url}: {e}")

    def search(self, keyword):
        results = []
        for url, text in self.index.items():
            if keyword.lower() in text.lower():
                results.append(url)
        return results

    def print_results(self, results):
        if results:
            print("Search results:")
            for result in results:
                print(f"- {result}")
        else:
            print("No results found.")


def main():
    crawler = WebCrawler()
    start_url = "https://example.com"
    crawler.crawl(start_url)
    keyword = "test"
    results = crawler.search(keyword)
    crawler.print_results(results)


class WebCrawlerTests(unittest.TestCase):
    @patch("requests.get")
    def test_crawl_success_with_internal_and_external_links(self, mock_get):
        sample_html = """
        <html><body>
            <h1>Welcome!</h1>
            <a href="/about">About Us</a>
            <a href="https://www.external.com">External Link</a>
        </body></html>
        """
        mock_response = MagicMock()
        mock_response.text = sample_html
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        crawler = WebCrawler()
        crawler.crawl("https://example.com")

        self.assertIn("https://example.com", crawler.index)
        self.assertIn("https://example.com/about", crawler.visited)
        self.assertNotIn("https://www.external.com", crawler.visited)

    @patch("requests.get")
    def test_crawl_with_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("Test Error")
        crawler = WebCrawler()
        crawler.crawl("https://example.com")
        self.assertIn("https://example.com", crawler.visited)
        self.assertNotIn("https://example.com", crawler.index)

    @patch("requests.get")
    def test_crawl_with_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        crawler = WebCrawler()
        crawler.crawl("https://example.com/404")
        self.assertIn("https://example.com/404", crawler.visited)
        self.assertNotIn("https://example.com/404", crawler.index)

    @patch("requests.get")
    def test_crawl_empty_page(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = "<html><body></body></html>"
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        crawler = WebCrawler()
        crawler.crawl("https://example.com")
        self.assertIn("https://example.com", crawler.index)
        self.assertEqual(crawler.index["https://example.com"], "")

    @patch("requests.get")
    def test_crawl_with_relative_and_absolute_links(self, mock_get):
        sample_html = """
        <html><body>
            <a href="/contact">Contact</a>
            <a href="https://example.com/help">Help</a>
        </body></html>
        """
        mock_response = MagicMock()
        mock_response.text = sample_html
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        crawler = WebCrawler()
        crawler.crawl("https://example.com")
        self.assertIn("https://example.com/contact", crawler.visited)
        self.assertIn("https://example.com/help", crawler.visited)

    @patch("requests.get")
    def test_crawl_with_duplicate_links(self, mock_get):
        sample_html = """
        <html><body>
            <a href="/about">About Us</a>
            <a href="/about">About Us Again</a>
        </body></html>
        """
        mock_response = MagicMock()
        mock_response.text = sample_html
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        crawler = WebCrawler()
        crawler.crawl("https://example.com")
        self.assertEqual(list(crawler.visited).count("https://example.com/about"), 1)

    def test_search_found_and_not_found(self):
        crawler = WebCrawler()
        crawler.index["page1"] = "This has the keyword"
        crawler.index["page2"] = "No keyword here"
        results = crawler.search("keyword")
        self.assertEqual(sorted(results), ["page1", "page2"])
        results = crawler.search("missing")
        self.assertEqual(results, [])

    def test_search_with_empty_keyword(self):
        crawler = WebCrawler()
        crawler.index["page1"] = "Some text"
        crawler.index["page2"] = "Another page"
        results = crawler.search("")
        self.assertEqual(sorted(results), ["page1", "page2"])

    @patch("requests.get")
    def test_recursive_crawl_multiple_levels(self, mock_get):
        html_root = """
        <html><body>
            <a href="/level1">Level 1</a>
        </body></html>
        """
        html_level1 = """
        <html><body>
            <a href="/level2">Level 2</a>
        </body></html>
        """
        html_level2 = "<html><body><p>Deep content</p></body></html>"

        def side_effect(url, timeout=5):
            resp = MagicMock()
            resp.status_code = 200
            if url.endswith("/level1"):
                resp.text = html_level1
            elif url.endswith("/level2"):
                resp.text = html_level2
            else:
                resp.text = html_root
            return resp

        mock_get.side_effect = side_effect
        crawler = WebCrawler()
        crawler.crawl("https://example.com")
        self.assertIn("https://example.com/level1", crawler.visited)
        self.assertIn("https://example.com/level2", crawler.visited)
        self.assertIn("Deep content", crawler.index["https://example.com/level2"])

    @patch("sys.stdout.write")
    def test_print_results_with_and_without_results(self, mock_stdout):
        crawler = WebCrawler()
        crawler.print_results(["https://test.com"])
        output = "".join(call.args[0] for call in mock_stdout.call_args_list)
        self.assertIn("Search results:", output)
        self.assertIn("https://test.com", output)
        mock_stdout.reset_mock()
        crawler.print_results([])
        output = "".join(call.args[0] for call in mock_stdout.call_args_list)
        self.assertIn("No results found.", output)


if __name__ == "__main__":
    unittest.main(exit=False)
    main()
