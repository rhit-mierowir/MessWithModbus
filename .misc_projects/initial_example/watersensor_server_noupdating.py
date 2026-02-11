# modbus_server.py
import asyncio
import logging
from enum import Enum,IntEnum

class func_code(IntEnum):
    # D -> Discrete (boolean)  # A -> Analog (multiple booleans/register)
    # From Table Here: https://www.se.com/us/en/faqs/FA168406/
    Read_D_Coils            = 1
    WriteOne_D_Coils        = 5
    WriteMany_D_Coils       = 15
    Read_D_Contacts         = 2
    Read_A_InputReg         = 4
    Read_A_HoldingReg       = 3
    WriteOne_A_HoldingReg   = 6
    WriteMany_A_HoldingReg  = 16

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

sensor_registers = ModbusDeviceContext(
        hr=ModbusSequentialDataBlock(0, [17] * 100), # Holding registers (address 0-99)
        di=ModbusSequentialDataBlock(0, [False] * 100), # Discrete inputs (address 0-99)
        co=ModbusSequentialDataBlock(0, [True] * 100), # Coils (address 0-99)
        ir=ModbusSequentialDataBlock(0, [20] * 100)  # Input registers (address 0-99)
    )

async def test_using_registers(registers: ModbusDeviceContext):
    """ Try to get values out of the register for general use. """
    log.info("Started Interpreting registers")
    while True:
        result = await registers.async_getValues(func_code.Read_A_HoldingReg,0,3)
        log.info(f"Read Values: {result}")
        asyncio.sleep(1)

async def run_server(registers: ModbusDeviceContext):
    """Run Modbus TCP server."""
    log.info("Initializing Modbus data store")
    store = registers
    context = ModbusServerContext(devices=store, single=True)

    identity = ModbusDeviceIdentification(
        info_name={
            "VendorName": "RHIT_SD",
            "ProductCode": "FWS",
            "VendorUrl": "https://www.youtube.com/watch?v=epLMUuSlc38",
            "ProductName": "FakeWaterSensor",
            "ModelName": "Fake One",
            "MajorMinorRevision": "0.0.1",
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
        asyncio.run(run_server(sensor_registers))
    except KeyboardInterrupt:
        log.info("Server stopped by user.")
