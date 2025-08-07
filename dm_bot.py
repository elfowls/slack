from playwright.sync_api import sync_playwright
import time

def start_dm_campaign(name, cookie, profiles, message, delay, limit):
    sent = 0
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_cookies(parse_cookie_string(cookie))
        page = context.new_page()

        for profile_url in profiles:
            if sent >= limit:
                break
            try:
                page.goto(profile_url)
                page.wait_for_timeout(3000)

                dm_button = page.query_selector('button:has-text("Message")')
                if dm_button:
                    dm_button.click()
                    page.wait_for_timeout(1000)
                    page.keyboard.type(message)
                    page.keyboard.press("Enter")
                    sent += 1
                    results.append({"url": profile_url, "status": "sent"})
                    time.sleep(delay)
                else:
                    results.append({"url": profile_url, "status": "dm_button_not_found"})
            except Exception as e:
                results.append({"url": profile_url, "status": "error", "error": str(e)})

        browser.close()

    return {"sent": sent, "results": results}

def fetch_dm_replies(cookie):
    replies = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_cookies(parse_cookie_string(cookie))
        page = context.new_page()

        page.goto("https://app.slack.com/client")
        page.wait_for_timeout(5000)

        threads = page.query_selector_all('div.c-virtual_list__item')
        for thread in threads[:10]:
            try:
                content = thread.inner_text()
                if "replied" in content.lower():
                    replies.append({"message": content})
            except:
                continue

        browser.close()
    return replies

def parse_cookie_string(cookie_string):
    cookies = []
    for pair in cookie_string.split(';'):
        if '=' in pair:
            name, value = pair.strip().split('=', 1)
            cookies.append({"name": name, "value": value, "domain": ".slack.com", "path": "/"})
    return cookies
