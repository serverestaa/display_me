from urllib.parse import quote_plus
from playwright.async_api import TimeoutError, Page

EASY_APPLY_SELECTOR = 'button:has-text("Easy Apply")'
RESULT_ITEM        = "div.jobs-search-results-list li.jobs-search-results__list-item"
NO_RESULTS_BANNER  = "div.jobs-search-no-results-banner"

async def find_easy_apply_jobs(page: Page, title: str, limit: int = 20):
    search_url = (
        "https://www.linkedin.com/jobs/search/"
        f"?keywords={quote_plus(title)}&f_AL=true&origin=JOB_SEARCH_PAGE_JOB_FILTER"
    )

    await page.goto(search_url, timeout=60_000)
    await page.wait_for_load_state("networkidle")

    # cookie banner on fresh profiles
    if await page.is_visible('button:has-text("Accept cookies")'):
        await page.click('button:has-text("Accept cookies")')

    # bounced back to login?
    if page.url.startswith("https://www.linkedin.com/login"):
        raise RuntimeError("LinkedIn session lost – re-login required.")

    try:
        await page.wait_for_selector(f"{RESULT_ITEM}, {NO_RESULTS_BANNER}", timeout=30_000)
    except TimeoutError:
        raise RuntimeError("Job list failed to load (markup shift or connectivity).")

    # no results?
    if await page.is_visible(NO_RESULTS_BANNER):
        return []

    # infinite-scroll until we have enough or bottom reached
    jobs = []
    seen = set()

    while len(jobs) < limit:
        for li in await page.locator(RESULT_ITEM).all():
            url  = await li.locator("a").first.get_attribute("href")
            if url in seen:
                continue
            seen.add(url)
            if not await li.locator(EASY_APPLY_SELECTOR).count():
                continue
            title_txt = await li.locator("span[dir='ltr']").first.inner_text()
            desc      = await li.locator("p").first.inner_text()
            jobs.append({"url": url, "title": title_txt, "description": desc})
            if len(jobs) >= limit:
                break

        # scroll a bit to trigger lazy loading; if nothing new, break
        prev_count = await page.locator(RESULT_ITEM).count()
        await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1500)
        if await page.locator(RESULT_ITEM).count() == prev_count:
            break

    return jobs[:limit]



async def apply_to_job(page, job, pdf_path, cover_letter: str):
    await page.goto(job["url"])
    if not await page.is_visible(EASY_APPLY_SELECTOR):
        return False              # not Easy Apply anymore
    await page.click(EASY_APPLY_SELECTOR)
    # Step wizard
    while True:
        # attach resume
        if await page.is_visible('input[type="file"]'):
            await page.set_input_files('input[type="file"]', pdf_path)
        # cover letter textbox
        if await page.is_visible('textarea'):
            await page.fill('textarea', cover_letter)
        # next / review / submit
        if await page.is_visible('button:has-text("Submit application")'):
            await page.click('button:has-text("Submit application")')
            await page.wait_for_timeout(1500)
            return True
        if await page.is_visible('button:has-text("Next")'):
            await page.click('button:has-text("Next")')
            continue
        # unknown step → bail
        await page.click('button[aria-label="Dismiss"]')
        return False
