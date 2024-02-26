import sys
import time
import RPi.GPIO as gpio

def read_jedec_file(path):
    array = ["0"] * 132 * 64
    for line in open(path):
        if line.startswith("*L"):
            base = int(line[2:7])
            data = line[8:].strip()
            size = len(data)
            array[base:base+size] = data

    # Logic matrix fuse data.
    matrix_data = [
        "".join([
            array[column*44+row]
            for column in range(132)
        ])
        for row in range(44)
    ]

    # Macrocell configuration fuse data, 2 per port.
    olmc_data = "".join([
        array[5808+2*port+1] + array[5808+2*port]
        for port in range(10)
    ])

    return matrix_data, olmc_data

# GPIO pin assignments (see schematic for reference).
PROGRAM     = 14    # Enable programming mode (+12V to chip pin 2).
WRITE       = 15    # Program R/W toggle (chip pin 3).
ERASE       = 23    # Erase mode (chip pins 4,6,7,9)
ACCESS_OLMC = 18    # Access output configuration bits (chip pin 8).
CLOCK       = 24    # Serial clock (chip pin 10).
DATA_IN     = 15    # Serial data in (chip pin 11).
DATA_OUT    = 7     # Serial data out (chip pin 14).
STROBE      = 8     # Strobe (chip pin 13).

# Exchange a data bit with the device.
def exchange(out=0):
    _in = gpio.input(DATA_OUT)
    gpio.output(CLOCK, False)
    gpio.output(DATA_IN, out != 0)
    gpio.output(CLOCK, True)
    return _in

# Pulse 
def strobe(duration=0):
    gpio.output(STROBE, False)
    if duration > 0:
        time.sleep(duration)
    gpio.output(STROBE, True)

def setup_gpio():
    gpio.setmode(gpio.BCM)
    gpio.setwarnings(False)
    for pin in [PROGRAM, WRITE, ACCESS_OLMC, ERASE, CLOCK, DATA_IN, STROBE]:
        gpio.setup(pin, gpio.OUT)
        gpio.output(pin, False)
    gpio.setup(DATA_OUT, gpio.IN)

def write(matrix_data, olmc_data):
    # Enter programming mode.
    time.sleep(.005)
    gpio.output(CLOCK, True)
    gpio.output(STROBE, True)
    time.sleep(.005)
    gpio.output(PROGRAM, True)
    time.sleep(.005)

    # Enable write mode.
    gpio.output(WRITE, True)
    gpio.output(ACCESS_OLMC, False)
    gpio.output(ERASE, False)

    # Erase the chip.
    gpio.output(ERASE, True)
    time.sleep(.010)
    strobe(.03)
    time.sleep(.010)
    gpio.output(ERASE, False)

    # Program logic matrix fuses.
    for row, row_data in enumerate(matrix_data):
        # Send in the data bits to write.
        for bit in row_data:
            exchange(bit != "0")
        # Send in the row address to write.
        for i in range(5, -1, -1):
            exchange((row >> i) & 1)
        # Perform write.
        strobe(.005)
        time.sleep(.010)
    print()

    # Program macrocell configuration fuses.
    gpio.output(ACCESS_OLMC, True)
    for bit in olmc_data:
        exchange(bit != "0")
    strobe(.005)
    time.sleep(.010)
    gpio.output(ACCESS_OLMC, False)

    # Write the last row (disables power-down mode).
    for k in range(132):
        exchange(False)
    for i in range(5, -1, -1):
        exchange((59 >> i) & 1)
    strobe(.005)
    time.sleep(.010)

    # Exit write mode.
    gpio.output(WRITE, False)
    gpio.output(DATA_IN, False)

    # Leave programming mode.
    gpio.output(PROGRAM, False)
    time.sleep(.005)
    gpio.output(STROBE, False)
    gpio.output(CLOCK, False)
    time.sleep(.005)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("usage: %s <jedec-file>" % sys.argv[0])
        sys.exit(-1)

    try:
        matrix_data, olmc_data = read_jedec_file(sys.argv[1])

        setup_gpio()
        print("Press Enter to write image, or Ctrl-C to abort.")
        input()
        write(matrix_data, olmc_data)
        print("Complete.")

    except KeyboardInterrupt:
        print("Aborted.")
