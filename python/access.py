import datetime
from datetime import date
import RPi.GPIO as GPIO
import json
import os
import requests
from RPLCD.i2c import CharLCD
import time

code=[]             # Codes can be keycodes or fobcodes from keypad or RFID
resetTime = 0       # Unix time to reset screen to main
screen = 0          # Screen number to show
blinkUntil = 0      # Unix time to blink screen until
blinkTimer = 0      # 
timeout = 20        # Seconds until screens reset
name=""             # User who just entered
lockPin= 11         # Which pin to unlock door
error = False

# Setup Devices
lcd = CharLCD('PCF8574', 0x27)
KEYPAD = [
  ["1","2","3"],
  ["4","5","6"],
  ["7","8","9"],
  ["*","0","#"]
]
ROW_PINS = [25, 8, 7, 1]
COL_PINS = [16, 20, 21]

GPIO.setmode(GPIO.BCM)
GPIO.setup(lockPin, GPIO.OUT)

for pin in ROW_PINS:
  GPIO.setup(pin, GPIO.OUT)

for pin in COL_PINS:
  GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Process input from keypad
def keypadHandler(key):
  global code

  # Give user more time with each press
  setReset(True) 
  print(key)

  if (key=="#"): # enter
    validateCode()
  elif (key=="*"): # clear
    code = []
  else:
    code.append(int(key))

def checkKeypad():
  global KEYPAD

  keypadBounce = 0

  for idr, row in enumerate(ROW_PINS):
    GPIO.output(row, GPIO.HIGH) # Row HIGH
    for idc, col in enumerate(COL_PINS): # Read COLs
      if(GPIO.input(col) == 1):

        # Debounce short presses
        while(GPIO.input(col) == 1):
          keypadBounce += 1
          time.sleep(0.01)

        if(keypadBounce > 10):
          keypadHandler((KEYPAD[idr][idc]))

        # Wait for release
        while(GPIO.input(col) == 1):
          pass

        # Reset debounce
        keypadBounce = 0;

    GPIO.output(row, GPIO.LOW)


# Custom Characters for LCD


# Error Icon
lcd.create_char(0, (
  0x1F,
  0x11,
  0x17,
  0x11,
  0x17,
  0x11,
  0x1F,
  0x00
))

# Play Icon
lcd.create_char(1, (
  0x10,
  0x18,
  0x1C,
  0x1E,
  0x1E,
  0x1C,
  0x18,
  0x10
))

# Exclamation mark in filled box
lcd.create_char(2, (
  0x1F,
  0x1B,
  0x1B,
  0x1B,
  0x1B,
  0x1F,
  0x1B,
  0x1F
))

# :)
lcd.create_char(3, (
  0x00,
  0x0A,
  0x0A,
  0x00,
  0x11,
  0x11,
  0x0E,
  0x00
))

# Kind of a cloud with check mark
lcd.create_char(4, (
  0x0C,
  0x17,
  0x11,
  0x1F,
  0x00,
  0x02,
  0x14,
  0x08
))


#
# Begin Methods 
#

# Assumes a fail-secure lock where HIGH means unlocked
def releaseLock():
  lcd.clear()
  lcd.cursor_pos = (0,0)
  lcd.write_string("\x02 Unlocking")
  GPIO.output(lockPin, GPIO.LOW)
  time.sleep(0.5)
  GPIO.output(lockPin, GPIO.LOW)

def setScreen(s):
  global screen
  lcd.clear()
  screen = s

def grantAccess():
  releaseLock()
  setScreen(1)
  setReset(True)
  setBlink()

def denyAccess():
  lcd.clear()
  lcd.cursor_pos = (0,0)
  lcd.write_string("\x02 Invalid Code")
  time.sleep(3)

def logEntry(fobId):
  lcd.clear()
  lcd.cursor_pos = (0,0)
  lcd.write_string("\x02 Logging...")
  url = 'https://members.hacman.org.uk/acs/activity'
  headers = {'ApiKey': os.environ['DEVICE_API_KEY']}
  data = {'tagId': fobId, 'device': 'keypad', 'occurredAt':'0'}

  requests.request(
    "POST",
    url,
    headers=headers,
    data=data,
    timeout=2
  )

# Validates the stored code against members.csv
def validateCode(keypad=True):
  global code, screen, name, error

  allowAccess = False
  
  # Keycodes stored as fobcodes that start with ff
  # Fobs do not ever start with ff
  prepend = ''
  if(keypad):
    prepend = 'ff'

  fullCode  = prepend + ''.join(map(str,code))

  try:
    with open('../members.csv', 'r') as members_f:
      for member in members_f.readlines():
        record = member.strip().split(',')
        accessCode = record[0].lower()
        username = record[1].lower()

        if(accessCode == fullCode):
          allowAccess = True
          name = username
  except:
    error = True
    print("Error parsing members.csv")

  if(allowAccess):
    grantAccess()
    logEntry(fullCode)
  else:
    denyAccess()
  lcd.clear()
  code=[]


# Screen reset (go back to main after so many seconds)
def setReset(force=False):
  global resetTime, timeout

  if(resetTime == 0 or force==True):
    resetTime = time.time() + timeout

def checkReset():
  global resetTime, screen, code

  if(resetTime > 0 and time.time() > resetTime):
    setScreen(0)
    resetTime = 0
    code = []

#
# Blinking the screen backlight
#
def setBlink():
  global blinkUntil, timeout
  blinkUntil = time.time() + timeout

def checkBlink():
  global blinkUntil, blinkTimer, error

  if(blinkUntil > 0 or error):
    if(blinkUntil > time.time() or error):
      decis = round(time.time() * 10)
      if(decis % 50 < 5  and blinkTimer == 0):
        blinkTimer = decis
        lcd.backlight_enabled = False
      if(decis - blinkTimer > 2):
        blinkTimer = 0
        lcd.backlight_enabled = True
    else:
      blinkUntil = 0
      lcd.backlight_enabled = True

#
# Blinking icon top left to indicate the system is running
# Prints over some other screens, e.g. Home
#
def statusIcon():
  sec = int(time.time())
  lcd.cursor_pos = (0,0)
  if((sec % 2) == 0):
    lcd.write_string('\x01')
  else:
    lcd.write_string(' ')

  lcd.cursor_pos = (1,0)
  if(error):
    lcd.write_string('\x02')
    lcd.write_string('\x00')

#
# Screens
#
def homeScreen():
  global error

  sec = int(time.time())
  lcd.cursor_pos = (0,1)
  lcd.write_string('DOORBOT')

  lcd.cursor_pos = (0,11)
  if(error):
    lcd.write_string('ERROR')
  else:
    lcd.write_string('READY')

  for x in range(1,6):
    lcd.cursor_pos = (1, x + 10)
    if (sec % 6  == x):
      lcd.write_string('~')
    else:
      lcd.write_string(' ')

def keypadScreen():
  lcd.cursor_pos = (0,1)
  lcd.write_string('KEYPAD   IN-USE')
  lcd.cursor_pos = (1,0)
  lcd.write_string('[')
  for x in code:
    lcd.write_string('*')
  lcd.write_string(']')

def welcomeScreen():
  global name
  lcd.cursor_pos = (0,1)
  lcd.write_string('Welcome,     \x03')
  lcd.cursor_pos = (1,1)
  lcd.write_string(name or 'hacker')


#
# RUN!
#
while True:
  if(screen == 0):
    if(len(code) == 0):
      homeScreen()
    else:
      keypadScreen()
      setReset()
  elif(screen == 1):
    welcomeScreen()
  else:
    lcd.cursor_pos = (1,0)
    lcd.write_string('\x02 Unknown state!')

  statusIcon()
  checkReset()
  checkBlink()
  checkKeypad()