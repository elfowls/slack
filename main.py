# FastAPI Backend to Send and Receive Slack DMs (with Supabase Account Storage)

---

## 📁 `main.py`

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from celery import Celery
from dm_bot import start_dm_campaign, fetch_dm_replies
import os
from supabase import create_client, Client
from cryptography.fernet import Fernet

app = FastAPI()

origins = [
    "https://slack-outreach-buddy.lovable.app",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

celery = Celery("worker", broker="redis://localhost:6379/0")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
FERNET_KEY = os.getenv("FERNET_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
fernet = Fernet(FERNET_KEY)

class CampaignRequest(BaseModel):
    campaignName: str
    accountIds: List[str]
    profileUrls: List[str]
    messageTemplate: str
    delayBetweenMessages: int
    maxMessagesPerDay: int

class AccountRequest(BaseModel):
    accountName: str
    workspace: str
    dailyLimit: int
    slackCookie: str
    user_id: str

@app.post("/api/create-campaign")
async def create_campaign(data: CampaignRequest):
    for account_id in data.accountIds:
        result = supabase.table("slack_accounts").select("encrypted_cookie").eq("id", account_id).single().execute()
        if result.data:
            decrypted_cookie = fernet.decrypt(result.data['encrypted_cookie'].encode()).decode()
            task = send_dms.delay(
                data.campaignName,
                decrypted_cookie,
                data.profileUrls,
                data.messageTemplate,
                data.delayBetweenMessages,
                data.maxMessagesPerDay
            )
    return {"status": "queued"}

@app.post("/api/add-account")
async def add_account(account: AccountRequest):
    encrypted_cookie = fernet.encrypt(account.slackCookie.encode()).decode()
    result = supabase.table("slack_accounts").insert({
        "user_id": account.user_id,
        "account_name": account.accountName,
        "workspace_name": account.workspace,
        "daily_limit": account.dailyLimit,
        "encrypted_cookie": encrypted_cookie
    }).execute()
    return {"status": "account added", "data": result.data}

@app.get("/api/replies")
async def get_replies(slack_cookie: str):
    try:
        replies = fetch_dm_replies(slack_cookie)
        return {"replies": replies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@celery.task
def send_dms(campaign_name, cookie, profiles, message, delay, limit):
    return start_dm_campaign(campaign_name, cookie, profiles, message, delay, limit)
```

---

## 📁 `dm_bot.py`

```python
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
```

---

## ✅ Summary
- ✅ Slack accounts now stored securely in Supabase (with Fernet encryption)
- ✅ Campaigns can pull encrypted cookies by `account_id`
- ✅ Ready to connect to your Supabase UI

Let me know if you want to add message history logging or campaign stats next.
