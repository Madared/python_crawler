import respx
from typer.testing import CliRunner

from crawler.cli import app

runner = CliRunner()


class TestCli:
    def test_help_output(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.stdout
        assert "URL" in result.stdout

    def test_missing_required_argument(self):
        result = runner.invoke(app, [])
        assert result.exit_code != 0
        assert "Missing argument" in result.stderr

    def test_invalid_url_format(self):
        result = runner.invoke(app, ["not-a-valid-url"])
        assert result.exit_code == 2
        assert "Invalid URL" in result.stderr

    def test_all_option_defaults(self):
        with respx.mock:
            respx.get("https://example.com/robots.txt").respond(200, text="")
            respx.get("https://example.com/").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )
            result = runner.invoke(app, ["https://example.com"])
            assert result.exit_code == 0
            assert "Crawl complete" in result.stdout

    def test_option_parsing(self):
        with respx.mock:
            respx.get("https://example.com/robots.txt").respond(200, text="")
            respx.get("https://example.com/").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )
            result = runner.invoke(
                app,
                [
                    "https://example.com",
                    "--concurrency",
                    "5",
                    "--max-pages",
                    "20",
                    "--delay",
                    "1.0",
                    "--verbose",
                ],
            )
            assert result.exit_code == 0

    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "crawler" in result.stdout
        assert "0.1.0" in result.stdout
