from drivers.modbus_ascii import ModbusASCII

# Change this to the UART connected to the driver
PORT = "/dev/ttyAMA0"

# Slave ID configured on the driver
SLAVE_ID = 1


uart = ModbusASCII(
    port=PORT,
    slave_id=SLAVE_ID
)

try:

    print("Testing UART communication...")
    print(f"Port      : {PORT}")
    print(f"Slave ID  : {SLAVE_ID}")

    # Register 1 = Slave Address
    value = uart.read_registers(1, 1)[0]

    print()
    print("Communication successful!")
    print(f"Driver Slave ID = {value}")

except Exception as e:

    print()
    print("COMMUNICATION FAILED")
    print(type(e).__name__)
    print(e)

finally:

    uart.close()