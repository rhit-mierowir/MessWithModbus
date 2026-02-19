# This file contains all Classes and objects used to save simulation results to a file.

from dataclasses import dataclass, field, is_dataclass, asdict
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager
import pandas as pd
import csv
import json
import os
import logging
from enum import Enum

from File_Management import RemotablePath, remotable_as_local_file

from collections.abc import Iterable, Generator, Iterator
from typing import Any, Optional, TypeVar

try:
    from _csv import _writer as CSV_Writer
    from _csv import _reader as CSV_Reader
except ImportError as e:
    # raise e  # Un-Comment line for syntax highlighting, Re-comment before run in docker
    CSV_Writer = TypeVar('CSV_Writer')
    CSV_Reader = TypeVar('CSV_Reader')

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.WARNING)

########################################################[ Environment Directories ]########################################################
# This class manages the directories and files we create to save results.
# It does all of the checks for files and directories, creating directories as needed.
# It also decides where each file is placed in the results folder. 


@dataclass(frozen=True)
class EnvironmentDirectories:
    out_dir:Path|str
    "The output path of the overall directories, the base of all others `out_dir/...`. Automatically converts to a path with Path()."
    environment_subdirectory_name:str|None  = field(default_factory=lambda:"Environment")
    "The name of the subdirectory for all data about the environment, if None, we just put everything in the out_dir. `out_dir/subdirectory/...` or `outdir/...`"
    history_file_name:str                   = field(default_factory=lambda:"EnvironmentHistory.csv")
    "The name of the file archiving the system's state changes. Results in a path like `out_dir/subdirectory/history_file_name`"
    context_file_name:str                   = field(default_factory=lambda:"EnvironmentContext.json")
    "The name of the file describing the structure of the system. Results in a path like `out_dir/subdirectory/context_file_name`"
    controller_history_file_name:str        = field(default_factory=lambda:"ControllerHistory.csv")
    "The name of the file describing actions and events from the controller."


    def __post_init__(self):
        if isinstance(self.out_dir, str):
            object.__setattr__(self, 'out_dir', Path(self.out_dir))
        
        if not os.path.exists(self.base_directory): # Make the directories if they don't exist.
            os.makedirs(self.base_directory)
    
    @property
    def base_directory(self)->Path:
        "The directory where all files are stored."
        if self.environment_subdirectory_name is not None:
            return self.out_dir / self.environment_subdirectory_name #type: ignore
        return self.out_dir #type:ignore

    @property
    def history_file_path(self)->Path:
        "The full path of the history_file."
        return self.base_directory / self.history_file_name

    @property
    def context_file_path(self)->Path:
        "The full path of the context_file."
        return self.base_directory / self.context_file_name
    
    @property
    def controller_history_file_path(self)->Path:
        "The full path of the controller_history_file."
        return self.base_directory / self.controller_history_file_name

########################################################[ Environment History File ]########################################################
# These functions and objects managing writing to the Environment History File which is done while the simulation is running.

@dataclass(frozen=True)
class EnvironmentLogData:
    "All the information for the history file recording the system state."
    water_level             :float
    overflowing             :bool       = field(default=False)
    empty                   :bool       = field(default=False)
    pump_active             :bool       = field(default=False)
    upper_sensor_active     :bool       = field(default=False)
    lower_sensor_active     :bool       = field(default=False)
    timestamp               :datetime   = field(default_factory=datetime.now)

class _HistFileManager:
    "A collection of functions to help manage writing the Environment History CSV file."

    @staticmethod
    def write_headers(writer:CSV_Writer): #type:ignore
        "Fill out the headers for"
        writer.writerow(['Time', 'level','is_pump_on','is_upper_sensor_active', 'is_lower_sensor_active', 'is_overflowing','is_empty'])

    @staticmethod
    def _write_data(writer:CSV_Writer,rows:Iterable[Iterable[Any]]): #type:ignore
        writer.writerows(rows)

    @staticmethod
    def _data_to_rows(data:EnvironmentLogData)->Iterable[Any]:
        row = []
        # row.append(data.timestamp.isoformat())                        # Universally recognized
        row.append(data.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f'))     # Excel Friendly & more readable
        row.append(data.water_level)
        row.append(data.pump_active)
        row.append(data.upper_sensor_active)
        row.append(data.lower_sensor_active)
        row.append(data.overflowing)
        row.append(data.empty)
        return row
    
    @staticmethod
    def write_data(writer:CSV_Writer,data:EnvironmentLogData): #type:ignore
        _HistFileManager._write_data(writer,[_HistFileManager._data_to_rows(data)])
    
    @staticmethod
    def write_datas(writer:CSV_Writer,datas:Iterable[EnvironmentLogData]): #type:ignore
        _HistFileManager._write_data(writer,rows=[_HistFileManager._data_to_rows(d) for d in datas])

    @staticmethod
    def read_all_data(history_file:Path)-> Generator[EnvironmentLogData,None,None]:
        "Reads from the start of the file to the end"
        with open(file=history_file, mode='r') as file:
            reader = csv.reader(file)
            next(reader) #Ignore headers
            for row in reader:
                yield EnvironmentLogData(
                    timestamp           = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S.%f'),
                    water_level         = float(row[1]),
                    pump_active         = bool(row[2]),
                    upper_sensor_active = bool(row[3]),
                    lower_sensor_active = bool(row[4]),
                    overflowing         = bool(row[5]),
                    empty               = bool(row[6])
                )
    
    @staticmethod
    def read_as_dataframe(history_file:RemotablePath)->pd.DataFrame:
        "Reads as dataframe with appropriate converters."
        def to_bool(x): return x.lower() in ('true', '1', 'yes')
        converters = {
            'Time': lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S.%f'),
            'level': float,
            'is_pump_on': to_bool,
            'is_upper_sensor_active': to_bool,
            'is_lower_sensor_active':to_bool,
            'is_overflowing':to_bool,
            'is_empty':to_bool
        }
        with remotable_as_local_file(history_file) as local_history_file:
            return pd.read_csv(local_history_file, converters=converters)

class _EnvironmentStateHistoryLogger:
    "This is the object held by the program provided by a context manager [update_state_history_file()]. This edits the file line by line so it can be viewed live."
    def __init__(self,history_file:Path):
        self.file = history_file
        with open(file=self.file,mode='w') as f:
            writer = csv.writer(f)
            _HistFileManager.write_headers(writer)

    def save(self,data:EnvironmentLogData):
        with open(file=self.file, mode='a') as f:
            writer = csv.writer(f)
            _HistFileManager.write_data(writer,data)

@asynccontextmanager
async def update_state_history_file(history_file:Path):
    "use a with statement `with update_state_history_file(...) as writer` to use this."
    try:
        state_log = _EnvironmentStateHistoryLogger(history_file)
        
        try:
            yield state_log
        except Exception as e:
                raise e #Don't actually catch errors
    except Exception as e:
        log.exception(f"Exception Occoured in Save_Results.")
        # Normally swallows exceptions, so at least we can see it now.

def read_state_history_file(history_file:Path)->Iterable[EnvironmentLogData]:
    "This returns an iterator from the contents of the environment log data, which can be itterated over in a for loop, reading the data as it is accessed from the iterator"
    return _HistFileManager.read_all_data(history_file)

########################################################[ Environment Context File ]########################################################
# These functions and objects managing writing to the Environment Context File which is done before the simulation.
# This file explains the conditions that were set for this run, primarily involving the simulation settings.

def save_to_context_file(file:Path,context:dict)->None:
    "Saves the dictionary provided to the Environment Context File to establish to the viewer how the Environment was setup prior to run."

    def context_serializer(obj:Any)->str|dict:
        if is_dataclass(obj):
            return asdict(obj) #type:ignore

        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON Serializable so can't be written the Context File. Add to context_serializer if needed.")

    try:
        with open(file=file,mode="w") as f:
            json.dump(context,f,default=context_serializer, indent=4)
    except Exception as e:
        log.exception(f"Error building Context File in Save_Results.")

########################################################[ Controller History File ]########################################################
# These functions and objects managing writing to the Controller History File. 
# This done if the Automatic_Controller is running and performs some signifigant action.

class CtrlLogTarget(Enum):
    "The things a controller can act towards."
    lower_level_sensor = "LLS"
    LLS = lower_level_sensor
    upper_level_sensor = "ULS"
    ULS = upper_level_sensor
    pump = "pump"

    @staticmethod
    def all()->set['CtrlLogTarget']:
        return {CtrlLogTarget.LLS,CtrlLogTarget.ULS,CtrlLogTarget.pump}

    @staticmethod
    def set_to_string(targets:set['CtrlLogTarget'])->str:
        return "-".join(t.value for t in targets)
    
    @staticmethod
    def string_to_set(target_string:str)->set['CtrlLogTarget']:
        out=set()
        strs = [s.strip() for s in target_string.split('-')]
        strs = [s for s in strs if not s==""]
        for s in strs:
            try:
                out.add(CtrlLogTarget(s))
            except ValueError:
                pass
        return out


@dataclass(frozen=True)
class ControllerLogData:
    "All the information for the controller history file recording the system state."
    is_action           :bool               = field(default=False)
    is_modbus_error     :bool               = field(default=False)
    is_state_refresh    :bool               = field(default=False)
    targets             :set[CtrlLogTarget] = field(default_factory=set)
    message             :str                = field(default="")
    timestamp           :datetime           = field(default_factory=datetime.now)

    @staticmethod
    def _parse_targets(target:set[CtrlLogTarget]|CtrlLogTarget|None)->set[CtrlLogTarget]:
        if target is None: return set()
        elif isinstance(target,CtrlLogTarget): return {target}
        else: return target

    @staticmethod
    def log_action(targets:set[CtrlLogTarget]|CtrlLogTarget|None=None,message:str="")->'ControllerLogData':
        return ControllerLogData(is_action=True,is_modbus_error=False,is_state_refresh=False,message=message,
                                 targets=ControllerLogData._parse_targets(targets))
    @staticmethod
    def log_modbus_error(targets:set[CtrlLogTarget]|CtrlLogTarget|None=None,message:str="")->'ControllerLogData':
        return ControllerLogData(is_action=False,is_modbus_error=True,is_state_refresh=False,message=message,
                                 targets=ControllerLogData._parse_targets(targets))
    @staticmethod
    def log_state_refresh(targets:set[CtrlLogTarget]|CtrlLogTarget|None=None,message:str="")->'ControllerLogData':
        return ControllerLogData(is_action=False,is_modbus_error=False,is_state_refresh=True,message="",
                                 targets=ControllerLogData._parse_targets(targets))
    


class _CtrlFileManager:
    "A collection of functions to help manage writing the Environment History CSV file."
    @staticmethod
    def write_headers(writer:CSV_Writer): #type:ignore
        "Fill out the headers for"
        writer.writerow(['Time', 'is_action','is_modbus_error', 'is_state_refresh','targets','message'])

    @staticmethod
    def _write_data(writer:CSV_Writer,rows:Iterable[Iterable[Any]]): #type:ignore
        writer.writerows(rows)

    @staticmethod
    def _data_to_rows(data:ControllerLogData)->Iterable[Any]:
        row = []
        # row.append(data.timestamp.isoformat())                        # Universally recognized
        row.append(data.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f'))     # Excel Friendly & more readable
        row.append(data.is_action)
        row.append(data.is_modbus_error)
        row.append(data.is_state_refresh)
        row.append(CtrlLogTarget.set_to_string(data.targets))
        row.append(data.message)
        return row
    
    @staticmethod
    def write_data(writer:CSV_Writer,data:ControllerLogData): #type:ignore
        _CtrlFileManager._write_data(writer,[_CtrlFileManager._data_to_rows(data)])
    
    @staticmethod
    def write_datas(writer:CSV_Writer,datas:Iterable[ControllerLogData]): #type:ignore
        _CtrlFileManager._write_data(writer,rows=[_CtrlFileManager._data_to_rows(d) for d in datas])
    
    @staticmethod
    def read_all_data(history_file:Path)-> Generator[ControllerLogData,None,None]:
        "Reads from the start of the file to the end"
        with open(file=history_file, mode='r') as file:
            reader = csv.reader(file)
            next(reader) #Ignore headers
            for row in reader:
                yield ControllerLogData(
                    timestamp           = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S.%f'),
                    is_action           = bool(row[1]),
                    is_modbus_error     = bool(row[2]),
                    is_state_refresh    = bool(row[3]),
                    targets             = CtrlLogTarget.string_to_set(row[4]),
                    message             = str(row[5])
                )
    
    @staticmethod
    def read_as_dataframe(history_file:RemotablePath)->pd.DataFrame:
        "Reads as dataframe with appropriate converters."
        
        def to_bool(x): return x.lower() in ('true', '1', 'yes')
        converters = {
            'Time': lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S.%f'),
            'is_action': to_bool,
            'is_modbus_error': to_bool,
            'is_state_refresh': to_bool,
            'targets': CtrlLogTarget.string_to_set,
            'message': str
        }
        with remotable_as_local_file(history_file) as local_history_file:
            return pd.read_csv(local_history_file, converters=converters)

class _ControllerHistoryLogger:
    "This is the object held by the program provided by a context manager [update_control_history_file()]. This edits the file line by line so it can be viewed live."
    def __init__(self,history_file:Path):
        self.file = history_file
        with open(file=self.file,mode='w') as f:
            writer = csv.writer(f)
            _CtrlFileManager.write_headers(writer)

    def save(self,data:ControllerLogData):
        with open(file=self.file, mode='a') as f:
            writer = csv.writer(f)
            _CtrlFileManager.write_data(writer,data)

@asynccontextmanager
async def update_control_history_file(history_file:Path):
    try:
        ctrl_log = _ControllerHistoryLogger(history_file)
        
        try:
            yield ctrl_log
        except Exception as e:
                raise e #Don't actually catch errors
    except Exception as e:
        log.exception(f"Exception Occoured in Save_Results.")
        # Normally swallows exceptions, so at least we can see it now.

def read_control_history_file(history_file:Path)->Iterable[ControllerLogData]:
    "This returns an iterator from the contents of the controller log data, which can be itterated over in a for loop, reading the data as it is accessed from the iterator"
    return _CtrlFileManager.read_all_data(history_file)