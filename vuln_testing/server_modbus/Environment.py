# modbus_server.py
import asyncio
import logging
import sys
from enum import Enum,IntEnum
from dataclasses import dataclass, field

try: 
    from pymodbus.datastore import (
        ModbusSequentialDataBlock,
        ModbusServerContext,
        ModbusDeviceContext,
    )
    from pymodbus.pdu.device import ModbusDeviceIdentification
    from pymodbus.server import StartAsyncTcpServer
    
except ImportError as e:
    raise ImportError("You need to install Pymodbus to run this 'pip install pymodbus'")

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger()
log.setLevel(logging.INFO)

@dataclass(frozen=True)
class SimulationParameters:
    "The parameters required to run the simulation. Uses an abstract 'level' to represent the volume of the liquid (e.g. Liters, Gallons, etc)."

    upper_sensor_activation_level: float
    "Above this level, the upper_sensor is active (1)"
    lower_sensor_activation_level: float
    "Above this level, the lower_sensor is active (1)"
    leak_rate_per_sec: float
    "How much the level decreases per second by leaking from container. (should be positive)"
    pump_rate_per_sec: float
    "How much the level increases per second when the pump is active. (should be positive)"

    initial_level: float = field(default=0)
    "Quantity of Liquid in container initially"
    min_level: float = field(default=0)
    "Minimum level of liquid in container before it can leak no more water"
    max_level: float = field(default=100)
    "Maximum level of liquid in container before it overflows"

class Simulation:
    def __init__(self, parameers:SimulationParameters, timestep_length_in_sec:float, pump_active:bool=True, leak_active:bool=True):
        self._parameters                = parameers
        self._timestep_sec              = timestep_length_in_sec
        self._pump_rate_per_step:float  = self._parameters.pump_rate_per_sec * self._timestep_sec
        self._leak_rate_per_step:float  = self._parameters.leak_rate_per_sec * self._timestep_sec

        self._current_level:float       = self._parameters.initial_level
        self._pump_is_active:bool       = False
        self._leak_is_active:bool       = True
        
        self._is_overflowing:bool       = self._parameters.initial_level >= self._parameters.max_level
        self._is_empty:bool             = self._parameters.min_level >= self._parameters.initial_level
        self._is_increasing:bool        = False
        self._is_decreasing:bool        = False

    def get_timestep_length_in_seconds(self)->float:
        return self._timestep_sec
    
    def get_current_level(self)->float:
        return self._current_level

    def is_overflowing(self)->bool:
        return self._is_overflowing
    
    def is_empty(self)->bool:
        return self._is_empty
    
    def is_increasing(self)->bool:
        return self._is_increasing
    
    def is_decreasing(self)->bool:
        return self._is_decreasing
    
    def is_upper_sensor_active(self)->bool:
        return self._current_level >= self._parameters.upper_sensor_activation_level
    
    def is_lower_sensor_active(self)->bool:
        return self._current_level >= self._parameters.lower_sensor_activation_level
    
    def set_pump(self,activate:bool):
        self._pump_is_active = activate
    
    def is_pump_active(self)->bool:
        return self._pump_is_active
    
    def set_leak(self,activate:bool):
        self._leak_is_active = activate
    
    def is_leak_active(self)->bool:
        return self._leak_is_active
    
    def perform_timestep(self):

        #Initialize Statistic Variables
        self._is_decreasing = False
        self._is_increasing = False
        self._is_overflowing = False
        self._is_empty = False

        # Find Water Level change this timestep (assume on for entire timestep if on now, otherwise off)
        level_change = 0

        if self._leak_is_active:
            level_change -= self._leak_rate_per_step

        if self._pump_is_active:
            level_change += self._pump_rate_per_step
        
        if level_change > 0:
            self._is_increasing = True
        elif level_change < 0:
            self._is_decreasing = True

        self._current_level += level_change

        # Constrain level to container

        if self._current_level <= self._parameters.min_level:
            self._current_level = self._parameters.min_level
            self._is_empty = True

        if self._current_level >= self._parameters.max_level:
            self._current_level = self._parameters.max_level
            self._is_overflowing = True

def log_sim_events(sim:Simulation):
    log.info(f"Simulated Tank Level = {sim.get_current_level()}")

    if sim.is_empty():
        log.info("Simulated Tank Is Empty")
    if sim.is_overflowing():
        log.info("Simulated Tank Is Overflowing")

async def simulate(context, sim:Simulation):
    """
    Proforms the provided simulation asyncronously, 
    and applies it to the current values in the modbus server. 
    """
    delay = sim.get_timestep_length_in_seconds()


    context.setValues(mb_func_code.Read_D_Coils, address=0, values=[sim.is_pump_active()])

    while True:
        upper_sensor_reading:bool = sim.is_upper_sensor_active()
        context.setValues(mb_func_code.Read_D_Contacts, address=0, values=[upper_sensor_reading])

        lower_sensor_reading:bool = sim.is_lower_sensor_active()
        context.setValues(mb_func_code.Read_D_Contacts, address=1, values=[lower_sensor_reading])

        await asyncio.sleep(delay)

        sim.set_leak(True) # Always True For us
        sim.set_pump(context.getValues(mb_func_code.Read_D_Coils, address=0, count=1)[0]) # Depends on current setting of pump
        
        sim.perform_timestep()

        log_sim_events(sim)


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


async def prepare_simulation(context, timestep_length_sec:float=0.5):
    
    return 



async def run_server(modbus_server, context):
    """Start updating_task concurrently with the current task."""


    param = SimulationParameters(
        initial_level=0,
        min_level=0,
        max_level=100,
        upper_sensor_activation_level=75,
        lower_sensor_activation_level=25,
        leak_rate_per_sec=5,
        pump_rate_per_sec=10
    )
    sim = Simulation(parameers=param,
                     timestep_length_in_sec=0.5,
                     pump_active=False,
                     leak_active=True
                     )
    sim_task = asyncio.create_task(simulate(context,sim))
    sim_task.set_name("Task Simulating Real Environment")

    # task = asyncio.create_task(updating_task(context)) # Run the updating task
    # task.set_name("example updating task")

    await modbus_server  # start the server, run until it fails

    # task.cancel() # Cancel the updating task
    sim_task.cancel()
    


async def main():
    """Combine setup and run."""
    modbus_server, context = setup_updating_server()
    await run_server(modbus_server, context)

def run_environment():
    "This is how you can run the environment from an external server"
    try:
        asyncio.run(main(), debug=True)
    except KeyboardInterrupt:
        log.info("Server stopped by user.")


if __name__ == "__main__":
    run_environment()
