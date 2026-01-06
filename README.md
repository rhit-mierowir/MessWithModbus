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
poetry run ./first_itteration/fake_plc.py
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