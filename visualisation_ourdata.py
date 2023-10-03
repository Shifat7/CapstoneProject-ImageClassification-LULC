# Credit to SSLTransformerRS GitHub repo


import json
import os
import csv
import numpy as np
import torch
import torch.nn.functional as F
import torch.nn as nn
from distutils.util import strtobool
from tqdm import tqdm
from torchvision.models import resnet18, resnet50
import rasterio

from dfc_dataset_sandbox import DFCDataset # use sandbox version

from Transformer_SSL.models.swin_transformer import * # refine to classes required
from utils import dotdictify
from Transformer_SSL.models import build_model

def main(patch_names):
    print (patch_names)
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


    # create a new model's instance
    model = DoubleSwinTransformerSegmentationS2(s2_backbone, out_dim=data_config['num_classes'], device=device)

    # load desired segmentation checkpoint (pick in GUI)
    model.load_state_dict(torch.load("swin-t-pixel-classification-charmed-puddle-99-epoch-4.pth", map_location='cpu')) # replace path with desired checkpoint
    model.to(device)

    # array of patch names (feed in from input.csv file or pick in GUI)
    #patch_names = ['S2A_MSIL2A_20220108T002711_R016_T54HWF_20220110T213759_combined_01_01', 'S2A_MSIL2A_20220108T002711_R016_T54HWF_20220110T213759_combined_01_02']

    input_folder = os.path.join('Patch_Cropper', 'patches_test') # set input folder for complete data set (i.e., entire state)
    # patch_names = [file for file in os.listdir(input_folder) if file.endswith('.tif')] # all patches under input directory

    for patch_name in patch_names:

        patch_file = os.path.join(input_folder, patch_name)

        # adapted from dfc_sen12ms_dataset
        with rasterio.open(patch_file) as patch:
            patch_data = patch.read()
            bounds = patch.bounds

        mpc_tensor = torch.from_numpy(patch_data.astype('float32')) # create input tensor of float32 values

        # Code for normalisation of patch - credit dfc_dataset.py
        s2_maxs = []
        for b_idx in range(mpc_tensor.shape[0]):
            s2_maxs.append(
                torch.ones((mpc_tensor.shape[-2], mpc_tensor.shape[-1])) * mpc_tensor[b_idx].max().item() + 1e-5
            )
        s2_maxs = torch.stack(s2_maxs)

        mpc_tensor = mpc_tensor / s2_maxs

        mpc_tensor = torch.unsqueeze(mpc_tensor, 0) # add dimension at first position

        print(mpc_tensor)
        print(mpc_tensor.shape) # output is now [1, 13, 224, 224] as desired

        patch_img = {"s2": mpc_tensor} # create dictionary using same format as DFC

        # evaluate using model
        model.eval() # sets the model in evaluation mode
        output = model(patch_img) # pass input to model, 'output' is instance of DoubleSwinTransformerSegmentation
        #output = model(img)

        test = torch.max(output, dim=1)
        #print(test.indices)

        output_arrays = test.indices.squeeze()

        # VISUALISATION CODE
        val_dataset.test_visual_mpc(mpc_tensor, output_arrays)


        
        # CSV OUTPUT

        # Get the spatial information from the GeoTIFF file
        with rasterio.open(patch_file) as current_patch:
            metadata = current_patch.meta
            transform = current_patch.transform

        # Create the "output" folder if it doesn't exist
        output_folder = "output"
        os.makedirs(output_folder, exist_ok=True)

        # Get the filename of the current TIF patch
        tif_filename = patch_name

        # Remove the file extension to use as data_info
        data_info = os.path.splitext(tif_filename)[0]

        # Generate the dynamic CSV filename
        csv_filename = os.path.join(output_folder, f"output_data_{data_info}.csv")

        # Create a CSV file inside the "output" folder for writing
        with open(csv_filename, mode='w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
        
            # Write a header row with column names
            csv_writer.writerow(["Latitude", "Longitude", "Class"])
        
            # Loop through the rows of output_arrays
            for row_index, row in enumerate(output_arrays):
                for col_index, class_value in enumerate(row):
                    # Calculate the geographic coordinates for each pixel
                    pixel_coordinates = transform * (col_index, row_index)
                
                    # Convert tensor element to a Python scalar
                    class_value_scalar = class_value.item()
                
                    # Write the coordinates and class value to the CSV file
                    csv_writer.writerow([pixel_coordinates[0], pixel_coordinates[1], class_value_scalar])
        
                
        # Print a message indicating the CSV file was created
        print(f"CSV file '{csv_filename}' created.")

        # ADD BAND TO GEOTIFF WITH SEGMENTATION CLASSES

        # Create a new GeoTIFF file with an additional band for segmentation classes 
        # We can setup to overwrite the old patch here or delete the old patch after to save space
        output_tif_filename = os.path.join(output_folder, f"output_patch_{patch_name}")

        # Create a copy of the input patch as a starting point for the output patch
        with rasterio.open(patch_file) as input_patch:
            output_meta = input_patch.meta
            output_meta['count'] += 1  # Increment the number of bands for the new class band

            with rasterio.open(output_tif_filename, 'w', **output_meta) as output_patch:
                # Copy the existing bands to the new GeoTIFF
                for i in range(1, input_patch.count + 1):
                    output_patch.write(input_patch.read(i), i)

                # Add the segmentation classes as an additional band (band number is input_patch.count + 1)
                output_patch.write(output_arrays, input_patch.count + 1)

        print(f"GeoTIFF file '{output_tif_filename}' created.")
