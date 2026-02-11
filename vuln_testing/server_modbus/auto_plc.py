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
from dataclasses import dataclass, field

from datetime import datetime

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",  # optional custom time format
)
log = logging.getLogger()
log.setLevel(logging.ERROR)

SERVER_IP = "172.16.141.136" # Connect to server
SERVER_PORT = 5020
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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


@dataclass
class environment_state():
    pump_is_active: bool = field(default=False)
    lower_sensor_is_triggered: bool = field(default=False)
    upper_sensor_is_triggered: bool = field(default=False)

async def update_state(client:AsyncModbusTcpClient, state:environment_state) -> None:
    match await pump_is_active(client):
        case Maybe.empty:
            print(f"{now} UPDATE:FAILED: MODBUS Couldn't get pump status")
        case Some(reading):
            state.pump_is_active = reading
    
    match await upper_sensor_is_triggered(client):
        case Maybe.empty:
            print(f"{now} UPDATE:FAILED: MODBUS Couldn't get upper sensor status")
        case Some(reading):
            state.upper_sensor_is_triggered = reading
    
    match await lower_sensor_is_triggered(client):
        case Maybe.empty:
            print(f"{now} UPDATE:FAILED: MODBUS Couldn't get lower sensor status")
        case Some(reading):
            state.lower_sensor_is_triggered = reading

    print(f"{now} UPDATE: Updated sensor state cache.")

async def flip_pump_if_pass_trigger(client:AsyncModbusTcpClient, state:environment_state) -> None:

    async def flip_pump_if_lower(lower_triggered:bool):
        # Turn on pump if the lower sensor is not triggered and the pump is off
        if (not lower_triggered) and (not state.pump_is_active):
            success = await set_pump(client, activate=True)
            if success:
                print(f"{now} SUCCESS: Turned ON pump by LLS")
                state.pump_is_active = True
            else:
                print(f"{now} FAILED: MODBUS couldn't turn on pump.")

    async def flip_pump_if_upper(upper_triggered:bool):
        # Turn off pump if the upper sensor is triggered and the pump is on
        if upper_triggered and state.pump_is_active:
            success = await set_pump(client, activate=False)
            if success:
                print(f"{now} SUCCESS: Turned OFF pump by ULS")
                state.pump_is_active = False
            else:
                print(f"{now} FAILED: MODBUS couldn't turn off pump.")
        

    match await lower_sensor_is_triggered(client):
        case Maybe.empty:
            print(f"{now} FAILED: MODBUS couldn't read lower sensor.")
        case Some(reading):
            await flip_pump_if_lower(reading)
            state.lower_sensor_is_triggered = reading

    match await upper_sensor_is_triggered(client):
        case Maybe.empty:
            print(f"{now} FAILED: MODBUS couldn't read upper sensor.")
        case Some(reading):
            await flip_pump_if_upper(reading)
            state.upper_sensor_is_triggered = reading


async def run_client():
    DELAY_SEC = 30
    DELAY_UNTIL_UPDATE = range(DELAY_SEC*167) #167 was a coefficient experimentally determined to correspont to ~1sec

    async with modbus_client(SERVER_IP,SERVER_PORT) as client:
        
        state = environment_state()
        await update_state(client,state)

        while True:
            for _ in DELAY_UNTIL_UPDATE:
                await flip_pump_if_pass_trigger(client,state)
                #print(f"__ {_}")
            await update_state(client,state)

            

        
        

    

if __name__ == "__main__":
    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        log.info(f"Program stopped by user. [ctrl+C]")
