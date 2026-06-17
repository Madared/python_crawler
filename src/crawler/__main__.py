import typer

app = typer.Typer()


@app.command()
def crawl(url: str):
    """Crawl a web page and extract information."""
    typer.echo(f"Crawling: {url}")


def main():
    app()


if __name__ == "__main__":
    main()
