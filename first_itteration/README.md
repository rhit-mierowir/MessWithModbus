# Configuration Information

## Modbus Communication

**PORT:** 5020 <\br>

### Register Assignments
| Signal Name | Data Type | Enable Read/Write | Register Type | Address | Length |
|--|--|--|--|--|--|
| Pump | Bool | Read/Write | Coil | 0 | 1 bit |
| Upper Level Sensor | Bool | Read Only | Discrete Inputs | 0 | 1 bit|
| Lower Level Sensor | Bool | Read Only| Discrete Inputs | 1 | 1 bit | 

## The Environment Configuration
### Visual Depiction
```
|             |
|             | < Upper Level Sensor
|  Container  |
|~~~~~~~~~~~~~|
|             | < Lower Level Sensor
|             <= Pump (If Active)
|             => Leak (Always Active)
\_____________/

```
