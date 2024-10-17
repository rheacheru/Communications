# Write your code here :-)
import pycubed_rfm9x
import board
import digitalio
# import busio
import time
import wifi
from secrets import secrets
import socketpool
import adafruit_requests
import rtc
# import adafruit_minimqtt.adafruit_minimqtt as MQTT
# import ssl
from adafruit_datetime import datetime
import traceback
# from comms import file_receive
import os
import asyncio
import json
import adafruit_hashlib as hashlib


import radio_diagnostics
from icpacket import Packet
from new_comms_protocol.ptp import AsyncPacketTransferProtocol as APTP
from new_comms_protocol.ftp import FileTransferProtocol as FTP


def check_write_permissions():
	try:
		with open("write_permissions_test_file.txt", "w") as f:
			f.write("test")
	except OSError:
		raise OSError("Read-only filesystem. Change boot.py to remount with option 'False' and unplug/replug.")
	else:
		print("Write permissions confirmed.")
		os.remove("write_permissions_test_file.txt")

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

def verify_packet(packet, desired_type):
	# Verify that the packet has the desired type
	assert desired_type in Packet.packet_types, "Desired type is invalid"
	if packet.categorize() == desired_type:
		# print(f"Packet is of desired type {desired_type}")
		return True
	else:
		print(f"Packet is of undesired type {packet.categorize()}, not {desired_type}")
		return False


async def main():
    print("Irvington CubeSat's Ground Station")
    
   
    MAX_PAYLOAD_SIZE = 256 - 4 - 6  
    MAX_PAYLOAD_SIZE -= 1  # 245 bytes
    
    CHUNK_SIZE = MAX_PAYLOAD_SIZE - 2  
    
    settings_hash = [-1]  # hack to pass by reference
    

    CS = digitalio.DigitalInOut(board.D5)
    CS.switch_to_output(True)
    RST = digitalio.DigitalInOut(board.D6)
    RST.switch_to_output(True)
    
  
    RADIO_FREQ_MHZ = 437.4
    node = const(0xfb)
    destination = const(0xfa)
    
 
    radio = pycubed_rfm9x.RFM9x(board.SPI(), CS, RST, RADIO_FREQ_MHZ)
    radio.spreading_factor = 8
    radio.node = node
    radio.destination = destination
    radio.enable_crc = True
    
    ptp = APTP(radio, packet_size=MAX_PAYLOAD_SIZE, timeout=10, log=False, enable_padding=False)
    ftp = FTP(ptp, chunk_size=CHUNK_SIZE, log=True)
    
    radio_diagnostics.report_diagnostics(radio)
    
    check_write_permissions()
    
    if os.path.exists("persistent_data.txt"):
        try:
            with open("persistent_data.txt", "r") as f:
                images_aware = int(f.readline().strip())
                incomplete_images = list(map(int, f.readline().strip().split()))
                to_assemble = list(map(int, f.readline().strip().split()))
        except Exception as e:
            print(f"Error reading persistent data: {e}")
            images_aware = 0
            incomplete_images = []
            to_assemble = []
    else:
        images_aware = 0
        incomplete_images = []
        to_assemble = []
	try:
		
	
	def save_data():
		with open("persistent_data.txt", "w") as f:
				f.write(str(images_aware))
				f.write("\n")
				f.write(" ".join(map(str, incomplete_images)))
				f.write("\n")
				f.write(" ".join(map(str, to_assemble)))
	
	async def save_telemetry(payload):
		filename = datetime.now().isoformat().replace(':','-')
		filepath = f"received_telemetry/{filename}.txt"
		with open(filepath, 'w') as f:
			f.write(json.dumps(payload))

	async def load_settings(settings_hash):
		with open('camera_settings.json', 'rb') as file:
			settings = file.read()
			digest = hashlib.md5(file.read()).hexdigest()
			if digest != settings_hash[0]:
				settings_hash[0] = digest
				return json.loads(settings)
		return -1
		
	
	while True:
		try:
			print("Waiting for telemetry ping (handshake 1)")   
			packet = await ptp.receive_packet()
			if not verify_packet(packet, "handshake1"):
				await asyncio.sleep(1)
				continue
			
			print("Telemetry ping (handshake 1) received")
			print("TESTING: reporting telemetry")
			print(packet.payload[1])
			await save_telemetry(packet.payload[1])
			
			camera_settings = await load_settings(settings_hash)
			if isinstance(camera_settings, dict):
				print("camera settings updated")

			packet = Packet.make_handshake2(cam_settings=camera_settings) # can send new_timeout=T or take_picture=False
			await ptp.send_packet(packet)
			print("Handshake 2 sent")
			
			print("Waiting for handshake 3")
			packet = await ptp.receive_packet(timeout=40) # Increased timeout for taking image
			if not verify_packet(packet, "handshake3"):
				continue
			
			print("Handshake 3 received")
			image_count = packet.payload[1]
			print(f"CubeSat has taken {image_count} images so far")
			
			# Update persistent data
			if image_count > images_aware:
				new_images = list(range(images_aware, image_count))
				incomplete_images.extend(new_images)
				images_aware = image_count
					
			# Request incomplete images
			# To do: record reception time datetime.now().isoformat() and time taken
			while True:
				if images_aware-1 not in incomplete_images: # most recent already received
					break
				image_id = images_aware-1 # assume IDs are 0 to images_aware-1
				filename = f"image_{image_id}.jpeg"
				local_path = f"received_images/image_{image_id}"
				
				start_time = time.monotonic()
				success = await ftp.request_file_custom(image_id, filename, local_path, defer_assembly=True)
				end_time = time.monotonic()
				print(f"Image {image_id} {'' if success else 'not '}fully received, taking {end_time-start_time} sec")
				
				if success:
					incomplete_images.remove(image_id)
					to_assemble.append(image_id)
					save_data()
					# send confirmation (deletion)
					packet = Packet.make_file_del(image_id)
					await ptp.send_packet(packet)
				else:
					save_data()
					break
			
			for image_id in to_assemble.copy():
				filename = f"image_{image_id}.jpeg"
				local_path = f"received_images/image_{image_id}"
				success = ftp.assemble_file(filename, local_path)
				if success:
					print(f"Image {image_id} assembled")
					to_assemble.remove(image_id)
					save_data()
		
		except Exception as e:
			print("Error in Main Loop:", ''.join(traceback.format_exception(e)))

if __name__ == "__main__":
	asyncio.run(main())
