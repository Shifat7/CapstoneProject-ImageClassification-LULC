import pystac
import planetary_computer
import rioxarray
import os
import csv
import rasterio

# Define a function to generate the output file path
def get_file_path(output_folder, file_name):
    return os.path.join(output_folder, f"{file_name}.tif")

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

    # List desired bands
    bands = ['AOT', 'B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B09', 'B11', 'B12', 'B8A']
    # Set the output folder
    output_folder = "DataFolder"

    # Create array to store tif file names for band specified
    band_files = []

    for band in bands:
        # Open the 'visual' asset
        asset_href = signed_item.assets[band].href

        ##ds = rioxarray.open_rasterio(asset_href)

        full_file_name = f"{file_name}_{band}"

        # Get the output file path
        output_path = get_file_path(output_folder, full_file_name)
    
        # Save the output file
        ##ds.rio.to_raster(output_path)
        ##print(f"Downloaded and saved {full_file_name}.tif to {output_path}")

        # Add file name to band_files array to read in later
        band_files.append(f"DataFolder/{full_file_name}.tif")



    # Stacker Code

    # Output folder for the combined GeoTIFF
    output_folder = "LargeStackedTifs"
    os.makedirs(output_folder, exist_ok=True)

    # Output file path for the combined GeoTIFF replace with name of large patch
    output_path = os.path.join(output_folder, f"{file_name}_combined.tif")

    # Open each band file
    band_datasets = [rasterio.open(band_file) for band_file in band_files]

    # Get metadata from the first band
    meta = band_datasets[0].meta
    meta.update({"count": 13})

    # Create a new GeoTIFF with multiple bands
    with rasterio.open(output_path, 'w', **meta) as dest:
        for i, band_ds in enumerate(band_datasets):
            dest.write(band_ds.read(1), i + 1)  # Write each band to the output file
            print(band_ds.read(1), i + 1)
            print(i)

    # Close the band datasets
    for band_ds in band_datasets:
        band_ds.close()

    print(f"Combined bands into {output_path}")
