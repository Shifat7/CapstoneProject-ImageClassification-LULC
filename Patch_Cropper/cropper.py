import rasterio
from rasterio.windows import Window
import os

# Create a folder to store the cropped patches
output_folder = 'patches_test'
os.makedirs(output_folder, exist_ok=True)

# Open Vuthy's large GeoTIFF file
input_file = 'S2A_MSIL2A_20221118T001111_R073_T55HCV_20221118T115719_combined.tif'
with rasterio.open(input_file) as src:
    # Get the geotransform (affine transformation matrix(?))
    transform = src.transform
    # Get the CRS information
    crs = src.crs

    print(src.count)

    # Define the size of the patches (in pixels)
    patch_width = 224
    patch_height = 224

    # Loop through the large GeoTIFF file, extracting patches
    for i in range(0, src.width, patch_width):
        for j in range(0, src.height, patch_height):
            # Define the window for the current patch
            window = Window(i, j, patch_width, patch_height)

            # Read the data from the window
            patch_data = src.read(window=window)

            # Define the output file name for the patch
            output_file = os.path.join(output_folder, f'patch_{i}_{j}.tif')

            # Write the patch to a new GeoTIFF file
            with rasterio.open(output_file, 'w', driver='GTiff', width=patch_width, height=patch_height,
                               count=src.count, dtype=src.dtypes[0], crs=crs, transform=transform) as dst:
                dst.write(patch_data)

            print(f'Created patch: {output_file}')
