# Tests run against the installed eidosxr package
# Install in development mode: pip install -e .

import pytest


@pytest.fixture(autouse=True)
def no_browser(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Stop show() opening a real browser tab.

    show() writes the spec to a temporary HTML file and hands it to
    webbrowser.open_new_tab, whose result it returns. A CI runner has no
    browser, so that returns False and the show() tests fail; locally every run
    opened tabs. Returns the URLs that would have been opened.
    """
    opened: list[str] = []

    def open_new_tab(url: str) -> bool:
        opened.append(url)
        return True

    monkeypatch.setattr("webbrowser.open_new_tab", open_new_tab)
    return opened
