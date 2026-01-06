# modbus_client.py
import asyncio
import logging

from pymodbus.client import AsyncModbusTcpClient

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

SERVER_IP = "127.0.0.1" # Connect to localhost
SERVER_PORT = 5020

async def run_client():
    client = AsyncModbusTcpClient(SERVER_IP, port=SERVER_PORT)

    log.info(f"Connecting to Modbus server at {SERVER_IP}:{SERVER_PORT}")
    await client.connect()

    if not client.connected:
        log.error("Failed to connect to the Modbus server.")
        return

    log.info("Successfully connected to the server.")

    try:
        # 1. Read Holding Registers (address 0, count 5)
        log.info("Attempting to read holding registers...")
        rr = await client.read_holding_registers(address=0, count=5)
        if rr.isError():
            log.error(f"Modbus Error reading holding registers: {rr}")
        else:
            log.info(f"Read Holding Registers (0-4): {rr.registers}")

        await asyncio.sleep(1)

        # 2. Write Single Coil (address 10, value True)
        log.info("Attempting to write single coil...")
        rq = await client.write_coil(address=10, value=True)
        if rq.isError():
            log.error(f"Modbus Error writing coil: {rq}")
        else:
            log.info(f"Wrote Coil 10: True")

        await asyncio.sleep(1)

        # 3. Read Coils (address 10, count 1)
        log.info("Attempting to read coils...")
        rr_coils = await client.read_coils(address=10, count=1)
        if rr_coils.isError():
            log.error(f"Modbus Error reading coils: {rr_coils}")
        else:
            log.info(f"Read Coil 10: {rr_coils.bits[0]}")

        await asyncio.sleep(1)

        # 4. Write Single Register (address 20, value 1234)
        log.info("Attempting to write single register...")
        rq_reg = await client.write_register(address=4, value=1234)
        if rq_reg.isError():
            log.error(f"Modbus Error writing register: {rq_reg}")
        else:
            log.info(f"Wrote Holding Register 4: 1234")

        await asyncio.sleep(1)

        # 5. Read Input Registers (address 5, count 3)
        log.info("Attempting to read input registers...")
        rr_ir = await client.read_input_registers(address=5, count=3)
        if rr_ir.isError():
            log.error(f"Modbus Error reading input registers: {rr_ir}")
        else:
            log.info(f"Read Input Registers (5-7): {rr_ir.registers}")
        

    except Exception as e:
        log.error(f"An error occurred during Modbus operations: {e}")
    finally:
        log.info("Closing connection.")
        client.close()

if __name__ == "__main__":
    asyncio.run(run_client())
