import os
import rasterio
from typing import Tuple, List
from rasterio.warp import transform
from rasterio.errors import CRSError

def get_patches_within_bbox(ne_corner: Tuple[float, float], sw_corner: Tuple[float, float], folder_path: str = 'Patch_Cropper/patches_test') -> List[str]:
    """
    Retrieves raster files within a specified bounding box based on their top-left corner coordinates.
    
    Parameters:
    - ne_corner (Tuple[float, float]): Northeast corner of bounding box.
    - sw_corner (Tuple[float, float]): Southwest corner of bounding box.
    - folder_path (str): Directory where the raster files are stored. Default is 'output'.
    
    Returns:
    List[str]: List of matching raster files.
    """
    
    print(f"Received coordinates: NE - {ne_corner}, SW - {sw_corner}")
    
    # Define the destination CRS as EPSG:4326 (WGS 84) 
    dst_crs = rasterio.crs.CRS.from_epsg(4326)

    matching_files = []
    
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.tif'):
            file_path = os.path.join(folder_path, file_name)
            
            try:
                with rasterio.open(file_path) as dataset:
                    # Check if dataset has a valid CRS
                    if not dataset.crs:
                        print(f"File {file_name} does not have a valid CRS. Skipping...")
                        continue

                    nw_coords_native = dataset.transform * (0, 0)
                    nw_coords_4326 = transform(dataset.crs, dst_crs, [nw_coords_native[0]], [nw_coords_native[1]])
                    nw_lon, nw_lat = nw_coords_4326[0][0], nw_coords_4326[1][0]
                    
                    if sw_corner[0] <= nw_lon <= ne_corner[0] and sw_corner[1] <= nw_lat <= ne_corner[1]:
                        matching_files.append(file_name)

            except rasterio.errors.CRSError:
                print(f"Error processing file: {file_name}. Skipping...")
    
    print("Matching files:", matching_files)
    return matching_files

# Uncomment below for testing
# ne_corner_box = (141.0245, -35.2229)
# sw_corner_box = (140.9751, -35.2633)
# matching_files = get_patches_within_bbox(ne_corner_box, sw_corner_box)
