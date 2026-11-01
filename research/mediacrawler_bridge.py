"""Run in MediaCrawler's own environment, never in the web application's environment."""
import asyncio
import os
from pathlib import Path
import sys


def run():
    upstream = Path(os.environ['MEDIACRAWLER_HOME']).resolve()
    os.chdir(upstream)
    sys.path.insert(0, str(upstream))
    # Use Playwright's isolated Chromium even when upstream requests system Chrome.
    from playwright.async_api import BrowserType
    original_launch = BrowserType.launch
    original_persistent = BrowserType.launch_persistent_context

    async def launch(browser, *args, **kwargs):
        kwargs['channel'] = os.getenv('JINGXU_BROWSER_CHANNEL', 'chromium')
        return await original_launch(browser, *args, **kwargs)

    async def persistent(browser, *args, **kwargs):
        kwargs['channel'] = os.getenv('JINGXU_BROWSER_CHANNEL', 'chromium')
        return await original_persistent(browser, *args, **kwargs)

    BrowserType.launch = launch
    BrowserType.launch_persistent_context = persistent
    import config
    platform = os.environ['JINGXU_PLATFORM']
    config.PLATFORM = platform
    config.KEYWORDS = os.environ['JINGXU_KEYWORDS']
    config.CRAWLER_TYPE = 'search'
    interactive = os.getenv('JINGXU_INTERACTIVE_LOGIN') == '1'
    config.LOGIN_TYPE = 'qrcode' if interactive else 'cookie'
    config.COOKIES = os.getenv('MEDIACRAWLER_' + platform.upper() + '_COOKIE', '')
    config.HEADLESS = not interactive
    config.ENABLE_CDP_MODE = False
    config.CDP_CONNECT_EXISTING = False
    config.SAVE_LOGIN_STATE = interactive
    config.SAVE_DATA_OPTION = 'json'
    config.SAVE_DATA_PATH = os.environ['JINGXU_RAW_DIR']
    config.CRAWLER_MAX_NOTES_COUNT = 5
    config.MAX_CONCURRENCY_NUM = 1
    config.ENABLE_GET_COMMENTS = False
    config.ENABLE_GET_SUB_COMMENTS = False
    config.ENABLE_GET_MEDIA = False
    config.ENABLE_GET_WORDCLOUD = False
    config.ENABLE_IP_PROXY = False
    config.CRAWLER_MAX_SLEEP_SEC = 5
    # Supply no extra CLI arguments: upstream defaults read the config above.
    sys.argv = [str(upstream / 'main.py')]
    import main

    async def collect():
        try:
            await main.main()
        finally:
            await main.async_cleanup()
    asyncio.run(collect())


if __name__ == '__main__':
    try:
        run()
    except Exception as exc:
        # Record only the error type, never upstream exception text or login data.
        status_path = os.getenv('JINGXU_ERROR_TYPE_FILE')
        if status_path:
            Path(status_path).write_text(type(exc).__name__, encoding='utf-8')
        raise SystemExit(1)
