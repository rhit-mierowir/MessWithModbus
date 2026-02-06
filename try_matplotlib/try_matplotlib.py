
from matplotlib import pyplot as plt
import matplotlib.animation as animation
import pandas as pd
from pathlib import Path
import signal
import sys

filename = Path('./fake_data.csv')
save_plot = Path('./plots.png')

# Create the figure and axis
fig, ax = plt.subplots()

def animate(frame):
    # Read the CSV file each time this function is called
    data = pd.read_csv(filename)
    
    # Clear the previous plot
    ax.clear()
    
    # Plot the data (adjust column names to match your CSV)
    ax.plot(data['timestamp'], data['y'])
    
    # Optional: Add labels and title
    ax.set_xlabel('X Label')
    ax.set_ylabel('Y Label')
    ax.set_title('Live Updating Plot')

# Create the animation
# interval is in milliseconds (1000 = update every 1 second)
ani = animation.FuncAnimation(fig, animate, interval=1000)

# Handle window close
def on_close(event):
    print("Window closed - saving figure...")
    fig.savefig(save_plot, dpi=300, bbox_inches='tight')

fig.canvas.mpl_connect('close_event', on_close)

# Handle Ctrl+C (SIGINT)
def signal_handler(sig, frame):
    print("\nCtrl+C detected - saving figure...")
    fig.savefig(save_plot, dpi=300, bbox_inches='tight')
    plt.close('all')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

plt.show()

