from wifi_manager import WifiManager
import machine
import time
import ujson
import ubinascii
import network
import struct
import ujson as json
import os
import requests # ไม่ใช้แล้ว
from umqtt.simple import MQTTClient # เพิ่มไลบรารี MQTT
# ... ส่วนโค้ดเดิม ...
def resetWIFI():
        coder_version = {"version":2}
        f = open('version.json','w') 
        f.write(json.dumps(coder_version)) 
        f.close()
        if check_file_exists('wifi.dat') :
            os.remove('wifi.dat') 

        
def read_credentials(selffle):
        lines = []
        try:
            with open(selffle) as file:
                lines = file.readlines()
        except Exception as error:
            if selffle:
                print(error)
            pass
        profiles = {}
        for line in lines:
            ssid, password = line.strip().split(';')
            profiles['ssid'] = ssid
            profiles['password'] = password
        return profiles
def check_file_exists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False
    
def get_device_serial_number():
        try:
            import machine
            import ubinascii
            return ubinascii.hexlify(machine.unique_id()).decode('utf-8').upper()
        except :
            return "UNKNOWN_SERIAL"
        

# MQTT Settings
MQTT_BROKER = "141.98.19.212"
MQTT_PORT = 1883
MQTT_CLIENT_ID = get_device_serial_number() # Unique ID for the device
STATUS_TOPIC = b"washing_machine/" + MQTT_CLIENT_ID + b"/status"
COMMAND_TOPIC = b"washing_machine/" + MQTT_CLIENT_ID + b"/commands"

# ... ส่วนโค้ดเดิม ...

led = machine.Pin(2, machine.Pin.OUT, value=0)
debounce_delay = 1000
timer_direction = 0

import wash

# Global MQTT client instance
client = None

def sub_cb(topic, msg):
    #print(f"Received MQTT message on topic '{topic.decode()}': {msg.decode()}")
    try:
        data_json = json.loads(msg.decode())
        interpret_command(data_json) # เรียกใช้ฟังก์ชัน interpret_command
    except :
        print(f"Failed to parse JSON from MQTT message")

def interpret_command(data_json):
    global client
    command_response_topic = b"washing_machine/" + MQTT_CLIENT_ID + b"/command_response"

    if 'command' in data_json:
        cmd = data_json['command']
        response_data = {} # Data to send back as command response

        try:
            if cmd['key'] == 'update_code' and 'url' in cmd and 'file_name' in cmd:
                #print(f"Updating code from {cmd['url']}")
                response_update = requests.get(cmd['url'])
                if response_update.status_code == 200:
                    with open(cmd['file_name'], 'w') as f:
                        f.write(response_update.text)
                    response_data = {"status": "success", "message": f"Updated {cmd['file_name']}"}
                    client.publish(command_response_topic, json.dumps(response_data).encode())
                    time.sleep(5)
                    machine.reset()
                    return True
                else:
                    response_data = {"status": "error", "message": f"Failed to download {cmd['file_name']}"}

            elif cmd['key'] == 'update_wash' and 'value' in cmd:
                #print("Updating wash.py")
                response_update = requests.get(cmd['value'])
                if response_update.status_code == 200:
                    with open('wash.py', 'w') as f: # ควรเป็น wash.py ไม่ใช่ wash.txt
                        f.write(response_update.text)
                    response_data = {"status": "success", "message": "Updated wash.py"}
                    client.publish(command_response_topic, json.dumps(response_data).encode())
                    time.sleep(5)
                    machine.reset()
                    return True
                else:
                    response_data = {"status": "error", "message": "Failed to update wash.py"}

            elif cmd['key'] == 'update_main' and 'value' in cmd:
                print("Updating main.py")
                response_update = requests.get(cmd['value'])
                if response_update.status_code == 200:
                    with open('main.py', 'w') as f: # ควรเป็น main.py ไม่ใช่ main.txt
                        f.write(response_update.text)
                    response_data = {"status": "success", "message": "Updated main.py"}
                    client.publish(command_response_topic, json.dumps(response_data).encode())
                    time.sleep(5)
                    machine.reset()
                    return True
                else:
                    response_data = {"status": "error", "message": "Failed to update main.py"}

            elif cmd['key'] == 'update_version':
                print("Updating all versions...")
                boot_url = 'https://raw.githubusercontent.com/SuperBoss221/wash_mqtt/refs/heads/main/boot.py' # ควรเป็น .py
                main_url = 'https://raw.githubusercontent.com/SuperBoss221/wash_mqtt/refs/heads/main/main.py' # ควรเป็น .py
                wifi_url = 'https://raw.githubusercontent.com/SuperBoss221/wash_mqtt/refs/heads/main/wifi_manager.py' # ควรเป็น .py
                wash_url = 'https://raw.githubusercontent.com/SuperBoss221/wash_mqtt/refs/heads/main/wash.py' # ควรเป็น .py
                try:
                    response_boot = requests.get(boot_url)
                    if response_boot.status_code == 200:
                        with open('boot.py', 'w') as f: f.write(response_boot.text)
                except : print(f"Error updating boot.py")
                try:
                    response_main = requests.get(main_url)
                    if response_main.status_code == 200:
                        with open('main.py', 'w') as f: f.write(response_main.text)
                except : print(f"Error updating main.py")
                try:
                    response_wifi = requests.get(wifi_url)
                    if response_wifi.status_code == 200:
                        with open('wifi_manager.py', 'w') as f: f.write(response_wifi.text)
                except : print(f"Error updating wifi.py")
                try:
                    response_wash = requests.get(wash_url)
                    if response_wash.status_code == 200:
                        with open('wash.py', 'w') as f: f.write(response_wash.text)
                except : print(f"Error updating wash.py")

                response_data = {"status": "success", "message": "Firmware update initiated."}
                client.publish(command_response_topic, json.dumps(response_data).encode())
                led.value(0)
                time.sleep(2)
                machine.reset()
                return True

            elif cmd['key'] == 'reset_error':
                #print("Resetting error...")
                txt = wash.reset_error()
                response_data = {"status": "success", "message": "Error reset initiated.", "modbus_response": json.loads(txt)}
                client.publish(command_response_topic, json.dumps(response_data).encode())
                led.value(0)
                machine.reset()
                return True
            elif cmd['key'] == 'reset_wifi':
                #print("Resetting WiFi...")
                resetWIFI()
                response_data = {"status": "success", "message": "WiFi reset initiated."}
                client.publish(command_response_topic, json.dumps(response_data).encode())
                time.sleep(5)
                led.value(0)
                machine.reset()
                return True

            elif cmd['key'] == 'get_status':
                #print("Getting status...")
                wash_status = json.loads(wash.get_machine_status())
                status_payload = {"version": "3", "cmd": "get_status", "ip": str(WiFIManager.get_address()[0]), "client_id": get_device_serial_number(), "status": wash_status}
                client.publish(STATUS_TOPIC, json.dumps(status_payload).encode()) # Publish status directly
                response_data = {"status": "success", "message": "Status published."}

            elif cmd['key'] == 'menu' and 'value' in cmd:
                #print(f"Selecting program {cmd['value']}")
                txt = wash.select_program(int(cmd['value']))
                response_data = {"status": "success", "message": f"Program {cmd['value']} selected.", "modbus_response": json.loads(txt)}

            elif cmd['key'] == 'coins' and 'value' in cmd:
                #print(f"Adding {cmd['value']} coins")
                txt = wash.add_coins(int(cmd['value']))
                response_data = {"status": "success", "message": f"Added {cmd['value']} coins.", "modbus_response": json.loads(txt)}

            elif cmd['key'] == 'start':
                #print("Starting operation")
                txt = wash.start_operation()
                response_data = {"status": "success", "message": "Start command sent.", "modbus_response": json.loads(txt)}

            elif cmd['key'] == 'stop':
                #print("Stopping operation")
                txt = wash.stop_operation()
                response_data = {"status": "success", "message": "Stop command sent.", "modbus_response": json.loads(txt)}

            elif cmd['key'] == 'command' and 'address' in cmd and 'value' in cmd:
                #print(f"Sending custom command to address {cmd['address']} with value {cmd['value']}")
                txt = wash.sendcommand(int(cmd['address']), int(cmd['value']))
                response_data = {"status": "success", "message": "Custom command sent.", "modbus_response": json.loads(txt)}

            elif cmd['key'] == 'reboot':
                #print("Rebooting device")
                response_data = {"status": "success", "message": "Device rebooting."}
                client.publish(command_response_topic, json.dumps(response_data).encode())
                time.sleep(5)
                machine.reset()
            else:
                response_data = {"status": "error", "message": "Unknown or incomplete command."}

        except :
            print(f"Error processing command: {e}")
            response_data = {"status": "error", "message": f"Error processing command: {e}"}
        finally:
            # Always publish a response for the command, even if it's an error
            client.publish(command_response_topic, json.dumps(response_data).encode())


mqtt_offline = 0
def connect_and_subscribe():
    global client , mqtt_offline
    try:
        client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT)
        client.set_callback(sub_cb)
        client.connect()
        client.subscribe(COMMAND_TOPIC)
        print(f"Connected to MQTT broker {MQTT_BROKER} and subscribed to {COMMAND_TOPIC.decode()}")
        return client
    except :
        print(f"Failed to connect to MQTT broker ",mqtt_offline)
        if mqtt_offline >= 5 :
                WiFIManager.connect()
                checkCnnect = 0
                while True:
                    if WiFIManager.is_connected():
                            print('Connected to WiFi!')
                            break
                    else:
                            if checkCnnect >= 10:
                                print('Resetting WiFi...')
                                machine.reset()
                            checkCnnect = checkCnnect + 1
                            time.sleep(10)
        mqtt_offline += 1
        return None

# ... ส่วนโค้ดเดิม ...

# เปลี่ยน logic ของ interpret_status_data (ส่วนนี้จะถูกตัดออกไป)
# def interpret_status_data(data):
#     try:
#         # ... โค้ด HTTP เดิม ...
#     except:
#         # ... โค้ด HTTP เดิม ...


# --- WIFI Connection ---
WiFIManager = WifiManager()
WiFIManager.connect()
checkCnnect = 0
while True:
    if WiFIManager.is_connected():
        print('Connected to WiFi!')
        break
    else:
        if checkCnnect >= 5:
            print('Resetting WiFi...')
            time.sleep(5)
            machine.reset()
        checkCnnect = checkCnnect + 1
        time.sleep(10)

led.value(1)
#print(str(WiFIManager.get_address()[0]))
if str(WiFIManager.get_address()[0]) == '0.0.0.0':
    #print('Rebooting due to no IP address')
    led.value(0)
    machine.reset()
led.value(0)
mqtt_offline =0
# Connect to MQTT after WiFi is connected
mqtt_client = None
while mqtt_client is None:
    mqtt_client = connect_and_subscribe()
    if mqtt_client is None:
        print("Retrying MQTT connection in 5 seconds...")
        time.sleep(5)

# Main loop for publishing status and checking for MQTT messages
while True:
    try:
        led.value(1) # Indicate activity
        wash_status = json.loads(wash.get_machine_status())
        # Prepare payload for MQTT
        status_payload = {
            "version": 1,
            "ip": str(WiFIManager.get_address()[0]),
            "client_id": get_device_serial_number(),
            "status": wash_status
        }
        mqtt_client.publish(STATUS_TOPIC, json.dumps(status_payload).encode())
        #print(f"Published status to {STATUS_TOPIC.decode()}")

        # Check for incoming MQTT messages (commands)
        mqtt_client.check_msg()

        led.value(0) # Activity done
        time.sleep(2) # Adjust interval as needed
    except OSError as e:
        #print(f"MQTT connection error: {e}. Reconnecting...")
        led.value(0)
        time.sleep(1)
        mqtt_client = None # Reset client to force re-connection
        while mqtt_client is None:
            mqtt_client = connect_and_subscribe()
            if mqtt_client is None:
                if mqtt_offline >= 5 :
                    WiFIManager.connect()
                    checkCnnect = 0
                    while True:
                        if WiFIManager.is_connected():
                            print('Connected to WiFi!')
                            break
                        else:
                            if checkCnnect >= 10:
                                #print('Resetting WiFi...')
                                machine.reset()
                            checkCnnect = checkCnnect + 1
                            time.sleep(10)
                            
                #print("Retrying MQTT connection in 5 seconds...")
                time.sleep(5)
                mqtt_offline +=1
        machine.reset()
    except :
        print(f"An unexpected error occurred")
        led.value(0)
        time.sleep(5)
        machine.reset()
machine.reset()
