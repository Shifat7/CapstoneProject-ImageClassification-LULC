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

# load desired segmentation checkpoint
model.load_state_dict(torch.load("checkpoints/swin-t-pixel-classification-charmed-puddle-99-epoch-4.pth", map_location='cpu')) # replace path with desired checkpoint
model.to(device)

# prepare input

# select a single patch from MPC data
patch_file = 'Patch_Cropper/patches_test/patch_3360_7168.tif'

# adapted from dfc_sen12ms_dataset
with rasterio.open(patch_file) as patch:
    patch_data = patch.read()
    bounds = patch.bounds

mpc_tensor = torch.from_numpy(patch_data.astype('float32'))

# Code for normalisation of patch - credit dfc_dataset.py
s2_maxs = []
for b_idx in range(mpc_tensor.shape[0]):
    s2_maxs.append(
        torch.ones((mpc_tensor.shape[-2], mpc_tensor.shape[-1])) * mpc_tensor[b_idx].max().item() + 1e-5
    )
s2_maxs = torch.stack(s2_maxs)

mpc_tensor = mpc_tensor / s2_maxs

#mpc_tensor = mpc_tensor[None, :, :, :] has same function as the below
mpc_tensor = torch.unsqueeze(mpc_tensor, 0)

print(mpc_tensor)
print(mpc_tensor.shape) # output is now [1, 13, 224, 224] as desired

patch_img = {"s2": mpc_tensor} # create dictionary using same format as DFC
#patch_img = {"s2": torch.from_numpy(patch_data)} # create dictionary using same format

# evaluate using model
model.eval() # sets the model in evaluation mode
output = model(patch_img) # pass input to model, 'output' is instance of DoubleSwinTransformerSegmentation
#output = model(img)

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
val_dataset.test_visual_mpc(mpc_tensor, output_arrays)

# for each pixel in image patch,
    # open CSV write
    # write coordinate info? and classification category (integer) to CSV file
    # close CSV write