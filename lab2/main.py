from temperature import read_temp_hum
from ultrasonic import distance_cm
import socket
from machine import Pin, SoftI2C
from machine_i2c_lcd import I2cLcd
from time import sleep

# --- LCD setup ---
I2C_ADDR = 0x27
i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=400000)
lcd = I2cLcd(i2c, I2C_ADDR, 2, 16)

# --- LED setup ---
led = Pin(2, Pin.OUT)  # adjust GPIO if needed

# --- HTML page ---
# --- HTML page ---
def web_page():
    gpio_state = "ON" if led.value() == 1 else "OFF"

    html = f"""
    <html>
    <head>
      <meta charset="UTF-8">       
      <title>ESP Web Server</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <link rel="icon" href="data:,">
      <style>
        html{{font-family: Helvetica; display:inline-block; margin: 0px auto; text-align: center;}}
        h1{{color: #0F3376; padding: 2vh;}}
        p{{font-size: 1.5rem;}}
        .button{{display: inline-block; background-color: #e7bd3b; border: none; 
        border-radius: 4px; color: white; padding: 10px 20px; text-decoration: none; font-size: 20px; margin: 2px; cursor: pointer;}}
        .button2{{background-color: #4286f4;}}
        input[type=text]{{font-size: 1.2rem; padding:5px; width:200px;}}
      </style>
      <script>
        function updateValues() {{
            fetch('/sensor')
            .then(response => response.json())
            .then(data => {{
                document.getElementById('distance').innerText = data.distance.toFixed(2) + ' cm';
                document.getElementById('temp').innerText = data.temp.toFixed(2) + ' °C';
            }})
            .catch(err => console.log('Error:', err));
        }}
        setInterval(updateValues, 1500);

        function sendText(text) {{
            fetch(`/lcd?text=${{encodeURIComponent(text)}}`)
            .then(response => response.text())
            .then(data => console.log(data))
            .catch(err => console.log('Error:', err));
        }}

        function sendDistance() {{
            const val = document.getElementById('distance').innerText.split(' ')[0];
            sendText("Distance " + val + "cm");
        }}

        function sendTemp() {{
            const val = document.getElementById('temp').innerText.split(' ')[0];
            sendText("Temp " + val + "C");
        }}
      </script>
    </head>
    <body>
      <h1>ESP Web Server</h1> 
      <p>GPIO state: <strong>{gpio_state}</strong></p>

      <p>
        Distance: <strong id="distance">0.0 cm</strong>
        <button class="button button2" onclick="sendDistance()">Write to LCD</button>
      </p>
      <p>
        Temperature: <strong id="temp">0.0 °C</strong>
        <button class="button button2" onclick="sendTemp()">Write to LCD</button>
      </p>

      <p><a href="/?led=on"><button class="button">ON</button></a></p>
      <p><a href="/?led=off"><button class="button button2">OFF</button></a></p>

      <p>
        <input type="text" id="lcdText" placeholder="Enter text">
        <button class="button button2" onclick="sendText(document.getElementById('lcdText').value)">Send</button>
      </p>
    </body>
    </html>
    """
    return html


# --- Socket server ---
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(5)

while True:
    conn, addr = s.accept()
    request = conn.recv(1024)
    request = str(request)

    # --- LED control ---
    led_on = request.find('/?led=on')
    led_off = request.find('/?led=off')
    if led_on == 6:
        print('LED ON')
        led.value(1)
    if led_off == 6:
        print('LED OFF')
        led.value(0)

    # --- Sensor JSON ---
    if '/sensor' in request:
        distance = distance_cm()
        temp, hum = (round(x, 2) for x in read_temp_hum())

        response = f'{{"distance": {distance}, "temp": {temp}, "hum": {hum}}}'
        conn.send('HTTP/1.1 200 OK\n')
        conn.send('Content-Type: application/json\n')
        conn.send('Connection: close\n\n')
        conn.sendall(response)
        conn.close()
        continue

    # --- LCD text input ---
    if '/lcd?text=' in request:
        start = request.find('/lcd?text=') + len('/lcd?text=')
        end = request.find(' ', start)
        text = request[start:end]
        text = text.replace('%20', ' ')

        lcd.clear()
        lcd.move_to(0, 0)
        lcd.putstr(text[:16])
        lcd.move_to(0, 1)
        lcd.putstr(text[16:32] if len(text) > 16 else '')

        conn.send('HTTP/1.1 200 OK\n\nText displayed')
        conn.close()
        continue
    
    

    # --- Serve main page ---
    response = web_page()
    conn.send('HTTP/1.1 200 OK\n')
    conn.send('Content-Type: text/html\n')
    conn.send('Connection: close\n\n')
    conn.sendall(response)
    conn.close()
