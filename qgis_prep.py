import csv
import numpy as np
import rasterio # Raster data library
import os

# Input and output folder paths
input_folder = "output"
output_folder = "output_tif"

# Create the output folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)

# Loop through all CSV files in the input folder
for csv_file in os.listdir(input_folder):
    if csv_file.endswith(".csv"):
        # Load CSV data into a Numpy array
        csv_path = os.path.join(input_folder, csv_file)
        with open(csv_path, "r") as f:
            csv_data = list(csv.reader(f))
        output_data = np.array(csv_data, dtype=np.int32)  # Convert to appropriate(I think?) data type

        # Print debug information
        print("CSV file:", csv_file)
        print("Output data shape:", output_data.shape)
        print("Output data type:", output_data.dtype)
        print("Minimum value:", np.min(output_data))
        print("Maximum value:", np.max(output_data))

        # Define the output GeoTIFF file name
        output_tiff = os.path.join(output_folder, f"{os.path.splitext(csv_file)[0]}.tif")
