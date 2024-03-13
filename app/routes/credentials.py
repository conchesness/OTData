import os

GOOGLE_CLIENT_CONFIG = {
    "web":
        {
            #"client_id":"437821053979-v4ar9ic6q1m21r8ig717apnuc37e4lps.apps.googleusercontent.com",
            "client_id":os.environ['otdata_google_client_id'],
            #"client_secret":"-uN11iQvJ9-vrsUkIVtL4eiD",
            "client_secret":os.environ['otdata_google_client_secret'],
            "project_id":"otdata-280023",
            "auth_uri":"https://accounts.google.com/o/oauth2/auth",
            "token_uri":"https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris":
                [
                    "https://127.0.0.1:5000/oauth2callback",
                    "https://otdata.hsoakland.tech/oauth2callback"
                ]
            }
        }