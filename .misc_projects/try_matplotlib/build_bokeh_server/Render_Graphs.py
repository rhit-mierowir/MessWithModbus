from pathlib import Path
from dataclasses import dataclass, field
import logging
from datetime import datetime

from Save_Results import EnvironmentDirectories
from File_Management import RemotablePath, RemotablePath, SCPAddress, LocalPath, remotable_open, parse_remotable_path

from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.document import Document
from bokeh.application.handlers.function import FunctionHandler
from bokeh.layouts import column
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, CustomJSTickFormatter, BoxAnnotation
from bokeh.models import Div
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


@dataclass
class render_graph_parameters:
    update_interval:int
    "Time in milliseconds (1000 = 1 sec) between updates to the bokeh server"
    port_used:int
    "The port the webpage is loaded on"
    history_file:RemotablePath
    "The Path To The file with the history of the environment."
    controller_history_file:RemotablePath|None
    "The the file relating to the history of the event"
    container: container_plot_parameters
    "Parameters needed to plot the container"
    



def make_document(doc:Document, parameters:render_graph_parameters):
    """Create the Bokeh document with parameters"""
    
    container = parameters.container

    display_parameters = Div(
        text=f"""
        <h1>Environment Graphing Parameters</h1>
        <p><b>Environment History File:</b> {parameters.history_file}</p>
        <p><b>Controller History File:</b> {parameters.controller_history_file}</p>
        """,
        #width=600,
        #height=50,
        width_policy="max",
        styles={'padding': '5px', 'background': "#d0fdff", 'text-align': 'left'}
    )

    envt_source = ColumnDataSource(data=dict(x=[], y=[]))
    ctrl_source = ColumnDataSource(data=dict(x=[], y=[]))

    files_included = []
    if parameters.history_file is not None: files_included.append("Environment")
    if parameters.controller_history_file is not None: files_included.append("Controller")
    files_included = " & ".join(files_included)
    # Create multiple colored bands
    container_zones = [
        {'bottom': container.min_level,         'top': container.low_trip_level,    'color': container.out_of_control_color, 'alpha': container.out_of_control_alpha, 'label': 'Beyond Lower Limit'},
        {'bottom': container.high_trip_level,   'top': container.max_level,         'color': container.out_of_control_color, 'alpha': container.out_of_control_alpha, 'label': 'Beyond Upper Limit'},
    ]
    
    level_plot = figure(
        title=f"Data from {files_included}",
        x_axis_label='Time',
        y_axis_label='level',
        tools='pan,wheel_zoom,box_zoom,reset,save',
        sizing_mode='stretch_width',
        height=600,
        y_range=(container.min_level,container.max_level)
    )
    
    level_plot.line('x', 'y', source=envt_source, line_width=2, color='blue')
    level_plot.scatter('x', 'y', source=envt_source, line_width=2, marker='square', color='blue')

    timestamp_format = CustomJSTickFormatter(code="""
        var totalSeconds = Math.floor(tick);
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
    level_plot.xaxis.formatter = timestamp_format

    for zone in container_zones:
        box = BoxAnnotation(
            bottom=zone['bottom'], 
            top=zone['top'], 
            fill_alpha=zone['alpha'], 
            fill_color=zone['color'],
            level = "underlay"
        )
        level_plot.add_layout(box)


    
    
    def update():
        x_data = []
        y_data = []
        try:
            first_time:datetime|None = None
            with remotable_open(parameters.history_file, 'r') as file:
                reader = csv.reader(file)
                next(reader)
                for row in reader:
                    x_time = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S.%f')
                    if first_time is None:
                        first_time = x_time
                    elapsed_seconds = (x_time-first_time).total_seconds()
                    x_data.append(elapsed_seconds)
                    y_data.append(float(row[1]))
            
            envt_source.data = dict(x=x_data, y=y_data)
        except Exception as e:
            print(f"Error: {e}")
    
    update()

    layout = column(display_parameters, level_plot, sizing_mode='stretch_both')
    
    doc.add_root(layout)
    doc.add_periodic_callback(update, parameters.update_interval)

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
    #raise NotImplementedError("Configure this manually before using this script independantly.")
    _run_bokeh_server(render_graph_parameters(
        update_interval=1,
        port_used=8000,
        history_file=parse_remotable_path(str(Path(Path(__file__).parent, "EnvironmentHistory.csv"))),
        controller_history_file=parse_remotable_path(str(Path(Path(__file__).parent, "ControllerHistory.csv"))),
        container=container_plot_parameters(
            max_level=100,
            min_level=0,
            high_trip_level=75,
            low_trip_level=25
        )
    ))