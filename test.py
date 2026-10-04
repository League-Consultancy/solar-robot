from pymodbus.client import ModbusSerialClient
from pymodbus import FramerType

PORT = "/dev/ttyAMA0"
SLAVE_ID = 11

client = ModbusSerialClient(
    port=PORT,
    framer=FramerType.ASCII,
    baudrate=9600,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=2,
)

try:
    print(f"Opening {PORT}...")

    if not client.connect():
        print("FAILED: Could not open serial port")
        raise SystemExit(1)

    print("Serial port opened.")

    print("Reading RMCS register 40001...")

    result = client.read_holding_registers(
        address=0,
        count=1,
        device_id=SLAVE_ID,
    )

    if result.isError():
        print("RMCS returned an error:")
        print(result)
    else:
        print("Response received!")
        print("Register 40001:", result.registers[0])
        print("Hex:", f"0x{result.registers[0]:04X}")

finally:
    client.close()
    print("Serial port closed.")

