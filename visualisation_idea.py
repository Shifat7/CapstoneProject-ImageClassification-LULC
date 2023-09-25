# Credit to SSLTransformerRS GitHub repo

import csv
import argparse
import json
import os
import random
import numpy as np
import torch
import wandb
import torch.nn.functional as F
import torch.nn as nn
from distutils.util import strtobool
from tqdm import tqdm
from torchvision.models import resnet18, resnet50
import rasterio
from rasterio.transform import from_origin
from rasterio.coords import BoundingBox


# New set for visualisation test
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from dfc_sen12ms_dataset import DFCSEN12MSDataset, Seasons, S1Bands, S2Bands, LCBands

from dfc_dataset_sandbox import DFCDataset # use sandbox version

from Transformer_SSL.models.swin_transformer import * # refine to classes required
from utils import save_checkpoint_single_model, dotdictify
from Transformer_SSL.models import build_model

if torch.cuda.is_available():
    device = torch.device("cuda")
else:
    device = torch.device("cpu:0")

with open("configs/backbone_config.json", "r") as fp: # need to include this file!!!
    swin_conf = dotdictify(json.load(fp))

s1_backbone = build_model(swin_conf.model_config)

swin_conf.model_config.MODEL.SWIN.IN_CHANS = 13
s2_backbone = build_model(swin_conf.model_config)

# Data configurations:
data_config = {
    'train_dir': 'splits/', # path to the training directory, this is "ROIs0000_validation" as currently configured,
    'val_dir': 'splits/', # path to the validation directory, this is "ROIs0000_test" as currently configured,
    'train_mode': 'validation', # can be one of the following: 'test', 'validation'
    'val_mode': 'test', # can be one of the following: 'test', 'validation'
    'num_classes': 8, # number of classes in the dataset.
    'clip_sample_values': True, # clip (limit) values
    'train_used_data_fraction': 1, # fraction of data to use, should be in the range [0, 1]
    'val_used_data_fraction': 1,
    'image_px_size': 224, # image size (224x224)
    'cover_all_parts_train': True, # if True, if image_px_size is not 224 during training, we use a random crop of the image
    'cover_all_parts_validation': True, # if True, if image_px_size is not 224 during validation, we use a non-overlapping sliding window to cover the entire image
    'seed': 42,
}

val_dataset = DFCDataset(
    data_config['val_dir'],
    mode=data_config['val_mode'],
    clip_sample_values=data_config['clip_sample_values'],
    used_data_fraction=data_config['val_used_data_fraction'],
    image_px_size=data_config['image_px_size'],
    cover_all_parts=data_config['cover_all_parts_validation'],
    seed=data_config['seed'],
)

# SAMPLE CODE FOR SEGMENTATION OUTPUT

# create a new model's instance
model = DoubleSwinTransformerSegmentation(s1_backbone, s2_backbone, out_dim=data_config['num_classes'], device=device)

#model = model.to(device)

# EVENTUALLY iterate through all patches here (include all subsequent code in loop starting here)

# select a single patch from MPC data
currentPatch = 45 #iterator

# load desired segmentation checkpoint
model.load_state_dict(torch.load("checkpoints/swin-t-pixel-classification-balmy-universe-47-epoch-200.pth", map_location='cpu')) # replace path with desired checkpoint
model.to(device)

# prepare input
img = {"s1": torch.unsqueeze(val_dataset[currentPatch]['s1'], 0), "s2": torch.unsqueeze(val_dataset[currentPatch]['s2'], 0)} # adding an extra dimension for batch information
# may look different to the above based on the form of the MPC data

# evaluate using model
model.eval() # sets the model in evaluation mode
output = model(img) # pass input to model, 'output' is instance of DoubleSwinTransformerSegmentation

#TEST CODE
print(torch.argmax(output)) # get 'argmax' value (not sure what this is) for output

test = torch.max(output, dim=1)
print(test.indices)

output_arrays = test.indices.squeeze()

count = 0
for i in output_arrays:
    print(i)
    count += 1
print(str(count) + " pixels in x axis.")
print(str(output_arrays[count - 1].size(dim=0)) + " pixels in y axis")

# VISUALISATION CODE
val_dataset.test_visual(currentPatch, output_arrays)

# for each pixel in image patch,
    # open CSV write
    # write coordinate info? and classification category (integer) to CSV file
    # close CSV write
# Create the "output" folder if it doesn't exist
output_folder = "output"
os.makedirs(output_folder, exist_ok=True)

# Define the full path to the TIFF file
tif_filename = "splits/ROIs0000_test/dfc_0/ROIs0000_test_dfc_0_p45.tif"

# Extract data_info from the TIFF filename
data_info = os.path.splitext(os.path.basename(tif_filename))[0]

# Open the current patch using rasterio to obtain its CRS and bounds
with rasterio.open(tif_filename) as current_patch:
    crs = current_patch.crs
    bounds = current_patch.bounds
    transform = current_patch.transform  # GeoTransform

    # Calculate real-world coordinates for the top-left corner of the patch
    lon, lat = transform * (0, 0)

    # Calculate real-world coordinates for the center of the patch (adjust as needed)
    center_lon, center_lat = transform * (current_patch.width / 2, current_patch.height / 2)

    # Generate the dynamic CSV filename
    csv_filename = os.path.join(output_folder, f"output_data_{data_info}.csv")

    # Create a CSV file inside the output folder for writing
    with open(csv_filename, mode='w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)

        # Loop through the rows of output_arrays
        for y in range(output_arrays.shape[0]):
            for x in range(output_arrays.shape[1]):
                # Calculate the geographic coordinates within the patch
                lon_pixel, lat_pixel = transform * (x + 0.5, y + 0.5)  # Use center of each pixel

                # Get the classification category
                category = output_arrays[y, x].item()

                # Write the geographic coordinates and category to the CSV file
                csv_writer.writerow([lon_pixel, lat_pixel, category])

    # Print a message indicating the CSV file was created
    print(f"CSV file '{csv_filename}' created.")



tif_filename = "splits/ROIs0000_test/dfc_0/ROIs0000_test_dfc_0_p45.tif"

with rasterio.open(tif_filename) as current_patch:
    metadata = current_patch.meta
    print(metadata)


# 13/08/2023 - need to train a new segmentation model, change path and load it
# copy VM to new drive, likely faster

# # Construct the file path for the GeoTIFF file based on currentPatch
# tif_filename = f"ROIs0000_{data_config['val_mode']}_dfc_0_p{currentPatch}.tif"

# # Open the current patch using rasterio to obtain its CRS and bounds
# with rasterio.open(tif_filename) as current_patch:
#     crs = current_patch.crs
#     bounds = current_patch.bounds

# # Define the pixel size (replace with your actual values)
# pixel_width = 10.0 
# pixel_height = -10.0 

# # Create the GeoTIFF file
# geotiff_filename = os.path.join(output_folder, f"output_data_{data_info}.tif")

# with rasterio.open(
#     geotiff_filename,
#     'w',
#     driver='GTiff',
#     height=output_arrays.shape[0],  # Set the height to match the number of rows in the output
#     width=output_arrays.shape[1],   # Set the width to match the number of columns in the output
#     count=1,  # Number of bands in the image
#     dtype=output_arrays.dtype,     # Data type of the image (e.g., uint8, uint16, float32)
#     crs=crs,               # Use the CRS obtained from the current patch
#     transform=from_origin(bounds.left, bounds.top, pixel_width, pixel_height),  # GeoTransform
# ) as dst:
#     dst.write(output_arrays, 1)  # Write the segmentation results to the GeoTIFF

# # Print a message indicating the GeoTIFF file was created
# print(f"GeoTIFF file '{geotiff_filename}' created.")
