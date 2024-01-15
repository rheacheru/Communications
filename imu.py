import board
import busio
from adafruit_lsm6ds.lsm6dsox import LSM6DSOX
from picamera2 import Picamera2 #need to install?
import time
import math
from datetime import datetime
import os


i2c = busio.I2C(board.SCL, board.SDA)
sensor1 = LSM6DSOX(i2c)
camera = Picamera2()
camera.resolution = (64,64)
THRESHOLD = 18
max = 0

print('shake imu to take picture')
while True:
    accelx, accely, accelz = sensor1.acceleration
    accelz = accelz - 9.8
    accel_value = math.sqrt(math.pow(accelx, 2)+ math.pow(accely, 2)+ math.pow(accelz, 2))
    if(accel_value > THRESHOLD):
        print('taking pic in 5 seconds get ready!')
        time.sleep(5)
        filename = f'{datetime.now().strftime("%Y%M%D%H%M%S")}.jpg'
        camera.start_and_capture_file(filename)
        camera.close()
        print('sending to mqtt')
        os.system(f'python sendcode.py {filename}')
    time.sleep(1)


