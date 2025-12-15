Project Proposal Draft 

Smart IoT-Enabled Trash Bin with Multi-Sensor Monitoring, MQTT Telemetry, and Telegram Bot Control 

1. Introduction 

This project proposes the design and implementation of a Smart IoT-Enabled Trash Bin System utilizing an ESP32 microcontroller paired with multiple ultrasonic sensors and environmental sensors. The system aims to automate trash detection, monitor bin capacity, gather environmental metadata, and transmit real-time telemetry to a backend for visualization. The solution integrates MQTT, InfluxDB, and Grafana for data collection and dashboarding, while a Telegram bot provides remote controls, status queries, and alert notifications. 

2. Objectives 

The main objectives of the system are: 

Automated Trash Event Detection 

 Detect when an item is thrown into the trash bin using an entrance-mounted ultrasonic sensor. 

Proximity-Based Bin Activation 

 Detect a user approaching the bin using an outward-facing ultrasonic sensor. 

Bin Capacity Measurement 

 Estimate the fullness of the bin using an ultrasonic sensor mounted inside the lid. 

Environmental Monitoring 

 Capture temperature and humidity using a DHT22 (or similar) sensor to gather contextual metadata. 

IoT Connectivity & Telemetry 

 Publish sensor readings and trash event counts via MQTT to an InfluxDB instance for time-series storage. 

Data Visualization 

 Display real-time and historical data using Grafana, including capacity trends, temperature/humidity, and trash counts. 

Telegram Bot Integration 

 Provide a simple remote interface to: 

Retrieve bin status 

View trash counts 

Access current sensor readings 

Trigger administrative commands (e.g., reset count) 

 

3. System Overview 

The proposed system consists of four primary components: 

3.1 Hardware Layer 

ESP32 Development Board (WiFi-enabled microcontroller) 

Three Ultrasonic Sensors (HC-SR04): 

Entrance Sensor: Detects items being thrown in. 

User Proximity Sensor: Detects people near the bin. 

Capacity Sensor: Measures distance to the trash level. 

DHT22 Temperature & Humidity Sensor 

3.2 Firmware Layer 

The ESP32 firmware will: 

Continuously read sensor values. 

Run event-based logic (detect trash throws, proximity events). 

Estimate capacity as a percentage using distance readings. 

Publish telemetry via MQTT with JSON payloads. 

Respond to incoming commands from the Telegram bot backend. 

3.3 Networking & Backend Layer 

MQTT Broker (Mosquitto or similar) facilitating lightweight communication. 

InfluxDB storing: 

Trash count events 

Capacity over time 

Temperature & humidity 

Sensor states 

Backend script or middleware to forward Telegram commands to the ESP32 via MQTT topics. 

3.4 Visualization & User Interface 

Grafana Dashboard displaying: 

Capacity graph 

Real-time fullness bar 

Trash event frequency 

Temperature & humidity trends 

Alerts (e.g., “Bin Full”) 

Telegram Bot providing instant access to: 

/status – bin capacity, temperature, humidity 

/count – number of trash events 

/summary – simplified text dashboard 

/reset – resets trash counter 

Automatic notifications when bin reaches 80–90% capacity 

 

4. Expected Outcomes 

Upon completion, the system will deliver: 

A fully functional IoT trash bin capable of autonomous sensing and monitoring. 

A complete time-series dataset visualized on Grafana. 

A Telegram bot providing remote operational control and insights. 

A modular architecture allowing future expansion (e.g., servo-based auto-opening lid, weight sensors, ML-based detection). 

 

 

 

Project Proposal: IoT-Enabled Smart Garbage Monitoring Bin 

Group 5: CHEA Vuthearith, KEO Sokati 

This project proposes an IoT-enabled Smart Garbage Monitoring Bin that uses sensors and automation to monitor fill level, detect odor, and improve collection efficiency. The solution integrates MQTT, InfluxDB, and Grafana for data collection and dashboarding, while a Telegram bot provides remote controls, status queries, and alert notifications. 

The goal is to design and implement an automated garbage bin that: 

Monitors fill level using an ultrasonic sensor 

Detects odor/moisture levels using a humidity sensor 

Automatically opens the lid when a user approaches 

Displays real-time bin status on an LCD 

Grafana dashboard display with  

Capacity graph  

Real-time fullness bar  

Trash event frequency  

Temperature & humidity trends  

Alerts (e.g., “Bin Full”) 

Sends IoT alerts when the bin is nearly full (≥80%) 
