# Overview

This is primarily for my Senior Design project and investigating how to use modbus using the scapy python library to emulate this traffic in a python script. 

This is just a place to house those scripts so I can point to them as needed.

# How To Run
1. Install [Poetry](https://python-poetry.org/docs/)
2. Clone this repository and `cd` into it
3. Initialize dependancies with poetry with: `poetry install`
4. Run the code you want to run via poetry: `poetry run <the file> --add-any-command-line-arguments`

To add dependancies to this project, write:
``` bash
poetry add <dependancy>
```

## More Specifically

``` bash
poetry install

#==========[ Terminal 1 ]=============#
poetry run ./first_itteration/watersensor_server.py

#==========[ Terminal 2 ]=============#
poetry run ./first_itteration/manual_plc.py
# OR
poetry run ./first_itteration/auto_plc.py
```

# General Resources and explaination of the files:
Early on, I tried to understand how to use scapy:
- [Documentation Example Lab](https://www.scribd.com/document/419491885/craft-modbus?v=0.184)
    - Primarily impacted first_scapy_experiment.py

Then, I learned of pymodbus:
- [Blog example of a simulated attack](https://mustafaalshawwa.com/posts/modbustcp/)
    - Primarily impacted in try_pymodbus/* (run both in separate terminals)
- [pymodbus On Github](https://github.com/pymodbus-dev/pymodbus/)
- [pymodbus Documentation](https://pymodbus.readthedocs.io/en/latest/source/server.html)

Confident I understood pymodbus, I decided to try to have a second async service on the server (device) also be able to edit the registers in addition to the client. This was a bit unintuitive and required a lot of figuring out what was ment through undocumented code, but eventually I was successful.

- Primarily impacted initial_example/*
    - initial_example/fake_plc.py (for future experimentation more specific applications, but initiall identical to try_pymodbus/modbus_client.py)
    - initial_example/watersensor_server_noupdating.py was my first attempt at this before encountering the example in the pymodbus documentation
    - initial_example/watersensor_server.py used the code for the updating server but I edited it for my use-case after spending a lot of time figuring out what was happening and getting rid of the needless complexity across the many example files it referenced, building off the example code I used in try_pymodbus/*
- I found [this example of an updating server in the pymodbus documentation](https://github.com/pymodbus-dev/pymodbus/blob/dev/examples/server_updating.py#L40) which was hard to interpret, but eventually I figured it out and used it to create watersensor_server.py
- I validated that the server (initial_example/watersensor_server.py) ran properly and showed the contents of the registers being edited.

`first_itteration/*` is the version where both the client and server look like the final simulation we are making and runs properly.

# How to Use First_Itteration Scripts

## Watersensor_server.py 

Run it as:
``` bash
poetry run ./first_itteration/watersensor_server.py
```

To change the parameters of the environment, change this code

``` python
261|    param = SimulationParameters(
262|        initial_level=0,
263|        min_level=0,
264|        max_level=100,
265|        upper_sensor_activation_level=75,
266|        lower_sensor_activation_level=25,
267|        leak_rate_per_sec=5,
268|        pump_rate_per_sec=10
269|    )
```

## manual_plc.py

Run as:
``` bash
poetry run ./first_itteration/manual_plc.py
```

This allows you to manually control the client side code via user input via standard input using the keyboard.

## auto_plc.py

Run as:
``` bash
poetry run ./first_itteration/auto_plc.py
```

Standard outputs:
```
UPDATE: Updated sensor state cache.
SUCCESS: Turned ON pump by LLS
SUCCESS: Turned OFF pump by ULS
SUCCESS: Turned ON pump by LLS
UPDATE: Updated sensor state cache.
SUCCESS: Turned OFF pump by ULS
SUCCESS: Turned ON pump by LLS
SUCCESS: Turned OFF pump by ULS
UPDATE: Updated sensor state cache.
SUCCESS: Turned ON pump by LLS
SUCCESS: Turned OFF pump by ULS
```

`LLS` - Lower Level Sensor

`ULS` - Upper Level Sensor

To change the how frequently UPDATE is run, edit this code:

```python
155|    async def run_client():
156|        DELAY_SEC = 30
157|        DELAY_UNTIL_UPDATE = range(DELAY_SEC*167) #167 was a coefficient experimentally determined to correspont to ~1sec

```

UPDATE validates that the stored parameters are regularly checked to ensure that they adhere to their status on the main server. This is to reduce the quantity of traffic sent to just the upper and lower level sensor in most situations while avoiding system state to separate too much 