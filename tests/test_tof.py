from sensors.tof import ToF


tof = ToF(bus_number=2)

tof.close()

print("VL53L0X I2C communication OK")