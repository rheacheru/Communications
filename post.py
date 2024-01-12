import json
import time
import requests
from jwt import JWT, jwk_from_pem
from datetime import datetime
import sys
from pathlib import Path

# Load your service account credentials
with open('ihscubesat-c9dc08a671e1.json', 'r') as f:
    sa_credentials = json.load(f)

# Prepare the JWT Claims
iat = time.time()
exp = iat + 3600

filepath = sys.argv[1]
filename = Path(filepath).name

payload = {
    'iss': sa_credentials['client_email'],
    'sub': sa_credentials['client_email'],
    'aud': 'https://oauth2.googleapis.com/token',
    'iat': iat,
    'exp': exp,
    'scope': 'https://www.googleapis.com/auth/drive.file'
}

# Sign the JWT
jwt_instance = JWT()
#private_key = jwk_from_dict(sa_credentials['private_key'])
private_key = jwk_from_pem(bytes(sa_credentials['private_key'], 'utf-8'))
signed_jwt = jwt_instance.encode(payload, private_key, 'RS256')

# Get the access token
token_response = requests.post(
    'https://oauth2.googleapis.com/token',
    headers={'Content-Type': 'application/x-www-form-urlencoded'},
    data={
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'assertion': signed_jwt
    }
)


access_token = token_response.json().get('access_token')

# Upload the file to Google Drive
headers = {
    "Authorization": "Bearer " + access_token
}

metadata = {
    'name': filename,
    'parents': ['1MTX5s9TRgT2vM9C_C2a_PbIkOMk3YSLR']
}

with open(filepath, 'rb') as fstream:
    filedata = fstream.read()

files = {
    'data': ('metadata', json.dumps(metadata), 'application/json; charset=UTF-8'),
    'file': filedata #update this
}

response = requests.post(
    'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart',
    headers=headers,
    files=files
)


print(response.text)