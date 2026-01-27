# modbus_client.py
import asyncio
import logging
from returns.result import Result, Success, Failure
from returns.maybe import Maybe, Some, Nothing
from returns.future import Future

from pymodbus.pdu import ModbusPDU
from pymodbus.client import AsyncModbusTcpClient
from contextlib import asynccontextmanager
from enum import Enum, auto

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.ERROR)

SERVER_IP = "127.0.0.1" # Connect to localhost
SERVER_PORT = 5020

@asynccontextmanager
async def modbus_client(server_ip:str=SERVER_IP, server_port:int=SERVER_PORT):
    
    client = AsyncModbusTcpClient(server_ip, port=server_port)
    log.info(f"Connecting to Modbus server at {server_ip}:{server_port}")
    await client.connect()

    if not client.connected:
        log.error("Failed to connect to the Modbus server.")
        return
    else:
        log.info("Successfully connected to the server.")
    
    try:
        yield client

    except KeyboardInterrupt as e:
        log.info(f"Program stopped by user: {e}")
    except Exception as e:
        log.error(f"An error occurred during Modbus operations: {e}")
        #raise e
    finally:
        log.info("Closing connection.")
        client.close()

def _find_errors(result:ModbusPDU) -> Result[ModbusPDU,ModbusPDU]:
    if result.isError():
        return Failure(result)
    return Success(result)

def _log_errors(result:Result[ModbusPDU,ModbusPDU]) -> Maybe[ModbusPDU]:
    match result:
        case Success(pdu):
            log.debug(f"Modbus Transaction Success: {result}")
            return Some(pdu)
        case Failure(pdu):
            log.error(f"Modbus Transaction Error: {result}")
            return Nothing
        
def handle_errors(result:ModbusPDU) -> Maybe[ModbusPDU]:
    return _log_errors(_find_errors(result))

async def upper_sensor_is_triggered(client:AsyncModbusTcpClient) -> Maybe[bool]:
    log.debug("Reading Status of upper water sensor")
    return handle_errors(await client.read_discrete_inputs(address=0, count=1)).bind(
        lambda pdu: Some(pdu.bits[0]) if len(pdu.bits) >= 1 else Nothing
    )

async def lower_sensor_is_triggered(client:AsyncModbusTcpClient) -> Maybe[bool]:
    log.debug("Reading Status of lower water sensor")
    return handle_errors(await client.read_discrete_inputs(address=1, count=1)).bind(
        lambda pdu: Some(pdu.bits[0]) if len(pdu.bits) >= 1 else Nothing
    )

async def set_pump(client:AsyncModbusTcpClient,activate:bool) -> bool:
    "Lets you set the water pump to be active or deactivated. Return True if successfully, False if error."
    log.debug(f"Turning Pump {'ON' if activate else 'OFF'}")
    return handle_errors(await client.write_coil(address=0, value=activate)).bind(
        lambda pdu: Some(True) #Get rid of pdu because not useful
    ).value_or(False)

async def pump_is_active(client:AsyncModbusTcpClient) -> Maybe[bool]:
    "Returns true if the water pump is active"
    log.debug("Reading Status of Pump")
    return handle_errors(await client.read_coils(address=0, count=1)).bind(
        lambda pdu: Some(pdu.bits[0]) if len(pdu.bits) >= 1 else Nothing
    )

def boolean_to_text(reading:Maybe[bool])->str:
    match reading:
        case Some(r):
            return "ON" if r else "OFF"
        case Maybe.empty: #Nothing
            return "ERROR"

def string_to_boolean(string:str)->Maybe[bool]:
    match string.strip().lower():
        case "1":
            return Some(True)
        case "0":
            return Some(False)
        case _:
            return Nothing

async def print_statuses(client:AsyncModbusTcpClient) -> None:
    log.info("Rendering a status page.")
    print(  f"Upper Water Level: {boolean_to_text(await upper_sensor_is_triggered(client))}\n"
          + f"Lower Water Level: {boolean_to_text(await lower_sensor_is_triggered(client))}\n"
          + f"Water Pump:        {boolean_to_text(await pump_is_active(client))}")

async def request_and_perform_user_input(client:AsyncModbusTcpClient) -> None:
    request = input(
        "="*25+"[ Commands Available ]"+"="*25+"\n"
        +"Update Status: [Enter]"+"\n"
        +"Water Pump:    p[Enter]"+"\n"
        +"> "
    )
    match request.lower():
        case "p" | "pump":
            request = input("Decide whether to activate or deactivate the pump. \n[1] to activate [0] to deactivate\n> ")
            match string_to_boolean(request):
                case Maybe.empty:
                    print(f"Could not understand request ({request}). Canceling.")
                    return
                case Some(val):
                    successful_send = await set_pump(client,activate=val)
                    print(f"{'Successfully' if successful_send else 'Unsuccessfully'} turned the water pump {'ON' if val else 'OFF'}.")     
        case _:
            return

async def initial_test_script(client):
    "A Script used to verify that the modbus protocol worked by printint to the screen. To be used durrins assorted debugging."

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
        log.info(f"Read Register 10: {rr_coils.registers}")

    await asyncio.sleep(1)
    
    # 4. Write Single Register (address 20, value 1234)
    log.info("Attempting to write single register...")
    rq_reg = await client.write_register(address=4, value=1234)
    if rq_reg.isError():
        log.error(f"Modbus Error writing register: {rq_reg}")
    else:
        log.info(f"Wrote Holding Register 4: 1234")
        log.info(f"Read Registers: {rr_coils.registers}")
        log.info(f"Read Coils: {rr_coils.bits}")

    await asyncio.sleep(1)

    # 5. Read Input Registers (address 5, count 3)
    log.info("Attempting to read input registers...")
    rr_ir = await client.read_input_registers(address=5, count=3)
    if rr_ir.isError():
        log.error(f"Modbus Error reading input registers: {rr_ir}")
    else:
        log.info(f"Read Input Registers (5-7): {rr_ir.registers}")
        log.info(f"Read bits: {rr_ir.bits}")

async def run_client():

    async with modbus_client(SERVER_IP,SERVER_PORT) as client:

        if False: # Set True for testing
            initial_test_script(client)
            return
        
        while True:
            await print_statuses(client)
            await request_and_perform_user_input(client)

        
        

    

if __name__ == "__main__":
    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        log.info(f"Program stopped by user. [ctrl+C]")
