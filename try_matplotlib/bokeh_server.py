from bokeh.plotting import figure, curdoc
from bokeh.models import ColumnDataSource,BoxAnnotation
from bokeh.layouts import column
from bokeh.models.widgets import Div
from bokeh.core.enums import MarkerType
import csv
from pathlib import Path

filename = Path('./fake_data.csv')
source1 = ColumnDataSource(data=dict(x=[], y=[], y2=[]))
source2 = ColumnDataSource(data=dict(x=[], y=[], y2=[]))

lower_limit = 25
upper_limit = 75
window_max = 100
window_min = 0
below_min = -1000
above_max = 1000


# Create multiple colored bands
zones = [
    #{'bottom': below_min,   'top': window_min,  'color': "#ff0000", 'alpha': 0.2, 'label': 'Outside Simulation Range'},
    {'bottom': window_min,  'top': lower_limit, 'color': "#e26749", 'alpha': 0.2, 'label': 'Beyond Lower Limit'},
    {'bottom': upper_limit, 'top': window_max,  'color': '#e26749', 'alpha': 0.2, 'label': 'Beyond Upper Limit'},
    #{'bottom': window_max,  'top': above_max,   'color': '#ff0000', 'alpha': 0.2, 'label': 'Outside Simulation Range'}
]

# First plot
p1 = figure(
    title="Plot 1 - Y vs X", 
    x_axis_label='X', 
    y_axis_label='Y',
    y_range= (0,100),
    tools='pan,wheel_zoom,box_zoom,reset,save',
    sizing_mode='stretch_width',
    height=400
)

for zone in zones:
    box = BoxAnnotation(
        bottom=zone['bottom'], 
        top=zone['top'], 
        fill_alpha=zone['alpha'], 
        fill_color=zone['color']
    )
    p1.add_layout(box)

p1.line('x', 'y', source=source1, line_width=2, color='blue')
p1.scatter('x', 'y2', source=source1, line_width=2, color='green')

# Second plot with linked x-axis
p2 = figure(
    title="Plot 2 - Cumulative Sum", 
    x_axis_label='X', 
    y_axis_label='Cumulative Y',
    tools='pan,wheel_zoom,box_zoom,reset,save',
    sizing_mode='stretch_width',
    height=400,
    x_range=p1.x_range  # Link x-axis to first plot
)
p2.scatter('x', 'y', source=source2, marker="x", size=10, line_width=2, color='red')
p2.line('x', 'y2', source=source2, line_width=2, color='green')

status = Div(text="<p>Loading...</p>", sizing_mode='stretch_width', height=30)

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
                
        
        # First plot: original data
        source1.data = dict(x=x_data, y=y_data, y2=[y+5 for y in y_data])
        
        # Second plot: cumulative sum
        cumsum = []
        running_sum = 0
        for y in y_data:
            running_sum += y
            cumsum.append(running_sum)
        source2.data = dict(x=x_data, y=cumsum, y2=[y%1000 for y in cumsum])
        
        status.text = f"<p>Points: {len(x_data)}</p>"
        
    except:
        pass

update()

layout = column(status, p1, p2, sizing_mode='stretch_both')

curdoc().add_root(layout)
curdoc().add_periodic_callback(update, 1000)
curdoc().title = "Linked Plots"

"""
'stretch_both' - Fills available width AND height (best for fullscreen)
'stretch_width' - Fills available width only
'stretch_height' - Fills available height only
'scale_width' - Scales proportionally to width
'scale_height' - Scales proportionally to height
'scale_both' - Scales proportionally to both
"""