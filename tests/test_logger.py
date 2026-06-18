from crawler.crawler._logger import CrawlLogger
from crawler.frontier import FrontierStats


class TestCrawlLogger:
    def test_print_summary_no_failures(self, capsys):
        stats = FrontierStats(discovered=5, visited=5, failed=0)
        CrawlLogger.print_summary(stats)
        assert capsys.readouterr().out.strip() == "Crawl complete: 5 pages"

    def test_print_summary_with_failures(self, capsys):
        stats = FrontierStats(discovered=10, visited=8, failed=2)
        CrawlLogger.print_summary(stats)
        assert capsys.readouterr().out.strip() == "Crawl complete: 8 pages, 2 failed"

    def test_page_fetched_with_error(self, capsys):
        logger = CrawlLogger(verbose=False)
        logger.page_fetched(0, "https://example.com/broken", [], "Connection refused")
        err = capsys.readouterr().err
        assert "ERROR" in err
        assert "https://example.com/broken" in err
        assert "Connection refused" in err

    def test_page_fetched_success_verbose(self, capsys):
        logger = CrawlLogger(verbose=True)
        logger.page_fetched(200, "https://example.com/", ["/page1"], None)
        out = capsys.readouterr().out
        assert "200 https://example.com/" in out
        assert "/page1" in out

    def test_page_fetched_success_non_verbose(self, capsys):
        logger = CrawlLogger(verbose=False)
        logger.page_fetched(200, "https://example.com/", ["/page1"], None)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_progress_verbose(self, capsys):
        logger = CrawlLogger(verbose=True)
        stats = FrontierStats(discovered=5, visited=3, failed=1)
        logger.progress(stats)
        err = capsys.readouterr().err
        assert "3 visited" in err
        assert "5 discovered" in err
        assert "1 failed" in err

    def test_progress_non_verbose(self, capsys):
        logger = CrawlLogger(verbose=False)
        stats = FrontierStats(discovered=5, visited=3, failed=1)
        logger.progress(stats)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""
