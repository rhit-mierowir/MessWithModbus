# modbus_server.py
import asyncio
import logging

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusDeviceContext,
)
from pymodbus.pdu.device import ModbusDeviceIdentification
from pymodbus.server import StartAsyncTcpServer

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

async def run_server():
    """Run Modbus TCP server."""
    log.info("Initializing Modbus data store")
    store = ModbusDeviceContext(
        hr=ModbusSequentialDataBlock(0, [17] * 100), # Holding registers (address 0-99)
        di=ModbusSequentialDataBlock(0, [15] * 100), # Discrete inputs (address 0-99)
        co=ModbusSequentialDataBlock(0, [True] * 100), # Coils (address 0-99)
        ir=ModbusSequentialDataBlock(0, [20] * 100)  # Input registers (address 0-99)
    )
    context = ModbusServerContext(devices=store, single=True)

    identity = ModbusDeviceIdentification(
        info_name={
            "VendorName": "Pymodbus",
            "ProductCode": "PM",
            "VendorUrl": "https://github.com/pymodbus-dev/pymodbus/",
            "ProductName": "Pymodbus Server",
            "ModelName": "Pymodbus Server",
            "MajorMinorRevision": "3.9.2",
        }
    )

    # Use a non-privileged port like 5020 (standard Modbus TCP is 502)
    address = ("0.0.0.0", 5020)
    log.info(f"Starting Modbus TCP server on {address[0]}:{address[1]}")
    server = await StartAsyncTcpServer(
        context=context, 
        identity=identity,  
        address=address,  
    )
    log.info("Server started. Use Ctrl+C to stop.")
    await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        log.info("Server stopped by user.")
