import network
import socket
import time
import urequests
from machine import Pin, PWM, I2C
import ujson

# ======================== CONFIGURATION ========================
# WiFi credentials
WIFI_SSID = "Wokwi-GUEST"
WIFI_PASSWORD = ""


# Telegram Bot
BOT_TOKEN = "8335706055:AAEYOtQxRszYMT0v6IU1bCdfeWm4ig_fn7c"
CHAT_ID = "-4846234897"

# Pin definitions
TRIG_PIN = 27
ECHO_PIN = 26
SERVO_PIN = 16
IR_SLOT1 = 32
IR_SLOT2 = 35
IR_SLOT3 = 34

# LCD I2C pins
LCD_SDA = 21
LCD_SCL = 22

# Constants
TOTAL_SLOTS = 3
DETECTION_DISTANCE = 20  # cm
DEBOUNCE_TIME = 200  # ms
LEAVE_GRACE = 1000  # 1 second
PRICE_PER_MINUTE = 0.5  # $0.5 per minute

# ======================== HARDWARE SETUP ========================
# Ultrasonic sensor
trig = Pin(TRIG_PIN, Pin.OUT)
echo = Pin(ECHO_PIN, Pin.IN)

# Servo
servo = PWM(Pin(SERVO_PIN), freq=50)

# IR sensors
ir_pins = [
    Pin(IR_SLOT1, Pin.IN, Pin.PULL_UP),
    Pin(IR_SLOT2, Pin.IN, Pin.PULL_UP),
    Pin(IR_SLOT3, Pin.IN, Pin.PULL_UP),
]

# LCD (I2C 16x2)
try:
    i2c = I2C(0, sda=Pin(LCD_SDA), scl=Pin(LCD_SCL), freq=100000)
    lcd_addr = 0x27
    has_lcd = True
except:
    has_lcd = False
    print("LCD not found - continuing without LCD")


# ======================== LCD DRIVER ========================
class LCD_I2C:
    def __init__(self, i2c, addr=0x27):
        self.i2c = i2c
        self.addr = addr
        self.backlight = 0x08
        self.init_lcd()

    def write_nibble(self, data):
        self.i2c.writeto(self.addr, bytearray([data | self.backlight]))
        time.sleep_us(1)
        self.i2c.writeto(self.addr, bytearray([data | 0x04 | self.backlight]))
        time.sleep_us(1)
        self.i2c.writeto(self.addr, bytearray([data | self.backlight]))
        time.sleep_us(100)

    def write_byte(self, data, mode):
        self.write_nibble(mode | (data & 0xF0))
        self.write_nibble(mode | ((data << 4) & 0xF0))

    def init_lcd(self):
        time.sleep_ms(50)
        self.write_nibble(0x30)
        time.sleep_ms(5)
        self.write_nibble(0x30)
        time.sleep_us(150)
        self.write_nibble(0x30)
        self.write_nibble(0x20)
        self.write_byte(0x28, 0)  # 4-bit, 2 lines
        self.write_byte(0x0C, 0)  # Display on, cursor off
        self.write_byte(0x06, 0)  # Entry mode
        self.clear()

    def clear(self):
        self.write_byte(0x01, 0)
        time.sleep_ms(2)

    def set_cursor(self, col, row):
        row_offsets = [0x00, 0x40]
        self.write_byte(0x80 | (col + row_offsets[row]), 0)

    def print(self, text):
        for char in text:
            self.write_byte(ord(char), 1)


# Initialize LCD
if has_lcd:
    lcd = LCD_I2C(i2c, lcd_addr)
else:
    lcd = None

# ======================== GLOBAL STATE ========================
slots = [
    {
        "occupied": False,
        "assigned_id": 0,
        "time_in": 0,
        "last_change_time": 0,
        "last_state": False,
        "leave_detected_time": 0,
    },
    {
        "occupied": False,
        "assigned_id": 0,
        "time_in": 0,
        "last_change_time": 0,
        "last_state": False,
        "leave_detected_time": 0,
    },
    {
        "occupied": False,
        "assigned_id": 0,
        "time_in": 0,
        "last_change_time": 0,
        "last_state": False,
        "leave_detected_time": 0,
    },
]

ticket_history = []
id_used = [False, False, False, False]  # index 0 unused, 1-3 for IDs


# ======================== SERVO CONTROL ========================
def open_gate():
    servo.duty(77)  # 90 degrees (~1.5ms pulse)
    print("Gate OPENED")


def close_gate():
    servo.duty(26)  # 0 degrees (~0.5ms pulse)
    print("Gate CLOSED")


# ======================== ULTRASONIC SENSOR ========================
def get_distance():
    trig.off()
    time.sleep_us(2)
    trig.on()
    time.sleep_us(10)
    trig.off()

    timeout = 30000
    start = time.ticks_us()
    while echo.value() == 0:
        if time.ticks_diff(time.ticks_us(), start) > timeout:
            return 999
        pass

    pulse_start = time.ticks_us()
    while echo.value() == 1:
        if time.ticks_diff(time.ticks_us(), pulse_start) > timeout:
            return 999
        pass
    pulse_end = time.ticks_us()

    duration = time.ticks_diff(pulse_end, pulse_start)
    distance = (duration * 0.0343) / 2
    return distance


# ======================== PARKING LOGIC ========================
def get_free_slot_count():
    return sum(1 for s in slots if not s["occupied"])


def get_lowest_available_id():
    for i in range(1, TOTAL_SLOTS + 1):
        if not id_used[i]:
            return i
    return 0


def assign_car_to_slot(slot_index):
    # Prevent double assignment - check if already occupied
    if slots[slot_index]["occupied"]:
        return

    car_id = get_lowest_available_id()
    if car_id == 0:
        print(f"ERROR: No available ID for Slot S{slot_index+1}")
        return

    # Mark ID as used FIRST to prevent race condition
    id_used[car_id] = True

    # Then update slot info
    slots[slot_index]["occupied"] = True
    slots[slot_index]["assigned_id"] = car_id
    slots[slot_index]["time_in"] = time.time()

    print(f"Car assigned: ID={car_id}, Slot=S{slot_index+1}")


def process_exit(slot_index):
    slot = slots[slot_index]
    car_id = slot["assigned_id"]
    time_out = time.time()
    duration_sec = time_out - slot["time_in"]
    duration_min = duration_sec / 60
    fee = duration_min * PRICE_PER_MINUTE

    ticket = {
        "id": car_id,
        "slot": slot_index + 1,
        "time_in": slot["time_in"],
        "time_out": time_out,
        "duration": duration_min,
        "fee": fee,
        "active": False,
    }

    ticket_history.append(ticket)
    if len(ticket_history) > 20:
        ticket_history.pop(0)

    # Free the slot and ID
    id_used[car_id] = False
    slots[slot_index]["occupied"] = False
    slots[slot_index]["assigned_id"] = 0
    slots[slot_index]["time_in"] = 0
    slots[slot_index]["leave_detected_time"] = 0

    print(
        f"Exit processed: ID={car_id}, Duration={duration_min:.1f}min, Fee=${fee:.2f}"
    )
    send_telegram_receipt(ticket)


def update_slots():
    now = time.ticks_ms()

    for i in range(TOTAL_SLOTS):
        current_ir = ir_pins[i].value() == 0  # LOW = occupied

        # Debounce
        if current_ir != slots[i]["last_state"]:
            slots[i]["last_change_time"] = now
            slots[i]["last_state"] = current_ir

        # Only process if state is stable for debounce period
        time_diff = time.ticks_diff(now, slots[i]["last_change_time"])
        if time_diff > DEBOUNCE_TIME:
            # Entry detection - only if not already occupied
            if current_ir and not slots[i]["occupied"]:
                assign_car_to_slot(i)
                # Reset debounce to prevent immediate re-trigger
                slots[i]["last_change_time"] = now

            # Exit detection with grace period
            elif not current_ir and slots[i]["occupied"]:
                if slots[i]["leave_detected_time"] == 0:
                    slots[i]["leave_detected_time"] = now
                elif (
                    time.ticks_diff(now, slots[i]["leave_detected_time"]) >= LEAVE_GRACE
                ):
                    process_exit(i)
                    # Reset debounce
                    slots[i]["last_change_time"] = now
            else:
                # Reset leave detection if car is still there
                slots[i]["leave_detected_time"] = 0


def check_entry():
    distance = get_distance()

    if 0 < distance < DETECTION_DISTANCE:
        free_count = get_free_slot_count()

        if free_count == 0:
            print("Parking FULL - Gate closed")
        else:
            print("Car detected - Opening gate")
            open_gate()
            time.sleep(5)
            close_gate()

        time.sleep(2)


# ======================== LCD UPDATE ========================
def update_lcd():
    if not lcd:
        return

    free_count = get_free_slot_count()

    lcd.clear()
    if free_count == 0:
        lcd.set_cursor(0, 0)
        lcd.print("    FULL")
    else:
        lcd.set_cursor(0, 0)
        lcd.print("Free:")
        col = 6
        for i in range(TOTAL_SLOTS):
            if not slots[i]["occupied"]:
                lcd.set_cursor(col, 0)
                lcd.print(f"S{i+1}")
                col += 3


# ======================== TELEGRAM ========================
def send_telegram_receipt(ticket):
    try:
        message = "\n".join(
            [
                "Ticket **CLOSED**",
                "",
                f"ID: {ticket['id']}",
                f"Slot: S{ticket['slot']}",
                f"Duration: {ticket['duration']:.1f} minutes",
                f"Fee: ${ticket['fee']:.2f}",
            ]
        )

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = ujson.dumps({"chat_id": CHAT_ID, "text": message})
        headers = {"Content-Type": "application/json"}

        response = urequests.post(url, data=data, headers=headers)

        if response.status_code == 200:
            print("Telegram receipt sent")
        else:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

        response.close()

    except Exception as e:
        print(f"Telegram error: {e}")


# ======================== WEB SERVER ========================
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    max_wait = 10

    while not wlan.isconnected() and max_wait > 0:
        print(".", end="")
        time.sleep(1)
        max_wait -= 1

    if not wlan.isconnected():
        print("\nWiFi connection failed!")
        return
    else:
        print("Connected!")
        ip = wlan.ifconfig()[0]
        print(f"IP: {ip}")
        return ip


def get_status_json():
    free_count = get_free_slot_count()
    occupied_count = TOTAL_SLOTS - free_count

    slots_data = []
    for i in range(TOTAL_SLOTS):
        s = slots[i]
        elapsed = int(time.time() - s["time_in"]) if s["occupied"] else 0
        slots_data.append(
            {
                "slot": i + 1,
                "occupied": s["occupied"],
                "id": s["assigned_id"] if s["occupied"] else None,
                "time_in": s["time_in"] if s["occupied"] else None,
                "elapsed": elapsed if s["occupied"] else 0,
            }
        )

    active_tickets = [
        {
            "id": s["assigned_id"],
            "slot": i + 1,
            "time_in": s["time_in"],
            "elapsed": int(time.time() - s["time_in"]),
        }
        for i, s in enumerate(slots)
        if s["occupied"]
    ]

    recent_tickets = [
        {
            "id": t["id"],
            "slot": t["slot"],
            "duration": round(t["duration"], 1),
            "fee": round(t["fee"], 2),
            "time_out": t["time_out"],
        }
        for t in reversed(ticket_history[-10:])
    ]

    return {
        "total": TOTAL_SLOTS,
        "free": free_count,
        "occupied": occupied_count,
        "status": "Available" if free_count > 0 else "FULL",
        "slots": slots_data,
        "active_tickets": active_tickets,
        "recent_tickets": recent_tickets,
    }


def web_page():
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Parking System</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f0f2f5; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                  color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .status-bar { display: flex; justify-content: space-around; margin-top: 15px; }
        .status-item { text-align: center; }
        .status-item h3 { font-size: 32px; margin: 5px 0; }
        .status-item p { opacity: 0.9; }
        .slots { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                 gap: 15px; margin-bottom: 20px; }
        .slot { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .slot.occupied { border-left: 5px solid #ef4444; }
        .slot.free { border-left: 5px solid #10b981; }
        .slot h3 { margin-bottom: 10px; }
        .slot-info { display: flex; flex-direction: column; gap: 8px; }
        .slot-info span { font-size: 14px; }
        .table-container { background: white; padding: 20px; border-radius: 10px;
                          box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }
        th { background: #f9fafb; font-weight: 600; }
        .badge { display: inline-block; padding: 4px 12px; border-radius: 12px;
                font-size: 12px; font-weight: 600; }
        .badge.success { background: #d1fae5; color: #065f46; }
        .badge.danger { background: #fee2e2; color: #991b1b; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚗 Smart Parking System</h1>
            <div class="status-bar">
                <div class="status-item">
                    <h3 id="total">3</h3>
                    <p>Total Slots</p>
                </div>
                <div class="status-item">
                    <h3 id="free">0</h3>
                    <p>Free</p>
                </div>
                <div class="status-item">
                    <h3 id="occupied">0</h3>
                    <p>Occupied</p>
                </div>
                <div class="status-item">
                    <span class="badge success" id="status">Available</span>
                </div>
            </div>
        </div>
        
        <div class="slots" id="slots"></div>
        
        <div class="table-container">
            <h2 style="margin-bottom: 15px;">🎫 Active Tickets</h2>
            <table id="activeTable">
                <thead>
                    <tr><th>ID</th><th>Slot</th><th>Time In</th><th>Elapsed</th></tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
        
        <div class="table-container">
            <h2 style="margin-bottom: 15px;">📋 Recent Closed Tickets</h2>
            <table id="recentTable">
                <thead>
                    <tr><th>ID</th><th>Slot</th><th>Duration</th><th>Fee</th><th>Time Out</th></tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
    </div>
    
    <script>
        function formatTime(timestamp) {
            return new Date(timestamp * 1000).toLocaleString();
        }
        
        function formatElapsed(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = seconds % 60;
            return mins + 'm ' + secs + 's';
        }
        
        async function updateDashboard() {
            try {
                const response = await fetch('/status');
                const data = await response.json();
                
                document.getElementById('total').textContent = data.total;
                document.getElementById('free').textContent = data.free;
                document.getElementById('occupied').textContent = data.occupied;
                
                const statusBadge = document.getElementById('status');
                statusBadge.textContent = data.status;
                statusBadge.className = 'badge ' + (data.status === 'FULL' ? 'danger' : 'success');
                
                const slotsDiv = document.getElementById('slots');
                slotsDiv.innerHTML = data.slots.map(s => `
                    <div class="slot ${s.occupied ? 'occupied' : 'free'}">
                        <h3>Slot ${s.slot}</h3>
                        <div class="slot-info">
                            <span><strong>Status:</strong> ${s.occupied ? '🔴 Occupied' : '🟢 Free'}</span>
                            ${s.occupied ? `
                                <span><strong>ID:</strong> ${s.id}</span>
                                <span><strong>Time In:</strong> ${formatTime(s.time_in)}</span>
                                <span><strong>Elapsed:</strong> ${formatElapsed(s.elapsed)}</span>
                            ` : ''}
                        </div>
                    </div>
                `).join('');
                
                const activeBody = document.querySelector('#activeTable tbody');
                activeBody.innerHTML = data.active_tickets.map(t => `
                    <tr>
                        <td>${t.id}</td>
                        <td>S${t.slot}</td>
                        <td>${formatTime(t.time_in)}</td>
                        <td>${formatElapsed(t.elapsed)}</td>
                    </tr>
                `).join('') || '<tr><td colspan="4" style="text-align:center;">No active tickets</td></tr>';
                
                const recentBody = document.querySelector('#recentTable tbody');
                recentBody.innerHTML = data.recent_tickets.map(t => `
                    <tr>
                        <td>${t.id}</td>
                        <td>S${t.slot}</td>
                        <td>${t.duration} min</td>
                        <td>$${t.fee.toFixed(2)}</td>
                        <td>${formatTime(t.time_out)}</td>
                    </tr>
                `).join('') || '<tr><td colspan="5" style="text-align:center;">No recent tickets</td></tr>';
                
            } catch (error) {
                console.error('Update failed:', error);
            }
        }
        
        updateDashboard();
        setInterval(updateDashboard, 3000);
    </script>
</body>
</html>"""
    return html


def start_server():
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)
    print("Web server running on port 80")

    while True:
        try:
            cl, addr = s.accept()
            request = cl.recv(1024).decode()

            if "GET /status" in request:
                response = ujson.dumps(get_status_json())
                cl.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
                cl.send(response)
            else:
                cl.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n")
                cl.send(web_page())

            cl.close()
        except Exception as e:
            print(f"Server error: {e}")
            try:
                cl.close()
            except:
                pass


# ======================== MAIN PROGRAM ========================
def main():
    print("Smart Parking System Starting...")

    if lcd:
        lcd.clear()
        lcd.set_cursor(0, 0)
        lcd.print("Initializing...")

    close_gate()
    ip = connect_wifi()

    if ip:
        print(f"\nAccess dashboard at: http://{ip}")

    update_lcd()

    # Start server in background (non-blocking simulation)
    import _thread

    _thread.start_new_thread(start_server, ())

    print("\nSystem Ready!")
    last_lcd_update = time.ticks_ms()

    while True:
        try:
            check_entry()
            update_slots()

            if time.ticks_diff(time.ticks_ms(), last_lcd_update) > 1000:
                update_lcd()
                last_lcd_update = time.ticks_ms()

            time.sleep(0.05)

        except KeyboardInterrupt:
            print("\nShutting down...")
            close_gate()
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)


# Run the system
if __name__ == "__main__":
    main()
