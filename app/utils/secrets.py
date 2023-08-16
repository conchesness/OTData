import os

def getSecrets():
    secrets = {
        'MONGO_HOST':f"{os.environ.get('mongodb_host')}/ccpa?retryWrites=true&w=majority",
        'MONGO_DB_NAME':'ccpa',
        'GOOGLE_CLIENT_ID': os.environ['ccpa_google_client_id'],
        'GOOGLE_CLIENT_SECRET':os.environ['ccpa_google_client_secret'],
        'GOOGLE_DISCOVERY_URL':"https://accounts.google.com/.well-known/openid-configuration",
        'twilio_account_sid':os.environ['twilio_account_sid'],
        'twilio_auth_token':os.environ['twilio_auth_token']
        }
    return secrets