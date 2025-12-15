## 1. Wiring

* **SDA** → ESP32 GPIO 21
* **SCL** → ESP32 GPIO 22
* **VCC** → 3.3V
* **GND** → GND

![Wiring Diagram](./media/wiring.png)

---

## 2. Task Execution

### Task 1 – BMP280 Read & Print

**Evidence:**

![Serial Monitor Screenshot](./media/serialmonitor.png)

---

### Task 2 – MQTT Publish

**Evidence:**

![MQTT Debug Screenshot](./media/monitor.png)

---

### Task 3 – Node-RED Flow

**Evidence:**

![Node-RED Flow Screenshot](./media/nodered.png)

---

### Task 4 – InfluxDB Setup

* Username: `test`
* Password: `test`
* Organization name: `test`
* Created bucket: `lab4_bmp280`
* Configured authentication token

**Evidence:**

![InfluxDB Data Screenshot](./media/influxdb.png)

---

### Task 5 – Grafana Dashboard

**Evidence:**

![Grafana Dashboard Screenshot](./media/grafana.png)

---

## 4. Data Pipeline Diagram

The overall data flow for this lab is:

```
ESP32 (BMP280)
    → MQTT Broker
        → Node-RED
            → InfluxDB
                → Grafana Dashboard
```

---

## 5. Files Submitted

* [ESP32 Python Code](./src/main.py)
* [Node-RED flow JSON](./src/nodered.json)
* [Demo Video](./media/demo.mp4)
