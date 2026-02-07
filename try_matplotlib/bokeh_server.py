from bokeh.plotting import figure, curdoc
from bokeh.models import ColumnDataSource, BoxAnnotation, LabelSet, DatetimeTickFormatter, CustomJSTickFormatter
from bokeh.layouts import column
from bokeh.models.widgets import Div
from bokeh.core.enums import MarkerType
import csv
from datetime import datetime
from pathlib import Path
import time

filename = Path('./fake_data.csv')
source1 = ColumnDataSource(data=dict(x=[], y=[], y2=[]))
source2 = ColumnDataSource(data=dict(x=[], y=[], y2=[]))

# Source for labels (separate from data)
label_source = ColumnDataSource(data=dict(
    x=[],
    y=[],
    y2=[],
    text=[]
))

lower_limit = 25
upper_limit = 75
window_max = 100
window_min = 0
below_min = -1000
above_max = 1000


# Create multiple colored bands
zones = [
    #{'bottom': below_min,   'top': window_min,  'color': "#ff0000", 'alpha': 0.2, 'label': 'Outside Simulation Range'},
    {'bottom': window_min,  'top': lower_limit, 'color': "#e26749", 'alpha': 0.8, 'label': 'Beyond Lower Limit'},
    {'bottom': upper_limit, 'top': window_max,  'color': '#e26749', 'alpha': 0.8, 'label': 'Beyond Upper Limit'},
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
    height=600
)

# Format how timestamps appear on axis
# p1.xaxis.formatter = DatetimeTickFormatter(
#     hours="%H:%M:%S",
#     minutes="%H:%M:%S",
#     seconds="%H:%M:%S",
#     minsec="%H:%M:%S",
#     milliseconds="%H:%M:%S.%3N"
# )

# Custom formatter for HH:MM:SS
p1.xaxis.formatter = CustomJSTickFormatter(code="""
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

# Rotate labels if needed
#p1.xaxis.major_label_orientation = 0.785  # 45 degrees in radians

for zone in zones:
    box = BoxAnnotation(
        bottom=zone['bottom'], 
        top=zone['top'], 
        fill_alpha=zone['alpha'], 
        fill_color=zone['color'],
        level = "underlay"
    )
    p1.add_layout(box)

p1.line('x', 'y', source=source1, line_width=2, color='blue') # legend_label="Active Data"
p1.scatter('x', 'y2', source=source1, line_width=2, color='green')

# labels = LabelSet(
#     x='x', y='y', text='text',
#     source=label_source,
#     x_offset=10, y_offset=5,  # Offset from point
#     text_font_size='9pt',
#     text_color="#D2308C",
#     background_fill_color='white',
#     background_fill_alpha=0.7
# )
# p1.add_layout(labels)

# # Configure legend
# p1.legend.location = "top_left"
# p1.legend.click_policy = "hide"  # Click to hide/show
# p1.legend.background_fill_alpha = 0.8
# p1.legend.border_line_color = "#333333"
# p1.legend.border_line_width = 2
# p1.legend.label_text_font_size = "10pt"

# Second plot with linked x-axis
p2 = figure(
    title="Plot 2 - Cumulative Sum", 
    x_axis_label='X', 
    y_axis_label='Cumulative Y',
    tools='',
    sizing_mode='stretch_width',
    height=200,

    x_range=p1.x_range  # Link x-axis to first plot
)
p2.scatter('x', 'y', source=source2, marker="x", size=10, line_width=2, color='red') #legend_label="Cumulative Sum"
p2.line('x', 'y2', source=source2, line_width=2, color='green')

# # Configure legend
# p2.legend.location = "top_left"
# p2.legend.click_policy = "hide"  # Click to hide/show
# p2.legend.background_fill_alpha = 0.8
# p2.legend.border_line_color = "#333333"
# p2.legend.border_line_width = 2
# p2.legend.label_text_font_size = "10pt"

# Bottom labels
bottom_labels = Div(
    text="""
    X  Plot Type 1,  -- this thing
    """,
    #width=600,
    height=50,
    width_policy="max",
    styles={'padding': '5px', 'background': '#e0e0e0', 'text-align': 'center'}
)

status = Div(text="<p>Loading...</p>", sizing_mode='stretch_width', height=30)

def update():
    x_data = []
    y_data = []
    try:
        first_time:datetime|None = None
        with open(filename, 'r') as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                x_time = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S.%f')
                if first_time is None:
                    first_time = x_time
                elapsed_seconds = (x_time-first_time).total_seconds()
                x_data.append(elapsed_seconds)
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

        # right_labels.text = f"""
        #     <div style='font-family: monospace;'>
        #         <p><strong>📊 Statistics</strong></p>
        #         <p>Latest: <b>{latest:.2f}</b></p>
        #         <p>Average: {avg:.2f}</p>
        #         <p>Max: {max_val:.2f}</p>
        #         <p>Min: {min_val:.2f}</p>
        #         <p>Points: {len(y_data)}</p>
        #     </div>
        #     """

        #bottom_labels.text = f"<p style='text-align: center;'>Latest update: {time.strftime('%H:%M:%S')}</p>"
        
        
    except:
        pass

update()

# layout = column(status, p1, p2, bottom_labels, sizing_mode='stretch_both')
layout = column(p1, p2, sizing_mode='stretch_both')


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

"""
poetry run bokeh serve --show bokeh_app.py
"""