# modbus_server.py
import asyncio
import logging
import sys
from enum import Enum,IntEnum

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusDeviceContext,
)
from pymodbus.pdu.device import ModbusDeviceIdentification
from pymodbus.server import StartAsyncTcpServer

class mb_func_code(IntEnum):
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

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

async def updating_task(context):
    """Update values in server.

    This task runs continuously beside the server
    It will increment some values each two seconds.

    It should be noted that getValues and setValues are not safe
    against concurrent use.
    """
    func_code = mb_func_code.Read_A_HoldingReg
    # device_id = 0x00
    address = 0x00
    count = 6

    # set values to zero
    values = context.getValues(func_code, address, count=count)
    values = [0 for v in values]
    context.setValues(func_code, address, values)

    txt = (
        f"updating_task: started: initialised values: {values!s} at address {address!s}"
    )
    print(txt)
    log.debug(txt)

    # incrementing loop
    while True:
        await asyncio.sleep(2)

        values = context.getValues(func_code, address, count=count)
        values = [v + 1 for v in values]
        context.setValues(func_code, address, values)

        txt = f"updating_task: incremented values: {values!s} at address {address!s}"
        print(txt)
        log.debug(txt)


def setup_updating_server():
    """Run server setup."""
    # The datastores only respond to the addresses that are initialized
    # If you initialize a DataBlock to addresses of 0x00 to 0xFF, a request to
    # 0x100 will respond with an invalid address exception.
    # This is because many devices exhibit this kind of behavior (but not all)
    
    # Continuing, use a sequential block without gaps.
    device_context = ModbusDeviceContext(
        hr=ModbusSequentialDataBlock(0, [17]    * 100), # Holding registers (address 0-99)
        di=ModbusSequentialDataBlock(0, [False] * 100), # Discrete inputs (address 0-99)
        co=ModbusSequentialDataBlock(0, [True]  * 100), # Coils (address 0-99)
        ir=ModbusSequentialDataBlock(0, [20]    * 100)  # Input registers (address 0-99)
    )
    context = ModbusServerContext(devices=device_context, single=True)
    identity = ModbusDeviceIdentification(
        info_name={
            "VendorName": "RHIT_SD",
            "ProductCode": "FWS",
            "VendorUrl": "https://www.youtube.com/watch?v=epLMUuSlc38",
            "ProductName": "FakeWaterSensor",
            "ModelName": "Fake One",
            "MajorMinorRevision": "0.0.0",
        }
    )

    # Use a non-privileged port like 5020 (standard Modbus TCP is 502)
    address = ("0.0.0.0", 5020)
    log.info(f"Starting Modbus TCP server on {address[0]}:{address[1]}")
    server = StartAsyncTcpServer(
        context=context, 
        identity=identity,  
        address=address,
    )
    return server, device_context



async def run_server(modbus_server, context):
    """Start updating_task concurrently with the current task."""
    task = asyncio.create_task(updating_task(context)) # Run the updating task
    task.set_name("example updating task")
    await modbus_server  # start the server, run until it fails
    task.cancel() # Cancel the updating task


async def main():
    """Combine setup and run."""
    modbus_server, context = setup_updating_server()
    await run_server(modbus_server, context)


if __name__ == "__main__":
    try:
        asyncio.run(main(), debug=True)
    except KeyboardInterrupt:
        log.info("Server stopped by user.")
