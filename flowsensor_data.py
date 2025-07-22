import RPi.GPIO as GPIO
import time
import firebase_admin
from firebase_admin import credentials, db

# GPIO setup
FLOW_SENSOR_PIN = 17  # GPIO 17 (Pin 11)
GPIO.setmode(GPIO.BCM)
GPIO.setup(FLOW_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Firebase setup
cred = credentials.Certificate("/home/pi/serviceAccountKey.json")  # Change to your path
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://your-project.firebaseio.com/'  # Replace with your DB URL
})

flow_rate = 0
pulse_count = 0

def pulse_callback(channel):
    global pulse_count
    pulse_count += 1

GPIO.add_event_detect(FLOW_SENSOR_PIN, GPIO.FALLING, callback=pulse_callback)

def calculate_flow():
    global pulse_count
    pulses = pulse_count
    pulse_count = 0
    # Conversion depends on your sensor spec (YF-S201: 450 pulses per liter)
    flow = (pulses / 450.0) * 60  # Liters per minute (L/min)
    return flow

try:
    while True:
        time.sleep(5)  # Measure every 5 seconds
        flow_rate = calculate_flow()
        print(f"Flow Rate: {flow_rate:.2f} L/min")

        # Upload to Firebase
        ref = db.reference('flow_data')
        ref.push({
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
            'flow_rate': round(flow_rate, 2)
        })

except KeyboardInterrupt:
    GPIO.cleanup()
    print("Stopped by user")dat
