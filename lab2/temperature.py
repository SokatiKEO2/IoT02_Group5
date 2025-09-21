import dht
import machine
import time

sensor = dht.DHT22(machine.Pin(4))

def read_temp_hum():
    sensor.measure()
    temp = sensor.temperature()
    hum = sensor.humidity()
    return temp, hum

