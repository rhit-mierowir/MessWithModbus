from bokeh.plotting import figure, output_file, save
from bokeh.models import ColumnDataSource
import csv
from pathlib import Path
import time
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

filename = Path('./fake_data.csv')

def read_csv_data(filename):
    x_data = []
    y_data = []
    try:
        with open(filename, 'r') as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                x_data.append(float(row[1]))
                y_data.append(float(row[2]))
    except:
        pass
    return x_data, y_data




def create_plot():
    x, y = read_csv_data(filename)
    
    if x and y:
        source = ColumnDataSource(data=dict(x=x, y=y))
        
        p = figure(
            title=f"Live Data - {len(x)} points",
            x_axis_label='X',
            y_axis_label='Y',
            width=800,
            height=400
        )
        
        p.line('x', 'y', source=source, line_width=2, color='navy')
        p.circle('x', 'y', source=source, size=4, color='navy')
        
        output_file('plot.html')
        save(p)
        print(f"✓ Updated: {len(x)} points at {time.strftime('%H:%M:%S')}")

create_plot()

class NoCacheHTTPRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()
    def log_message(self, format, *args):
        pass

def start_server():
    server = HTTPServer(('0.0.0.0', 8000), NoCacheHTTPRequestHandler)
    print("🌐 Open: http://localhost:8000/plot.html")
    server.serve_forever()

thread = threading.Thread(target=start_server, daemon=True)
thread.start()

time.sleep(1)

try:
    while True:
        create_plot()
        time.sleep(1)
except KeyboardInterrupt:
    print("\n✅ Done")