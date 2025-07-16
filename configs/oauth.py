from authlib.integrations.starlette_client import OAuth
from config import settings

oauth = OAuth()

oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    api_base_url="https://openidconnect.googleapis.com/v1/",   
    client_kwargs={"scope": "openid email profile"},
)
