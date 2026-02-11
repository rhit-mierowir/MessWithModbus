from pathlib import Path
from dataclasses import dataclass
import logging

from .Save_Results import EnvironmentDirectories
from .File_Management import RemotablePath, RemotablePath, SCPAddress, LocalPath, remotable_open, parse_remotable_path

from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

@dataclass
class render_graph_parameters:
    update_interval:int
    "Time between updates to the bokeh server"
    port_used:int
    "The port the webpage is loaded on"
    history_file:RemotablePath
    "The Path To The file with the history of the environment."
    controller_history_file:RemotablePath|None
    "The the file relating to the history of the event"



def make_document(doc, data_file='./fake_data.csv', update_interval=1000):
    """Create the Bokeh document with parameters"""
    from bokeh.plotting import figure
    from bokeh.models import ColumnDataSource
    import csv
    from pathlib import Path
    
    filename = Path(data_file)
    source = ColumnDataSource(data=dict(x=[], y=[]))
    
    p = figure(
        title=f"Data from {filename.name}",
        x_axis_label='X',
        y_axis_label='Y',
        tools='pan,wheel_zoom,box_zoom,reset,save',
        sizing_mode='stretch_width',
        height=400
    )
    
    p.line('x', 'y', source=source, line_width=2, color='blue')
    
    def update():
        x_data = []
        y_data = []
        try:
            with open(filename, 'r') as file:
                reader = csv.reader(file)
                next(reader)
                for row in reader:
                    x_data.append(float(row[1]))
                    y_data.append(float(row[2]))
            
            source.data = dict(x=x_data, y=y_data)
        except Exception as e:
            print(f"Error: {e}")
    
    update()
    
    doc.add_root(p)
    doc.add_periodic_callback(update, update_interval)

def _run_bokeh_server(parameters:render_graph_parameters)->None:
    # Your runtime parameters
    data_file = './my_data.csv'
    update_interval = 1000
    port = 8080
    
    # Create application with parameters passed to make_document
    apps = {
        '/': Application(
            FunctionHandler(
                lambda doc: make_document(doc, data_file, update_interval)
            )
        )
    }
    
    # Start server
    server = Server(apps, port=port)
    server.start()
    
    log.info(f"Opening Bokeh application on http://localhost:{port}/")
    
    server.io_loop.add_callback(server.show, "/")
    server.io_loop.start()

def render_graphs(parameters:render_graph_parameters, directories:EnvironmentDirectories):
    _run_bokeh_server(parameters)

# Main execution
if __name__ == '__main__':
    raise NotImplementedError("Configure this manually before using this script independantly.")
    _run_bokeh_server()