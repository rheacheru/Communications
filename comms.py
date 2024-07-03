import json
import time
import adafruit_requests
#from adafruit_jwt import JWT
from secrets import secrets
import wifi 
import socketpool
import rtc
import ssl

def attempt_wifi():
    # TODO: Move wifi pass and id to config
    # try connecting to wifi
    print("Connecting to WiFi...")
    try:
        wifi.radio.connect(ssid=secrets["wifi"]["ssid"], password=secrets["wifi"]["password"])
        # wifi.radio.connect(ssid="Stanford") # open network
        print("Signal: {}".format(wifi.radio.ap_info.rssi))
        # Create a socket pool
        pool = socketpool.SocketPool(wifi.radio)
        # sync out RTC from the web
        synctime(pool)
    except Exception as e:
        print("Unable to connect to WiFi: {}".format(e))
        return None
    else:
        return pool  


def synctime(pool):
    try:
        requests = adafruit_requests.Session(pool)
        TIME_API = "http://worldtimeapi.org/api/ip"
        the_rtc = rtc.RTC()
        response = None
        while True:
            try:
                print("Fetching time")
                # print("Fetching json from", TIME_API)
                response = requests.get(TIME_API)
                break
            except (ValueError, RuntimeError) as e:
                print("Failed to get data, retrying\n", e)
                continue

        json1 = response.json()
        print(json1)
        now = time.localtime(json1['unixtime'])
        the_rtc.datetime = now
    except Exception as e:
        print('[WARNING]', e) 
    
'''def post_image(filepath, pool):
    synctime(pool)
    with open('ihscubesat-c9dc08a671e1.json', 'r') as f:
        sa_credentials = json.load(f)
    # Prepare the JWT Claims
    iat = time.time()
    exp = iat + 300
    filepath = filepath
    filename = filepath.split('/')[-1]
    payload = {
        'iss': sa_credentials['client_email'],
        'sub': sa_credentials['client_email'],
        'aud': 'https://oauth2.googleapis.com/token',
        'iat': iat,
        'exp': exp,
        'scope': 'https://www.googleapis.com/auth/drive.file'
    }
    #convert to bytes
    signed_jwt = JWT.generate(payload, secrets['google_private_key'], 'RS256')
    # Get the access token
    ssl_context = ssl.create_default_context()  #added ssl context here
    requests = adafruit_requests.Session(pool,ssl_context)
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
        "Authorization": f'Bearer {access_token}'
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
        url = 'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart',
        headers=headers,
        data=files
    )
    print(response.text)'''


def file_receive(filepath, size, rfm9x):
    with open(filepath, "wb+") as stream:
            count = 0
            rssi = 0
            while count < size:
                data = rfm9x.receive(timeout=10)
                rssi = rssi + rfm9x.last_rssi
                stream.write(data)
                count = count + 249
                print('done')
    print(f'saved image, avg rssi: {rssi//((count//249)+1)}')


#pool = attempt_wifi()
#filepath = 'received_images/THBBlueEarthTest.jpeg'
#post_image(filepath, pool)
