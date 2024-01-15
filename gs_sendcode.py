import paho.mqtt.client as paho
from CIRCUITPY.secrets import secrets
import sys
import json



# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc, yyy):
    print("Connected with result code "+str(rc))
    filepath = sys.argv[1]
    file = open(f'CIRCUITPY/{filepath}','r')
    payload = json.dumps({"filepath": filepath, "data": file.read()}).encode('utf-8')
    client.publish(secrets['mqtt']['codetopic'], payload =payload , qos=0)
    print("sent")
    file.close()
    client.disconnect()
    print('disconnected')

client = paho.Client(client_id="", userdata=None, protocol=paho.MQTTv5)
client.tls_set(tls_version=paho.ssl.PROTOCOL_TLS)
client.username_pw_set(secrets["mqtt"]["username"],secrets['mqtt']['password'])
client.connect(secrets['mqtt']['broker'], secrets['mqtt']['port'])

client.on_connect = on_connect

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give   a threaded interface and a
client.loop_forever()