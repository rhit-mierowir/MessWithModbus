import matplotlib
matplotlib.use('Agg')

from matplotlib import pyplot as plt
from pathlib import Path
import csv
import time
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

filename = Path('./fake_data.csv')
save_plot = Path('./plot.png')

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

def create_webpage():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Live Plot</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }
            h1 { color: #333; }
            .timestamp { color: #666; font-size: 14px; }
            img {
                width: 100%;
                max-width: 800px;
                border: 2px solid #ddd;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
        </style>
        <script>
            setInterval(function() {
                document.getElementById('plot').src = 'plot.png?' + new Date().getTime();
                document.getElementById('time').textContent = new Date().toLocaleTimeString();
            }, 1000);
        </script>
    </head>
    <body>
        <h1>Live Data Visualization</h1>
        <p class="timestamp">Last updated: <span id="time"></span></p>
        <img id="plot" src="plot.png" alt="Live Plot">
    </body>
    </html>
    """
    with open('index.html', 'w') as f:
        f.write(html)

create_webpage()

class NoCacheHTTPRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

def start_server():
    server = HTTPServer(('0.0.0.0', 8000), NoCacheHTTPRequestHandler)
    print("🌐 Open: http://localhost:8000")
    server.serve_forever()

server_thread = threading.Thread(target=start_server, daemon=True)
server_thread.start()

time.sleep(0.5)

# Manual update loop
fig, ax = plt.subplots(figsize=(10, 6))

print("Starting update loop...")
try:
    while True:
        x, y = read_csv_data(filename)
        
        if x and y:
            ax.clear()
            ax.plot(x, y, linewidth=2)
            ax.set_xlabel('X Label')
            ax.set_ylabel('Y Label')
            ax.set_title(f'Live Plot - {len(x)} points')
            ax.grid(True, alpha=0.3)
            fig.savefig(save_plot, dpi=150, bbox_inches='tight')
            print(f"✓ Updated: {len(x)} points at {time.strftime('%H:%M:%S')}")
        
        time.sleep(1)  # Update every second
        
except KeyboardInterrupt:
    print("\n💾 Saving final plot...")
    fig.savefig(save_plot, dpi=300, bbox_inches='tight')
    print("✅ Done!")