from machine import Pin, I2C
import time
import network
import json
from umqtt.simple import MQTTClient
import bmp280

# ---------- WIFI ----------
WIFI_SSID = "YOUR_WIFI"
WIFI_PASSWORD = "YOUR_PASSWORD"

wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(WIFI_SSID, WIFI_PASSWORD)

while not wifi.isconnected():
    time.sleep(1)

print("WiFi connected")

# ---------- MQTT ----------
MQTT_BROKER = "test.mosquitto.org"
CLIENT_ID = "esp32-bmp280"
TOPIC = b"esp32/bmp280/data"

mqtt = MQTTClient(CLIENT_ID, MQTT_BROKER)
mqtt.connect()
print("MQTT connected")

# ---------- I2C ----------
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)

# ---------- BMP280 ----------
bmp = bmp280.BMP280(i2c, addr=0x76, use_case=bmp280.BMP280_CASE_WEATHER)

bmp.oversample = bmp280.BMP280_OS_HIGH
bmp.sea_level_pressure = 101325  # Pa

# ---------- MAIN LOOP ----------
while True:
    temperature = round(bmp.temperature, 2)
    pressure = round(bmp.pressure, 2)

    payload = {"temperature": temperature, "pressure": pressure}

    print("Temperature:", temperature, "°C | Pressure:", pressure, "Pa")

    mqtt.publish(TOPIC, json.dumps(payload))
    print("Published:", payload)
    time.sleep(5)
