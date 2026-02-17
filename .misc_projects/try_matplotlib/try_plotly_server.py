import plotly.graph_objects as go
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
    except Exception as e:
        print(f"Error reading CSV: {e}")
    return x_data, y_data

def create_plot():
    x, y = read_csv_data(filename)
    
    if not x or not y:
        print("No data available yet...")
        # Create empty plot with message
        fig = go.Figure()
        fig.add_annotation(
            text="Waiting for data...",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20)
        )
    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x, 
            y=y, 
            mode='lines+markers',
            name='Data',
            line=dict(width=2),
            marker=dict(size=4)
        ))
        
        fig.update_layout(
            title=f'Live Data Visualization - {len(x)} points',
            xaxis_title='X Label',
            yaxis_title='Y Label',
            template='plotly_white',
            hovermode='x unified'
        )
    
    # Save as interactive HTML with CDN (no local dependencies)
    fig.write_html(
        'plot.html', 
        auto_open=False,
        include_plotlyjs='cdn'  # Use CDN instead of embedded
    )
    print(f"✓ Updated plot: {len(x)} points at {time.strftime('%H:%M:%S')}")

# Create initial plot
create_plot()

class NoCacheHTTPRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Expires', '0')
        super().end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress HTTP logs for cleaner output

def start_server():
    server = HTTPServer(('0.0.0.0', 8000), NoCacheHTTPRequestHandler)
    print("=" * 50)
    print("📊 Plotly Server running!")
    print("🌐 Open: http://localhost:8000/plot.html")
    print("=" * 50)
    server.serve_forever()

thread = threading.Thread(target=start_server, daemon=True)
thread.start()

time.sleep(1)

print("Starting update loop... (Press Ctrl+C to stop)")
try:
    while True:
        create_plot()
        time.sleep(1)
except KeyboardInterrupt:
    print("\n✅ Stopped")

