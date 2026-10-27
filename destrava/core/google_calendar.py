import os
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CREDENTIALS_PATH = "credentials.json"
TOKEN_PATH = "token.json"


def get_calendar_service():
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH,
                SCOPES,
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def get_events(start: datetime, end: datetime) -> list[dict]:
    service = get_calendar_service()

    response = service.events().list(
        calendarId="primary",
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events: list[dict] = []

    for event in response.get("items", []):
        event_start = event.get("start", {}).get("dateTime")
        event_end = event.get("end", {}).get("dateTime")

        if not event_start or not event_end:
            continue

        events.append(
            {
                "id": event.get("id", ""),
                "title": event.get("summary", "Compromisso"),
                "start": datetime.fromisoformat(
                    event_start.replace("Z", "+00:00")
                ),
                "end": datetime.fromisoformat(
                    event_end.replace("Z", "+00:00")
                ),
                "type": "event",
            }
        )

    return events
