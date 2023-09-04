import pystac
import planetary_computer
import rioxarray
import os
import csv

# Replace with the CSV file containing file names
csv_file = "input.csv"

# Read the CSV file to get a list of file names
file_names = []
with open(csv_file, 'r') as csv_file:
    csv_reader = csv.reader(csv_file)
    for row in csv_reader:
        file_names.extend(row)

# Loop through the list of file names and download each one
for file_name in file_names:
    # Construct the item_url by appending the file name to the base URL
    item_url = f"https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a/items/{file_name}"
    
    # Load the individual item metadata and sign the assets
    item = pystac.Item.from_file(item_url)
    signed_item = planetary_computer.sign(item)

    # Open the 'visual' asset
    asset_href = signed_item.assets["visual"].href
    ds = rioxarray.open_rasterio(asset_href)

    # Set the output folder
    output_folder = "C:\\Users\\yivut\\DataFolder"

    # Define a function to generate the output file path
    def get_file_path(output_folder, file_name):
        return os.path.join(output_folder, f"{file_name}.tif")

    # Get the output file path
    output_path = get_file_path(output_folder, file_name)

    # Save the output file
    ds.rio.to_raster(output_path)
    print(f"Downloaded and saved {file_name}.tif to {output_path}")
