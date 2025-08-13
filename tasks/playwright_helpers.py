# tasks/playwright_helpers.py
from playwright.async_api import Page, expect, TimeoutError
import asyncio

LOGIN_URL = "https://www.linkedin.com/login"

async def ensure_logged_in(page: Page, email: str, password: str) -> None:
    # fast path: already authenticated
    await page.goto("https://www.linkedin.com/feed/")
    if "feed" in page.url:
        return

    # slow path: log in
    await page.goto(LOGIN_URL)
    await page.fill('input[name="session_key"]', email)
    await page.fill('input[name="session_password"]', password)
    await page.click('button[type="submit"]')

    # LinkedIn may pop captcha or 2FA → quick robustness
    try:
        await page.wait_for_url("*feed*", timeout=10_000)
    except TimeoutError:
        raise RuntimeError("LinkedIn login failed – check credentials / 2-FA")
