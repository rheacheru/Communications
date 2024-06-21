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
# from comms import file_receive
import os
import asyncio


from new_comms_protocol.ptp import AsyncPacketTransferProtocol
from new_comms_protocol.ftp import FileTransferProtocol



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



async def main():
	CS = digitalio.DigitalInOut(board.D20)
	CS.switch_to_output(True)
	RST = digitalio.DigitalInOut(board.D21)
	RST.switch_to_output(True)
	print('hello')

	RADIO_FREQ_MHZ = 437.4
	node = const(0xfb)
	destination = const(0xfa)
	MAX_PACKET_SIZE = 250

	radio = pycubed_rfm9x.RFM9x(board.SPI(), CS, RST, 437.4)
	radio.spreading_factor = 8
	radio.node = node
	radio.destination = destination
	radio.enable_crc = True
	
	pool = attempt_wifi()
	
	PTP = AsyncPacketTransferProtocol(radio, packet_size=MAX_PACKET_SIZE, timeout=10, log=False)
	FTP = FileTransferProtocol(PTP, log=False)
	
	# async def send_packet(self, packet_type, payload, sequence_num=2**15 - 1):
	
	while True:
		try:
			print('Waiting for telemetry ping (handshake 1)')	
			
			packet = radio.receive(timeout=10)
			if packet is None:
				continue
			packet = packet.decode("utf-8")
			if packet != "#IRVCB":
				continue
			print("Telemetry ping (handshake 1) received")
			
			radio.send(b"#IRVCBH2")
			print("Handshake 2 sent, waiting for handshake 3")
			
			# filepath =f'received_telemetry/{datetime.now().isoformat()}.txt'.replace(":", "-")
			# with open(filepath, 'w') as f:
			#     f.write(packet)
			#     print(f"Telemetry packet written to {filepath}")
			# radio.send("IRVCB")

			packet = radio.receive(timeout=10)
			if packet is None:
				continue
			identifier = packet[0:8].decode("utf-8")
			if identifier != "#IRVCBH3":
				continue
			print("Handshake 3 received")
			
			image_count = int.from_bytes(packet[8:12], "little")
			print(f"CubeSat has taken {image_count} images so far")
			
			# Start listening for image packets
			while True:
				packet_list, missing = await FTP.receive_file_custom()
				if packet_list is None:
					print("No image packet received")
					break
				print("Image packet received")
				print(packet_list)
				print(missing)
			
			# Request images or return to standby
			
		
		except Exception as e:
			print("Error in Main Loop: " + ''.join(traceback.format_exception(e)))

if __name__ == "__main__":
	asyncio.run(main())
