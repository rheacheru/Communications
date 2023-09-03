#import adafruit_rfm9x 
import time
RADIO_FREQ_MHZ = 437.4
import serial

ser = serial.Serial(port="COM1", baudrate=9600)


while True:
    if ser.inWaiting() != 0: 
        packet = ser.receive(ser.in_waiting)
        if packet is not None:
            print(str(packet, "ascii"))
            time.sleep(3)
    


