"""Optional YouTube/Facebook publishing helpers.
Credentials are read from environment variables/files and are never stored in source code.
"""
import os
from pathlib import Path


def youtube_upload(video_path: str, title: str, description: str = "", tags=None, privacy="private"):
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.auth.transport.requests import Request
    import pickle

    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    client_file = Path(os.getenv("YOUTUBE_CLIENT_SECRETS", "client_secrets.json"))
    token_file = Path(os.getenv("YOUTUBE_TOKEN", "token.pickle"))
    if not client_file.exists():
        raise FileNotFoundError("ضع client_secrets.json من Google Cloud في مجلد المشروع.")

    credentials = None
    if token_file.exists():
        with token_file.open("rb") as f:
            credentials = pickle.load(f)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_file), scopes)
            credentials = flow.run_local_server(port=0)
        with token_file.open("wb") as f:
            pickle.dump(credentials, f)

    youtube = build("youtube", "v3", credentials=credentials)
    body = {"snippet": {"title": title, "description": description, "tags": tags or []},
            "status": {"privacyStatus": privacy}}
    request = youtube.videos().insert(
        part="snippet,status", body=body,
        media_body=MediaFileUpload(video_path, mimetype="video/mp4", resumable=True))
    response = request.execute()
    return f"https://www.youtube.com/watch?v={response['id']}"


def facebook_upload(video_path: str, title: str, description: str = ""):
    import requests
    page_id = os.getenv("FACEBOOK_PAGE_ID")
    token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
    if not page_id or not token:
        raise RuntimeError("ضع FACEBOOK_PAGE_ID و FACEBOOK_PAGE_ACCESS_TOKEN في متغيرات البيئة.")
    url = f"https://graph-video.facebook.com/v23.0/{page_id}/videos"
    with open(video_path, "rb") as video:
        response = requests.post(
            url,
            params={"access_token": token, "title": title, "description": description},
            files={"source": (Path(video_path).name, video, "video/mp4")},
            timeout=300,
        )
    response.raise_for_status()
    return response.json()
