import random
import time
import json
import os

from paho.mqtt import client as mqtt_client


# ~ broker = 'ye6cff2a.ala.us-east-1.emqxsl.com'
# ~ port = 8883
# ~ topic = "kuvoz/07/01"
# ~ # generate client ID with pub prefix randomly
# ~ client_id = f'kuvoz-mqtt-{random.randint(0, 1000)}'
# ~ username = 'oktay'
# ~ password = 'VV9iB_3ad:2VERX'

def readFile():
    if(os.path.isfile("./connect.json")):
        # read data from file
        with open("connect.json", "r") as f:
            data =json.load(f)
    # ~ else:
        # ~ # define data to save
        # ~ data = {
            # ~ "broker": "ye6cff2a.ala.us-east-1.emqxsl.com",
            # ~ "port": 8883,
            # ~ "topic": "kuvoz/07/00",
            # ~ "client_id": f'kuvoz-mqtt-{random.randint(0, 1000)}',
            # ~ "username": "oktay",
            # ~ "password": "VV9iB_3ad:2VERX"
        # ~ }

        # ~ # save data to file
        # ~ with open("connect.json", "w") as f:
            # ~ json.dump(data, f)
    return data

def connect_mqtt(data):
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
            client.subscribe(data["topic"])  # Add this line
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(data["client_id"])
    client.tls_set(tls_version=mqtt_client.ssl.PROTOCOL_TLS)
    client.username_pw_set(data["username"], data["password"])
    client.on_connect = on_connect
    client.connect(data["broker"], int(data["port"]),keepalive=60)
    client.on_disconnect = on_disconnect
    return client


def publish(client,msgP,data):
    msg_count = 0
    # ~ param=KuvozParam()
    # ~ while True:
        # ~ time.sleep(10)
        # ~ msg = f"Sicaklık: {par.sicaklik}"
    # ~ msgJ = {"temperature": "{:.2f}".msgP.sicaklik,"humidity":"{:.2f}".msgP.nem}
    msgJ = {"temperature": f"{msgP.sicaklik:.1f}", "humidity": f"{msgP.nem:.1f}"}

    result = client.publish(data["topic"], json.dumps(msgJ))
    # result: [0, 1]
    status = result[0]
    if status == 0:
        print(f"Send `{msgP}` to topic `{data['topic']}`")
    else:
        print(f"Failed to send message to topic {data['topic']}")
    # ~ msg_count += 1
def subscribe(client: mqtt_client,data,msgP):
    def on_message(client, userdata, msg):
        print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        if(msg.payload.decode() == 'On'):
            # ~ print(f"Mesaj alındı")
            publish(client,msgP,data)
            

    client.subscribe(data["topic"])
    client.on_message = on_message
    

def on_disconnect(client, userdata, rc):
    print("Disconnected, trying to reconnect")
    client.reconnect()

def run():
    data=readFile()
    client = connect_mqtt(data)
    subscribe(client,data)
    client.loop_forever()
    
    publish(client,'dene',data)


if __name__ == '__main__':
    run()
