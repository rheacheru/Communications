# Write your code here :-)
import pycubed_rfm9x
import board
import digitalio
import busio
import time
import wifi
from secrets import secrets
import socketpool
import adafruit_requests
import rtc
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import ssl
from datetime import datetime

CS = digitalio.DigitalInOut(board.D12)
CS.switch_to_output(True)
RST = digitalio.DigitalInOut(board.D13)
RST.switch_to_output(True)
print('hello')

RADIO_FREQ_MHZ = 437.4
node = const(0xfb)
destination = const(0xfa)

rfm9x = pycubed_rfm9x.RFM9x(board.SPI(), CS, RST, 437.4)
rfm9x.spreading_factor = 8
rfm9x.node = node
rfm9x.destination = destination
def main1():
    while True:
        packet = rfm9x.receive(timeout=10)
        #print('hi')
        if packet is not None:
            print(packet)
            print(rfm9x.last_rssi)

        

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
        current_time = json1['datetime']
        the_date, the_time = current_time.split('T')
        year, month, mday = [int(x) for x in the_date.split('-')]
        the_time = the_time.split('.')[0]
        hours, minutes, seconds = [int(x) for x in the_time.split(':')]

        # We can also fill in these extra nice things
        year_day = json1['day_of_year']
        week_day = json1['day_of_week']
        is_dst = json1['dst']

        now = time.struct_time(
            (year, month, mday, hours, minutes, seconds, week_day, year_day, is_dst))
        the_rtc.datetime = now
    except Exception as e:
        print('[WARNING]', e)



def main2():
    pool = attempt_wifi()
    print('in main2')
    while True:
        packet = rfm9x.receive(timeout=10)
        if packet is None:
            continue
        now = datetime.now()
        current_time = now.strftime("%Y%M%D%H%M%S")
        path =f'received_images/{current_time}.jpg'
        print(path)
        size = int.from_bytes(packet, 'big')
        print(size)
        with open(path, "wb+") as stream:
            count = 0
            rssi = 0
            while count < size:
                data = rfm9x.receive(timeout=10)
                rssi = rssi + rfm9x.last_rssi
                stream.write(data)
                count = count + 249
                print('done')
        print('saved image')
        print(f'avg rssi: {rssi//((count//249)+1)}')


main2()




