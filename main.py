from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from dm_bot import start_dm_campaign, fetch_dm_replies

app = FastAPI()

# Allow CORS from frontend domain
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

# Campaign request payload
class CampaignRequest(BaseModel):
    campaignName: str
    slackCookie: str
    profileUrls: List[str]
    messageTemplate: str
    delayBetweenMessages: int
    maxMessagesPerDay: int

# Endpoint to start sending DMs
@app.post("/api/create-campaign")
async def create_campaign(data: CampaignRequest):
    try:
        result = start_dm_campaign(
            data.campaignName,
            data.slackCookie,
            data.profileUrls,
            data.messageTemplate,
            data.delayBetweenMessages,
            data.maxMessagesPerDay
        )
        return {"status": "done", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint to fetch replies
@app.get("/api/replies")
async def get_replies(slack_cookie: str):
    try:
        replies = fetch_dm_replies(slack_cookie)
        return {"replies": replies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
