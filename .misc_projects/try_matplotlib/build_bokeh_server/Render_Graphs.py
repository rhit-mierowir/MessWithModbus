from pathlib import Path
from dataclasses import dataclass, field
import logging
from datetime import datetime, timedelta
import functools as ft
from collections.abc import Callable
from typing import Any
import pandas as pd

from Save_Results import EnvironmentDirectories, _CtrlFileManager, _HistFileManager, CtrlLogTarget
from File_Management import RemotablePath, RemotablePath, SCPAddress, LocalPath, remotable_open, parse_remotable_path

from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.document import Document
from bokeh.application.handlers.function import FunctionHandler
from bokeh.layouts import column
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, CustomJSTickFormatter, BoxAnnotation, Range1d
from bokeh.models import Div, Label
from bokeh.models import PanTool, WheelZoomTool, BoxZoomTool, ResetTool, SaveTool, CopyTool, HoverTool
from bokeh.models import ColumnDataSource, FixedTicker
import csv
from pathlib import Path

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

@dataclass
class container_plot_parameters:
    max_level:float
    min_level:float
    high_trip_level:float
    low_trip_level:float
    out_of_control_color:str = field(default="#e26749")
    out_of_control_alpha:float = field(default=0.8)
    level_unit:str|None = field(default=None)


@dataclass
class render_graph_parameters:
    update_interval:int
    "Time in milliseconds (1000 = 1 sec) between updates to the bokeh server"
    port_used:int
    "The port the webpage is loaded on"
    history_file:RemotablePath|None
    "The Path To The file with the history of the environment."
    controller_history_file:RemotablePath|None
    "The the file relating to the history of the event"
    container: container_plot_parameters
    "Parameters needed to plot the container"

@dataclass
class parameter_header_values:

    history_file:str|None
    "The Path To The file with the history of the environment. These are always saved on init."
    controller_history_file:str|None
    "The the file relating to the history of the event. These are always saved on init."
    container:container_plot_parameters
    "This is the dataclass containing relevant information for the container being plotted."
    start_of_file_time:datetime|None
    "This is the real-world time that the first test starts. This is initialized to None, and should be filled in while running."

    def __init__(self,graph_parameters:render_graph_parameters):
        self.history_file               = str(graph_parameters.history_file)
        self.controller_history_file    = str(graph_parameters.controller_history_file)
        self.container                  = graph_parameters.container
        self.start_of_file_time         = None

    def _update_parameter_header_text(self,text_display:Div):
        text_list = ["<h1>Environment Graphing Parameters</h1>"]
        text_list.append(f"<p><b>Environment History File:</b> {self.history_file}</p>")
        text_list.append(f"<p><b>Controller History File:</b> {self.controller_history_file}</p>")
        if self.start_of_file_time is not None: text_list.append(f"<p><b>Start of Test:</b> {str(self.start_of_file_time)}</p>")

        text_display.text = "\n".join(text_list)

    



def make_document(doc:Document, parameters:render_graph_parameters):
    """Create the Bokeh document with parameters"""
    
    container = parameters.container

    display_parameters = parameter_header_values(parameters)

    display_parameters_div = Div(
        text=f"""
        This Text Should Be Replaced
        """,
        #width=600,
        #height=50,
        width_policy="max",
        styles={'padding': '5px', 'background': "#d0fdff", 'text-align': 'left'}
    )

    update_display_parameters:Callable[[],None] = lambda: display_parameters._update_parameter_header_text(display_parameters_div)
    "This Function updates the text that displays parameters on the top of the page."
    update_display_parameters()

    envt_source = ColumnDataSource(data=dict(
        time                = [],
        level               = [],
        is_pump_on          = [],
        is_lower_sensor_on  = [],
        is_upper_sensor_on  = [],
        is_overflowing      = [],
        is_empty            = []
    ))
    ctrl_source = ColumnDataSource(data=dict(
        time                = [],
        is_action           = [],
        is_modbus_error     = [],
        is_state_refresh    = [],
        target_pump         = [],
        target_ULS          = [],
        target_LLS          = [],
        message             = []
    ))

    ctrl_categories = ["pump_action", "pump_error", "pump_refresh", "pump_refresh_error", "ULS_refresh", "ULS_refresh_error", "LLS_refresh", "LLS_refresh_error"]
    ctrl_labels     = ["Pump Action", "Pump Error", "Pump Refresh", "Pump Refresh Error", "ULS Refresh", "ULS Refresh Error", "LLS Refresh", "LLS Refresh Error"]
    ctrl_colors     = ["blue"       , "red"       , "blue"        , "red"               , "purple"     , "red"              , "green"      , "red"              ]
    ctrl_markers    = ["diamond"    , "x"         , "circle"      , "x"                 , "circle"     , "x"                , "circle"     , "x"                ]
    ctrl_y_index    = [ 0           , 0           , 1             , 1                   ,  2           , 2                  , 3            , 3                  ]

    ctrl_text_labels   = ["Write Pump"      , "Read Pump"   , "Read ULS", "Read LLS"]
    ctrl_text_labels_y = [0                 , 1             , 2         , 3         ]

    # One ColumnDataSource per category, initialized empty
    ctrl_category_sources = {
        cat: ColumnDataSource(dict(time=[], y=[], message=[]))
        for cat in ctrl_categories
    }

    def get_masks(data):
        """Compute combined boolean masks from raw data columns."""
        return {
            "pump_action":          [(a and p) and not e    for a, e, p  in zip(data['is_action'],   data['is_modbus_error'], data['target_pump'], )],
            "pump_error":           [a and p and e          for a, e, p  in zip(data['is_action'],   data['is_modbus_error'], data['target_pump'], )],
            "pump_refresh":         [r and p and not e      for r, e, p  in zip(data['target_pump'], data['is_modbus_error'], data['is_state_refresh'])],
            "pump_refresh_error":   [r and p and e          for r, e, p  in zip(data['target_pump'], data['is_modbus_error'], data['is_state_refresh'])],
            "ULS_refresh":          [r and u and not e      for r, e, u  in zip(data['target_ULS'],  data['is_modbus_error'], data['is_state_refresh'])],
            "ULS_refresh_error":    [r and u and e          for r, e, u  in zip(data['target_ULS'],  data['is_modbus_error'], data['is_state_refresh'])],
            "LLS_refresh":          [r and l and not e      for r, e, l  in zip(data['target_LLS'],  data['is_modbus_error'], data['is_state_refresh'])],
            "LLS_refresh_error":    [r and l and e          for r, e, l  in zip(data['target_LLS'],  data['is_modbus_error'], data['is_state_refresh'])],
        }

    # Create multiple colored bands
    container_zones = [
        {'bottom': container.min_level,         'top': container.low_trip_level,    'color': container.out_of_control_color, 'alpha': container.out_of_control_alpha, 'label': 'Beyond Lower Limit'},
        {'bottom': container.high_trip_level,   'top': container.max_level,         'color': container.out_of_control_color, 'alpha': container.out_of_control_alpha, 'label': 'Beyond Upper Limit'},
    ]

    timestamp_format = CustomJSTickFormatter(code="""
        // Convert from microseconds to seconds
        var totalSeconds = Math.floor(tick);  // tick is already in seconds
        var hours = Math.floor(totalSeconds / 3600);
        var minutes = Math.floor((totalSeconds % 3600) / 60);
        var seconds = totalSeconds % 60;
        
        if (hours > 0) {
            // Show HH:MM:SS if over an hour
            return String(hours).padStart(2, '0') + ':' + 
                String(minutes).padStart(2, '0') + ':' + 
                String(seconds).padStart(2, '0');
        } else {
            // Show MM:SS if under an hour
            return String(minutes).padStart(2, '0') + ':' + 
                String(seconds).padStart(2, '0');
        }
    """)
    
    level_plot = figure(
        title=f"Container Level of Environment",
        x_axis_label='Time Since Start (HH:MM:SS or MM:SS)',
        y_axis_label='Container Level'+("" if container.level_unit is None else f" ({container.level_unit})"),
        tools=[PanTool(dimensions='width'), 
               WheelZoomTool(dimensions='width'), 
               BoxZoomTool(dimensions='width'), 
               ResetTool(), 
               SaveTool(),
               #CopyTool()
               ],
        sizing_mode='stretch_width',
        height=600,
        y_range=Range1d(start=container.min_level, end=container.max_level,bounds=(container.min_level,container.max_level)) #type: ignore
    )
  
    level_plot.line('time', 'level', source=envt_source, line_width=2, color='blue')
    level_plot.scatter('time', 'level', source=envt_source, line_width=2, marker='square', color='blue')
    level_plot.xaxis.formatter = timestamp_format

    for zone in container_zones:
        box = BoxAnnotation(bottom=zone['bottom'], top=zone['top'], fill_alpha=zone['alpha'], fill_color=zone['color'],level = "underlay")
        level_plot.add_layout(box)

    environment_signals_plot = figure(
        title="Environment Signals",
        x_axis_label='Time Since Start (HH:MM:SS or MM:SS)',
        y_axis_label="",
        tools=[
            #    PanTool(dimensions='width'), 
            #    WheelZoomTool(dimensions='width'), 
            #    BoxZoomTool(dimensions='width'), 
            #    ResetTool(), 
            #    SaveTool(),
            #    CopyTool()
               ],
        sizing_mode='stretch_width',
        height=300,
        y_range=Range1d(start=0, end=5,bounds=(0,5)), #Based on num signals #type:ignore
        x_range=level_plot.x_range
    )
    environment_signals_plot.xaxis.formatter = timestamp_format
    environment_signals_plot.xaxis.visible = False
    environment_signals_plot.yaxis.visible = False

    add_label = lambda label, index:environment_signals_plot.add_layout(Label(x=-1,y=index+0.5,text=label,text_align="right",text_baseline="middle",text_line_height=0.5))
    NUM_ENVIRONMENT_SIGNALS = 5
    environment_signals_plot.line('time','is_pump_on', source=envt_source, line_width=2, color='blue')
    add_label("Pump Active",4)
    environment_signals_plot.line('time','is_lower_sensor_on', source=envt_source, line_width=2, color='black')
    add_label("Lower Sensor",2)
    environment_signals_plot.line('time','is_upper_sensor_on', source=envt_source, line_width=2, color='black')
    add_label("Upper Sensor",3)
    environment_signals_plot.line('time','is_overflowing', source=envt_source, line_width=2, color='red')
    add_label("Overflowing",1)
    environment_signals_plot.line('time','is_empty', source=envt_source, line_width=2, color='red')
    add_label("Empty",0)

    environment_signal_zones = [
        {'bottom':i, 'top':i+1,'color': "#17002F", 'alpha': 0.1 if i % 2 == 1 else 0, 'label': ''}
        for i in range(NUM_ENVIRONMENT_SIGNALS)
    ]
    for e in environment_signal_zones:
        box = BoxAnnotation(bottom=e['bottom'], top=e['top'], fill_alpha=e['alpha'], fill_color=e['color'],level = "underlay")
        environment_signals_plot.add_layout(box)


    controller_message_plot = figure(
        title="Controller Message Log",
        x_axis_label='Time Since Start (HH:MM:SS or MM:SS)',
        y_axis_label="",
        tools=[] if parameters.history_file is not None else [
               PanTool(dimensions='width'), 
               WheelZoomTool(dimensions='width'), 
               BoxZoomTool(dimensions='width'), 
               ResetTool(), 
               SaveTool(),
               #CopyTool()
               ],
        sizing_mode='stretch_width',
        height=200,
        y_range=Range1d(start=min(ctrl_y_index)-0.5, end=max(ctrl_y_index)+0.5,bounds=(min(ctrl_y_index)-0.5,max(ctrl_y_index)+0.5)), #type:ignore
        x_range=level_plot.x_range
    )
    controller_message_plot.xaxis.formatter = timestamp_format
    # Turn on x-axis only if no axis from history file
    controller_message_plot.xaxis.visible = parameters.history_file is None
    controller_message_plot.yaxis.visible = False

    p_ctrl = controller_message_plot

    for i, (cat, label, color, marker) in enumerate(zip(ctrl_categories, ctrl_labels, ctrl_colors, ctrl_markers)):
        p_ctrl.scatter('time', 'y', source=ctrl_category_sources[cat],
                    color=color, legend_label=label, marker=marker, size=8)

    for label, y in zip(ctrl_text_labels,ctrl_text_labels_y):
        p_ctrl.add_layout(Label(x=-3,y=y,text=label,text_align="right",text_baseline="middle",text_line_height=0.5))

    p_ctrl.yaxis.ticker = FixedTicker(ticks=list(range(len(ctrl_labels))))
    p_ctrl.yaxis.formatter = CustomJSTickFormatter(code=f"const labels = {ctrl_labels}; return labels[tick] ?? tick;")
    p_ctrl.add_tools(HoverTool(tooltips=[("Time", "@time"), ("Message", "@message")]))
    p_ctrl.legend.click_policy = "hide"
    p_ctrl.legend.visible = False
    


    def update(print_results=False):

        def align_signal(signal:bool,index:int)->float:
            SCALE_SIGNALS:float = 0.9
            SIGNAL_OFFSET:float = 1.0
            s = int(signal)
            s = SCALE_SIGNALS*s + (1-SCALE_SIGNALS)/2
            return s + SIGNAL_OFFSET*index

        try:
            envt_data:pd.DataFrame|None = _HistFileManager.read_as_dataframe(parameters.history_file) if parameters.history_file is not None else None
            ctrl_data:pd.DataFrame|None = _CtrlFileManager.read_as_dataframe(parameters.controller_history_file) if parameters.controller_history_file is not None else None

            tmp_min = []
            if envt_data is not None: tmp_min.append(envt_data['Time'].min())
            if ctrl_data is not None: tmp_min.append(ctrl_data['Time'].min())
            first_time = min(*tmp_min) if len(tmp_min) > 1 else (tmp_min[0] if len(tmp_min) == 1 else datetime.max) # If no max time, set to datetime.max

            if envt_data is not None: envt_data['rel_time'] = (envt_data['Time'] - first_time).dt.total_seconds()
            if ctrl_data is not None: ctrl_data['rel_time'] = (ctrl_data['Time'] - first_time).dt.total_seconds()

            if display_parameters.start_of_file_time is None and first_time < datetime.max: # Update display parameters first time start_of_file_time is calculated
                display_parameters.start_of_file_time = first_time
                update_display_parameters()

            if print_results: print(envt_data)
            if print_results: print(ctrl_data)

            if envt_data is not None:
                envt_source.data = dict(
                    time                = envt_data['rel_time'],
                    level               = envt_data['level'],
                    is_pump_on          = [align_signal(b,index=4) for b in envt_data['is_pump_on']],
                    is_upper_sensor_on  = [align_signal(b,index=3) for b in envt_data['is_upper_sensor_active']],
                    is_lower_sensor_on  = [align_signal(b,index=2) for b in envt_data['is_lower_sensor_active']],
                    is_overflowing      = [align_signal(b,index=1) for b in envt_data['is_overflowing']],
                    is_empty            = [align_signal(b,index=0) for b in envt_data['is_empty']]
                )
            if ctrl_data is not None:
                ctrl_source.data = dict(
                    time                = ctrl_data['rel_time'],
                    is_action           = ctrl_data['is_action'],
                    is_modbus_error     = ctrl_data['is_modbus_error'],
                    is_state_refresh    = ctrl_data['is_state_refresh'],
                    target_pump         = [CtrlLogTarget.pump in x for x in ctrl_data['targets']],
                    target_ULS          = [CtrlLogTarget.ULS in x for x in ctrl_data['targets']],
                    target_LLS          = [CtrlLogTarget.LLS in x for x in ctrl_data['targets']],
                    message             = ctrl_data['message']
                )

            masks = get_masks(ctrl_source.data)
            for i, cat in enumerate(ctrl_categories):
                mask = masks[cat]
                ctrl_category_sources[cat].data = dict(
                    time    = [t for t, b in zip(ctrl_source.data['time'],    mask) if b],
                    y       = [ctrl_y_index[i]] * sum(mask),
                    message = [m for m, b in zip(ctrl_source.data['message'], mask) if b]
                )

        except Exception as e:
            log.exception(f"Error: {e}")
        
        if print_results:
            print("-"*50)
            print(envt_source.data)
            print("="*50)
            print(ctrl_source.data)
    
    update(print_results=False)

    layout_column = []
    layout_column.append(display_parameters_div)
    if parameters.history_file is not None:
        layout_column.append(level_plot)
    if parameters.history_file is not None:
        layout_column.append(environment_signals_plot)
    if parameters.controller_history_file is not None:
        layout_column.append(controller_message_plot)

    layout = column(*layout_column, sizing_mode='stretch_both')
    
    doc.add_root(layout)
    periodic_update:Callable[[],None] = ft.partial(update,print_results=False)
    doc.add_periodic_callback(periodic_update, parameters.update_interval)

def _run_bokeh_server(parameters:render_graph_parameters)->None:
    
    # Create application with parameters passed to make_document
    apps = {
        '/': Application(
            FunctionHandler(
                lambda doc: make_document(doc, parameters=parameters)
            )
        )
    }
    
    # Start server
    server = Server(apps, port=parameters.port_used)
    server.start()
    
    log.info(f"Opening Bokeh application on http://localhost:{parameters.port_used}/")
    
    server.io_loop.add_callback(server.show, "/")
    server.io_loop.start()

def render_graphs(parameters:render_graph_parameters, directories:EnvironmentDirectories):
    _run_bokeh_server(parameters)

# Main execution
if __name__ == '__main__':
    
    HIST_FILE: RemotablePath | None = None
    CTRL_FILE: RemotablePath | None = None
    # Comment the following lines out to act like they weren't provided.
    HIST_FILE = parse_remotable_path(str(Path(Path(__file__).parent, "EnvironmentHistory.csv")))
    CTRL_FILE = parse_remotable_path(str(Path(Path(__file__).parent, "ControllerHistory.csv")))
    


    _run_bokeh_server(render_graph_parameters(
        update_interval=1,
        port_used=8000,
        history_file=HIST_FILE,
        controller_history_file=CTRL_FILE,
        container=container_plot_parameters(
            max_level=100,
            min_level=0,
            high_trip_level=75,
            low_trip_level=25,
            level_unit="L"
        )
    ))