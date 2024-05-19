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
from adafruit_datetime import datetime
import traceback
from comms import file_receive
import os


CS = digitalio.DigitalInOut(board.D20)
CS.switch_to_output(True)
RST = digitalio.DigitalInOut(board.D21)
RST.switch_to_output(True)
print('hello')

RADIO_FREQ_MHZ = 437.4
node = const(0xfb)
destination = const(0xfa)

rfm9x = pycubed_rfm9x.RFM9x(board.SPI(), CS, RST, 437.4)
rfm9x.spreading_factor = 8
rfm9x.node = node
rfm9x.destination = destination

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



pool = attempt_wifi()
while True:
    try:
        print('Waiting for messages....')
        packet = rfm9x.receive(timeout=10)
        if packet is None:
            continue
        filepath =f'received_telemetry/{datetime.now().isoformat()}.txt'
        with open(filepath, 'w') as f:
            f.write(packet)
        rfm9x.send("IRVCB")

        packet = rfm9x.receive(timeout=10)
        size = int.from_bytes(packet[1:5], 'little')
        print(size)
        packet_count = (size-1)//244+1
        image_name = datetime.now().isoformat()
        folder_path = f"received_images/{image_name}"
        os.mkdir(folder_path)
        with open(f"{folder_path}/packet_0.raw","wb") as f:
            f.write(packet[5:])
        count = 1
        request_packet_list = [0]*packet_count # 0 for not received correctly, 1 for received correctly

        while count < packet_count:
            packet = rfm9x.receive(timeout=10)
            if chr(packet[0]) == '1' and len(packet) == 249:
                packet_number = int.from_bytes(packet[1:5], 'little')
                with open(f"{folder_path}/packet_{packet_number}.raw","wb") as f:
                    f.write(packet[5:])
                request_packet_list[packet_number] = 1
                count += 1
            elif len(packet) < 249:
                print("wrong length")
                with open(f"corrupted/{datetime.now().isoformat()}.raw","w") as f:
                    f.write(packet)
            else:
                print("not 1 at beginning")
                with open(f"corrupted/{datetime.now().isoformat()}.raw","w") as f:
                    f.write(packet)

    except Exception as e:
        print("Error in Main Loop: " + ''.join(traceback.format_exception(e)))







