# import matplotlib
# matplotlib.use('Agg')  # Use non-interactive backend

from matplotlib import pyplot as plt
import matplotlib.animation as animation
#import pandas as pd
import csv
from pathlib import Path
import signal
import sys
import time

filename = Path('./fake_data.csv')
save_plot = Path('./plots.png')
html_file = Path('./plot.html')

# Create the figure and axis
fig, ax = plt.subplots()


def create_html():
    """Create an HTML file that auto-refreshes the image"""
    # html_content = \
    # """
    # <!DOCTYPE html>
    # <html>
    # <head>
    #     <title>Live Plot</title>
    #     <meta http-equiv="refresh" content="1">
    #     <style>
    #         body { 
    #             margin: 0; 
    #             display: flex; 
    #             justify-content: center; 
    #             align-items: center; 
    #             min-height: 100vh;
    #             background: #f0f0f0;
    #         }
    #         img { 
    #             max-width: 95vw; 
    #             max-height: 95vh;
    #             box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    #         }
    #     </style>
    # </head>
    # <body>
    #     <img src="plot.png?t={}">
    # </body>
    # </html>
    # """.format(int(time.time()))
    
    # with open(html_file, 'w') as f:
    #     f.write(html_content)

def read_csv_data(filename):
    """
    Read CSV file and return x and y data as lists.
    Returns: (x_data, y_data) tuple of lists
    """
    x_data = []
    y_data = []
    
    try:
        with open(filename, 'r') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header row
            
            for row in reader:
                x_data.append(float(row[1]))  # x column (index 1)
                y_data.append(float(row[2]))  # y column (index 2)
    
    except FileNotFoundError:
        pass  # Return empty lists if file doesn't exist yet
    except (ValueError, IndexError):
        pass  # Handle malformed data
    
    return x_data, y_data

frame_count=0

create_html()

def animate(frame):
    global frame_count
    # Read the CSV file each time this function is called
    
    try:
        data = pd.read_csv(filename)
    except:
        x,y = read_csv_data(filename)
        data = {'timestamp':x,'y':y}
    
    # Clear the previous plot
    ax.clear()
    
    # Plot the data (adjust column names to match your CSV)
    ax.plot(data['timestamp'], data['y'])
    
    # Optional: Add labels and title
    ax.set_xlabel('X Label')
    ax.set_ylabel('Y Label')
    ax.set_title('Live Updating Plot')

    # frame_count += 1
    # if frame_count % 10 == 0:
    fig.savefig(save_plot, dpi=300, bbox_inches='tight')
        # print(f"Saved frame {frame_count}")

    create_html()

# Create the animation
# interval is in milliseconds (1000 = update every 1 second)
ani = animation.FuncAnimation(fig, animate, interval=1000, cache_frame_data=False)

# Handle window close
def on_close(event):
    print("Window closed - saving figure...")
    fig.savefig(save_plot, dpi=300, bbox_inches='tight')

fig.canvas.mpl_connect('close_event', on_close)

# Handle Ctrl+C (SIGINT)
# def signal_handler(sig, frame):
#     print("\nCtrl+C detected - saving figure...")
#     fig.savefig(save_plot, dpi=300, bbox_inches='tight')
#     plt.close('all')
#     sys.exit(0)

# signal.signal(signal.SIGINT, signal_handler)

plt.show()
#ani.save(save_plot, writer='pillow', fps=1)

# Keep it running
# import time
# try:
#     while True:
#         plt.pause(1)
# except KeyboardInterrupt:
#     fig.savefig(save_plot, dpi=300, bbox_inches='tight')
#     print("Saved final plot")

