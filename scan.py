from pymodbus.client import ModbusSerialClient
from pymodbus import FramerType

PORT = "/dev/ttyAMA0"

client = ModbusSerialClient(
    port=PORT,
    framer=FramerType.ASCII,
    baudrate=9600,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=0.15,
)

if not client.connect():
    print("Could not open UART")
    raise SystemExit(1)

print("Scanning RMCS slave IDs 1-247...")

found = []

for slave_id in range(1, 248):
    try:
        result = client.read_holding_registers(
            address=0,
            count=1,
            device_id=slave_id,
        )

        if not result.isError():
            print(
                f"FOUND slave ID {slave_id}: "
                f"40001 = {result.registers[0]} "
                f"(0x{result.registers[0]:04X})"
            )
            found.append(slave_id)

    except Exception:
        pass

client.close()

print("\nScan complete.")
print("Found:", found)

