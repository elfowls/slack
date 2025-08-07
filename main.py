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
