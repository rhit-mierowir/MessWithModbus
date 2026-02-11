import csv
import time
import random
from datetime import datetime
from pathlib import Path

# Create the CSV file with headers
filename = Path('./fake_data.csv')

with open(filename, 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['timestamp', 'x', 'y'])  # Headers

print(f"Started writing data to {filename}")
print("Press Ctrl+C to stop")

try:
    x = 0
    while True:
        # Generate some sample data
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        y = random.uniform(0, 100)  # Random value between 0 and 100
        
        # Append to CSV
        with open(filename, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, x, y])
        
        #print(f"Written: {timestamp}, {x}, {y}")
        
        x += 1
        time.sleep(1)  # Wait 0.25 seconds (quarter second)
        
except KeyboardInterrupt:
    print("\nStopped writing data")