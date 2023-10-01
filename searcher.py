import os
import rasterio
from typing import Tuple, List
from rasterio.warp import transform

def get_patches_within_bbox(ne_corner: Tuple[float, float], sw_corner: Tuple[float, float], folder_path: str = 'output') -> List[str]: # Will need to modify to the folder storing the cropped pre-segmentation patches
    # Define the destination CRS as EPSG:4326 (WGS 84) 
    dst_crs = rasterio.crs.CRS.from_epsg(4326)

    # List to store file names that match criteria
    matching_files = []
    
    # Loop through each file in the folder
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.tif'):
            file_path = os.path.join(folder_path, file_name)
            
            # Open the file to check its top-left corner coordinates
            with rasterio.open(file_path) as dataset:
                # Get the geospatial coordinates of the top-left corner in the native CRS
                nw_coords_native = dataset.transform * (0, 0)
                
                # Convert the coordinates to EPSG:4326 so that they are the geo coords
                nw_coords_4326 = transform(dataset.crs, dst_crs, [nw_coords_native[0]], [nw_coords_native[1]])
                nw_lon, nw_lat = nw_coords_4326[0][0], nw_coords_4326[1][0]
                
                # Check if the converted coordinates fall within the provided bounding box
                if sw_corner[0] <= nw_lon <= ne_corner[0] and sw_corner[1] <= nw_lat <= ne_corner[1]:
                    matching_files.append(file_name)
    
    return matching_files

# TESTING
ne_corner_box = (141.0245, -35.2229)
sw_corner_box = (140.9751, -35.2633)
matching_files = get_patches_within_bbox(ne_corner_box, sw_corner_box)
print(matching_files)