import os

#twilio
twilio_account_sid = os.environ['twilio_account_sid']
twilio_auth_token = os.environ['twilio_auth_token']

# Google
GOOGLE_CLIENT_CONFIG = {
    "web":
        {
            "client_id":os.environ['ccpa_google_client_id'],
            "client_secret":os.environ['ccpa_google_client_secret'],
            "project_id":"ccpa-394520",
            "auth_uri":"https://accounts.google.com/o/oauth2/auth",
            "token_uri":"https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris":
                [
                    "https://127.0.0.1:5000/oauth2callback"
                ]
            }
        }