# Credit to SSLTransformerRS GitHub repo

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

# New set for visualisation test
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from dfc_sen12ms_dataset import DFCSEN12MSDataset, Seasons, S1Bands, S2Bands, LCBands

# New from Erik code for read patch from file
import rasterio
from enum import Enum

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
model = DoubleSwinTransformerSegmentationS2(s2_backbone, out_dim=data_config['num_classes'], device=device)

#model = model.to(device)

# EVENTUALLY iterate through all patches here (include all subsequent code in loop starting here)

# select a single patch from MPC data
currentPatch = 45 #iterator

# load desired segmentation checkpoint
model.load_state_dict(torch.load("checkpoints/swin-t-pixel-classification-charmed-puddle-99-epoch-4.pth", map_location='cpu')) # replace path with desired checkpoint
model.to(device)

# prepare input
#img = {"s1": torch.unsqueeze(val_dataset[currentPatch]['s1'], 0), "s2": torch.unsqueeze(val_dataset[currentPatch]['s2'], 0)}
img = {"s2": torch.unsqueeze(val_dataset[currentPatch]['s2'], 0)}
# may look different to the above based on the form of the MPC data
#print(torch.unsqueeze(val_dataset[currentPatch]['s2'], 0).shape) # [1, 13, 224, 224]

patch_file = 'Patch_Cropper/patches_test/patch_0_0.tif'
#with rasterio.open(patch_file) as src:
#    patch_data = src.read()

class S2Bands(Enum):
    B01 = aerosol = 1
    B02 = blue = 2
    B03 = green = 3
    B04 = red = 4
    B05 = re1 = 5
    B06 = re2 = 6
    B07 = re3 = 7
    B08 = nir1 = 8
    B08A = nir2 = 9
    B09 = vapor = 10
    B10 = cirrus = 11
    B11 = swir1 = 12
    B12 = swir2 = 13
    ALL = [B01, B02, B03, B04, B05, B06, B07, B08, B08A, B09, B10, B11, B12]
    RGB = [B04, B03, B02]
    NONE = None

bands = S2Bands.RGB.value
# adapted from dfc_sen12ms_dataset
with rasterio.open(patch_file) as patch:
    patch_data = patch.read()
    bounds = patch.bounds

# patch_data format is [[224[224], 224[224], 224[224]]]

#mpc_tensor = torch.zeros(1, 13, 224, 224)

#mpc_tensor[0, 0, 0, 0] = patch_data[0][0][0]
#mpc_tensor[0, 0, 0, 1] = patch_data[0][0][1]

#print(mpc_tensor[:, 1, 1, 1])

#for i in patch_data[1]:
#    print(i)

# convert numpy array to required size with patch_data.resize() WORKING HERE
mpc_tensor = torch.from_numpy(patch_data.astype('float32'))

print(mpc_tensor)
print(mpc_tensor.shape)

#patch_data = patch_data[None, :, :, :]
# need to add 'batch information' B as extra dimension at start of array
# need to reconfigure array

patch_img = {"s2": mpc_tensor} # create dictionary using same format
#patch_img = {"s2": torch.from_numpy(patch_data)} # create dictionary using same format

#print(img)
#print(patch_data)

# evaluate using model
model.eval() # sets the model in evaluation mode
output = model(patch_img) # pass input to model, 'output' is instance of DoubleSwinTransformerSegmentation
#output = model(img)

#TEST CODE
#print(torch.argmax(output)) # get 'argmax' value (not sure what this is) for output

test = torch.max(output, dim=1)
#print(test.indices)

output_arrays = test.indices.squeeze()

'''
Test segmentation output
count = 0
for i in output_arrays:
    print(i)
    count += 1
print(str(count) + " pixels in x axis.")
print(str(output_arrays[count - 1].size(dim=0)) + " pixels in y axis")'''

# VISUALISATION CODE
val_dataset.test_visual(currentPatch, output_arrays)

# for each pixel in image patch,
    # open CSV write
    # write coordinate info? and classification category (integer) to CSV file
    # close CSV write


# 13/08/2023 - need to train a new segmentation model, change path and load it
# copy VM to new drive, likely faster