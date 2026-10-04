from drivers.modbus_ascii import ModbusASCII


MOTORS = {
    "LEFT": {
        "port": "/dev/ttyAMA0",
        "id": 11,
    },

    "RIGHT": {
        "port": "/dev/ttyAMA1",
        "id": 11,
    },

    "BRUSH": {
        "port": "/dev/ttyAMA4",
        "id": 11,
    },
}


for name, config in MOTORS.items():

    print("\n" + "=" * 40)
    print(f"Testing {name}")
    print(f"Port: {config['port']}")
    print(f"Slave ID: {config['id']}")
    print("=" * 40)

    driver = None

    try:
        driver = ModbusASCII(
            port=config["port"],
            slave_id=config["id"],
            baudrate=9600,
            timeout=0.5,
        )

        # Register 1 = slave address
        response = driver.read_registers(
            1,
            1
        )

        print(f"Slave ID response: {response}")

        if response[0] == config["id"]:
            print("✓ Communication OK")
        else:
            print(
                f"✗ Unexpected ID: {response[0]}"
            )

    except Exception as e:
        print(f"✗ Communication FAILED: {e}")

    finally:
        if driver:
            driver.close()
