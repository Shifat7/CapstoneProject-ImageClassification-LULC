import os

import numpy as np
import pandas as pd
from PIL import Image
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from albumentations.pytorch import ToTensorV2
import albumentations as A
from rasterio.windows import Window
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset

from utils import AlbumentationsToTorchTransform
from dfc_sen12ms_dataset import DFCSEN12MSDataset, Seasons, S1Bands, S2Bands, LCBands

IGBP_map = {
    1: "Evergreen Needleleaf FOrests",
    2: "Evergreen Broadleaf Forests",
    3: "Deciduous Needleleaf Forests",
    4: "Deciduous Broadleaf Forests",
    5: "Mixed Forests",
    6: "Closed (Dense) Shrublands",
    7: "Open (Sparse) Shrublands",
    8: "Woody Savannas",
    9: "Savannas",
    10: "Grasslands",
    11: "Permanent Wetlands",
    12: "Croplands",
    13: "Urban and Built-Up Lands",
    14: "Croplands/Natural Vegetation Mosaics",
    15: "Permanent Snow and Ice",
    16: "Barren",
    17: "Water Bodies",
}

DFC_map = {
    1: "Forest",
    2: "Shrubland",
    3: "Savanna",
    4: "Grassland",
    5: "Wetlands",
    6: "Croplands",
    7: "Urban/Built-up",
    8: "Snow/Ice",
    9: "Barren",
    10: "Water",
}

# this is what we use in this work
DFC_map_clean = {
    0: "Forest",
    1: "Shrubland",
    2: "Grassland",
    3: "Wetlands",
    4: "Croplands",
    5: "Urban/Built-up",
    6: "Barren",
    7: "Water",
    255: "Invalid",
}

s1_mean = [0.7326, 0.3734]
s1_std = [0.1634, 0.1526]
s2_mean = [
    80.2513,
    67.1305,
    61.9878,
    61.7679,
    73.5373,
    105.9787,
    121.4665,
    118.3868,
    132.6419,
    42.9694,
    1.3114,
    110.6207,
    74.3797,
]
s2_std = [
    4.5654,
    7.4498,
    9.4785,
    14.4985,
    14.3098,
    20.0204,
    24.3366,
    25.5085,
    27.1181,
    7.5455,
    0.1892,
    24.8511,
    20.4592,
]

# Remapping IGBP classes to simplified DFC classes
IGBP2DFC = np.array([0, 1, 1, 1, 1, 1, 2, 2, 3, 3, 4, 5, 6, 7, 6, 8, 9, 10])


class DFCDataset(Dataset):
    """Pytorch wrapper for DFCSEN12MSDataset"""

    def __init__(
        self,
        base_dir,
        mode="dfc",
        transforms=None,
        simclr_dataset=False,
        clip_sample_values=True,
        used_data_fraction=1.0,
        image_px_size=256,
        cover_all_parts=False,
        balanced_classes=False,
        seed=42,
        sampling_seed=42,
        normalize=False,
        moby_transform=None,
    ):
        """cover_all_parts: if image_px_size is not 256, this makes sure that during validation the entire image is used
        during training, we read image parst at random parts of the original image, during vaildation, use a non-overlapping sliding window to cover the entire image"""
        super(DFCDataset, self).__init__()

        self.clip_sample_values = clip_sample_values
        self.used_data_fraction = used_data_fraction
        self.image_px_size = image_px_size
        self.cover_all_parts = cover_all_parts
        self.balanced_classes = balanced_classes
        self.simclr_dataset = simclr_dataset
        self.normalize = normalize
        self.moby_transform = moby_transform

        if mode == "dfc":
            self.seasons = [
                Seasons.AUTUMN_DFC,
                Seasons.SPRING_DFC,
                Seasons.SUMMER_DFC,
                Seasons.WINTER_DFC,
            ]
        elif mode == "test":
            self.seasons = [Seasons.TESTSET]
        elif mode == "validation":
            self.seasons = [Seasons.VALSET]
        elif mode == "sen12ms":
            self.seasons = [
                Seasons.SPRING,
                Seasons.SUMMER,
                Seasons.FALL,
                Seasons.WINTER,
            ]
        else:
            raise ValueError(
                "Unsupported mode, must be in ['dfc', 'sen12ms', 'test', 'validation']"
            )

        self.data = DFCSEN12MSDataset(base_dir)

        if self.balanced_classes:
            self.observations = pd.read_csv(
                os.path.join(base_dir, mode + "_observations_balanced_classes.csv"),
                header=0,
                # names=["Season", "Scene", "ID", "dfc_label", "copy_nr"],
            )
        else:
            self.observations = pd.read_csv(
                os.path.join(base_dir, mode + "_observations.csv"),
                header=None,
                names=["Season", "Scene", "ID"],
            )
        if self.cover_all_parts:
            num_img_parts = int(256**2 / self.image_px_size**2)
            obs = []
            for season, scene, idx in self.observations.values:
                for i in range(num_img_parts):
                    obs.append([season, scene, idx, i])

            self.observations = pd.DataFrame(
                obs, columns=["Season", "Scene", "ID", "ScenePart"]
            )

        self.observations = self.observations.sample(
            frac=self.used_data_fraction, random_state=sampling_seed
        ).sort_index()
        self.transforms = transforms
        self.mode = mode

        if self.transforms:
            augmentation = A.Compose(
                [
                    A.Affine(scale=1, translate_px=5, rotate=20),
                    A.RandomResizedCrop(208, 208, scale=(0.2, 1.0), p=1),
                    # RandomGrayscale(p=0.5),
                    # A.GaussianBlur(sigma_limit=[.1, 2.], p=0.5),
                    # A.HorizontalFlip(p=0.5),
                    # A.Normalize(mean=list(BAND_STATS["mean"].values()), std=list(BAND_STATS["std"].values()), max_pixel_value=255),
                    ToTensorV2(),
                ]
            )

            self.train_transforms = AlbumentationsToTorchTransform(augmentation)

        base_aug = A.Compose(
            [
                ToTensorV2(),
            ]
        )

        self.base_transform = AlbumentationsToTorchTransform(base_aug)

    def __getitem__(self, idx, s2_bands=S2Bands.ALL, transform=True, normalize=True):
        obs = self.observations.iloc[idx]
        season = Seasons[obs.Season[len("Seasons.") :]]

        if self.image_px_size != 256:
            # crop the data to self.image_px_size times self.image_px_size (e.g. 128x128)
            x_offset, y_offset = np.random.randint(0, 256 - self.image_px_size, 2)
            window = Window(x_offset, y_offset, self.image_px_size, self.image_px_size)

        else:
            window = None

        if self.mode != "sen12ms":
            # high-resolution LC (dfc) labels are not available for the entire dataset
            s1, s2, lc, dfc, bounds = [
                x.astype(np.float32) if type(x) == np.ndarray else x
                for x in self.data.get_s1_s2_lc_dfc_quad(
                    season,
                    obs.Scene,
                    int(obs.ID),
                    s1_bands=S1Bands.ALL,
                    s2_bands=s2_bands,
                    lc_bands=LCBands.LC,
                    dfc_bands=LCBands.DFC,
                    include_dfc=True,
                    window=window,
                )
            ]
            dfc[dfc == 3] = 0
            dfc[dfc == 8] = 0
            dfc[dfc >= 3] -= 1
            dfc[dfc >= 8] -= 1
            dfc -= 1
            dfc[dfc == -1] = 255

            dfc_unique, dfc_counts = np.unique(dfc, return_counts=True)
            dfc_label = dfc_unique[
                dfc_counts.argmax()
            ]  # this is already mapped to dfc in data.get_s1_s2_lc_dfc_quad
            dfc_label_str = DFC_map_clean[int(dfc_label)]

            dfc_multilabel = torch.tensor(
                [
                    class_idx
                    for class_idx, num in zip(dfc_unique, dfc_counts)
                    if num / self.image_px_size**2 >= 0.1 and class_idx != 255
                ]
            ).long()
            dfc_multilabel_one_hot = torch.nn.functional.one_hot(
                dfc_multilabel.flatten(), num_classes=8
            ).float()
            dfc_multilabel_one_hot = dfc_multilabel_one_hot.sum(
                dim=0
            )  # create one one-hot label for all classes
            # all classes which make up more than 10% of a scene, as per https://arxiv.org/pdf/2104.00704.pdf

        else:
            s1, s2, lc, bounds = [
                x.astype(np.float32) if type(x) == np.ndarray else x
                for x in self.data.get_s1_s2_lc_dfc_quad(
                    season,
                    obs.Scene,
                    int(obs.ID),
                    s1_bands=S1Bands.ALL,
                    s2_bands=s2_bands,
                    lc_bands=LCBands.LC,
                    dfc_bands=LCBands.DFC,
                    include_dfc=False,
                    window=window,
                )
            ]

            dfc = None

        # set savanna and ice label to 255, which is ignore_index of loss function
        # reduce other labels to 0-7
        # print("Number of savanna pixels:", lc[lc == 3].size)
        # print("Number of ice pixels:", lc[lc == 8].size)
        lc[lc == 3] = 0
        lc[lc == 8] = 0
        lc[lc >= 3] -= 1
        lc[lc >= 8] -= 1
        lc -= 1
        # print("Number of invalid pixels:", lc[lc == -1].size)
        lc[lc == -1] = 255

        # use the most frequent MODIS class as pseudo label
        lc_unique, lc_counts = np.unique(lc, return_counts=True)
        lc_label = lc_unique[
            lc_counts.argmax()
        ]  # this is already mapped to dfc in data.get_s1_s2_lc_dfc_quad
        lc_label_str = DFC_map_clean[int(lc_label)]

        lc_multilabel = torch.tensor(
            [
                class_idx
                for class_idx, num in zip(lc_unique, lc_counts)
                if num / self.image_px_size**2 >= 0.1 and class_idx != 255
            ]
        ).long()
        lc_multilabel_one_hot = torch.nn.functional.one_hot(
            lc_multilabel.flatten(), num_classes=8
        ).float()
        lc_multilabel_one_hot = lc_multilabel_one_hot.sum(dim=0)
        # all classes which make up more than 10% of a scene, as per https://arxiv.org/pdf/2104.00704.pdf

        # as per the baseline paper https://arxiv.org/pdf/2002.08254.pdf
        if self.clip_sample_values:
            s1 = np.clip(s1, a_min=-25, a_max=0)
            s1 = (
                s1 + 25
            )  # go from [-25,0] to [0,25] interval to make normalization easier
            s2 = np.clip(s2, a_min=0, a_max=1e4)

        if self.moby_transform is not None:
            img = np.concatenate([s1, s2])
            img = np.moveaxis(img, 0, -1)
            img1 = self.moby_transform[0](image=img)
            img2 = self.moby_transform[1](image=img)

            return {"img1": img1["image"], "img2": img2["image"], "idx": idx}

        if self.transforms is not None and transform:
            s1 = self.train_transforms(np.moveaxis(s1, 0, -1))
            s2 = self.train_transforms(np.moveaxis(s2, 0, -1))
            # lc = self.train_transforms(np.moveaxis(lc, 0, -1))
            # dfc = self.train_transforms(np.moveaxis(dfc, 0, -1))

        elif self.simclr_dataset:
            # specific to "normal SimCLR" training
            x = Image.fromarray(
                np.moveaxis((s2[[3, 2, 1], :, :] * 255).astype(np.uint8), 0, -1)
            )
            x1, x2 = self.simclr_transform(x)
            x = torch.tensor(np.moveaxis(np.array(x), -1, 0)).float()

            return {
                "x": x,
                "x1": x1,
                "x2": x2,
                "dfc_label": dfc_label,
                "dfc_multilabel_one_hot": dfc_multilabel_one_hot,
            }

        else:
            s1 = self.base_transform(np.moveaxis(s1, 0, -1))
            s2 = self.base_transform(np.moveaxis(s2, 0, -1))

        # normalize images channel wise
        s1_maxs = []
        for ch_idx in range(s1.shape[0]):
            s1_maxs.append(
                torch.ones((s1.shape[-2], s1.shape[-1])) * s1[ch_idx].max().item()
                + 1e-5
            )
        s1_maxs = torch.stack(s1_maxs)

        s2_maxs = []
        for b_idx in range(s2.shape[0]):
            s2_maxs.append(
                torch.ones((s2.shape[-2], s2.shape[-1])) * s2[b_idx].max().item() + 1e-5
            )
        s2_maxs = torch.stack(s2_maxs)

        if normalize or self.normalize:
            s1 = s1 / s1_maxs
            s2 = s2 / s2_maxs

            # if not torch.isnan(s1).any():
            #    assert s1.max() <= 1 and s1.min() >= 0 and s2.max() <= 1 and s2.min() >= 0, print(f"Normalization went wrong for idx: {str(idx)}")

        output = {
            "s1": s1,
            "s2": s2,
            "lc": lc,
            "bounds": bounds,
            "idx": idx,
            "lc_label": lc_label,
            "lc_label_str": lc_label_str,
            "lc_multilabel": lc_multilabel.numpy().tolist(),
            "lc_multilabel_one_hot": lc_multilabel_one_hot,
            "season": str(season.value),
            "scene": obs.Scene,
            "id": obs.ID,
        }

        output_tensor = {
            "s1": s1,
            "s2": s2,
            "lc": lc,
            "idx": idx,
            "lc_label": lc_label,
            "lc_multilabel_one_hot": lc_multilabel_one_hot,
        }  # new pytorch version does not allow non-tensor values in dataloader

        if dfc is not None:
            output.update(
                {
                    "dfc": dfc,
                    "dfc_label": dfc_label,
                    "dfc_label_str": dfc_label_str,
                    "dfc_multilabel_one_hot": dfc_multilabel_one_hot,
                }
            )  # , "dfc_multilabel" : dfc_multilabel.numpy().tolist()})

            output_tensor.update(
                {
                    "dfc": dfc,
                    "dfc_label": dfc_label,
                    "dfc_multilabel_one_hot": dfc_multilabel_one_hot,
                }
            )  # , "dfc_multilabel" : dfc_multilabel.numpy().tolist()})
            # print(",".join([k + " : " + str(np.array(v).shape) for k,v in output_tensor.items()]))
            return output_tensor
        else:
            # print(",".join([k + " : " + str(np.array(v).shape) for k,v in output_tensor.items()]))
            return output_tensor

    def __len__(self):
        return self.observations.shape[0]
    
    def testSqueeze(self, idx):
        sample = self.__getitem__(idx, s2_bands=S2Bands.RGB, transform=False) # this is an object with s1, s2, lc and dfc data included

        dfc = sample.get("dfc") # get the dfc data from the bigger object

        dfc_data = dfc.squeeze()
        
        count = 0
        for i in dfc_data:
            print(i)
            count += 1
        print(str(count) + " pixels in x axis.")
        print(str(dfc_data[count - 1].size) + " pixels in y axis")

    def test_visual_mpc(self, patch_img, model_output, transform=False): # test function: self = Class instance, idx = patch ID
        #sample = self.__getitem__(idx, s2_bands=S2Bands.RGB, transform=transform) #get the patch object

        s2 = patch_img[:, [2,3,4], :, :]
        s2 = torch.squeeze(s2, 0)
        print(s2.shape)
        #dfc = sample.get("dfc") GET CLASSIFIED DFC DATA FROM SAMPLE
        # fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(35, 5))
        fig, axs = plt.subplots(1, 3, figsize=(15, 5)) # CHANGE SECOND PARAMETER TO ADJUST NUMBER OF ROWS OF SUBPLOTS
        img = np.moveaxis(s2.numpy(), 0, -1)
        img = img / img.max(axis=(0, 1))
        axs[0].imshow(img)
        axs[0].set_title("Sentinel-2 RGB")

        divider2 = make_axes_locatable(axs[1])
        cax2 = divider2.append_axes("right", size="5%", pad=0.05)
        dfc_data = model_output # see if works? same arrays printed to screen
        data_stat = dfc_data[dfc_data != 255] # if operation
        data_stat = data_stat[np.isnan(data_stat) == False] # if operation
        #mi, ma = int(np.min(data_stat)), int(np.max(data_stat))
        cmap = plt.get_cmap("RdBu", 8) # choose a colour map

        print(model_output.squeeze().numpy())

        dfc_plot = model_output.reshape([224, 224]).numpy()
        #dfc_plot[dfc_plot == 255] = np.nan

        mat = axs[1].matshow(dfc_plot, cmap=cmap, vmin=0 - 0.5, vmax=7 + 0.5) # create the plot
        cax2 = plt.colorbar(
            mat, ticks=np.arange(8), cax=cax2, orientation="vertical"
        )

        axs[1].set_title("Inference Output")
        axs[1].axis(False)

        unique, counts = np.unique(dfc_plot, return_counts=True)
        labels = [DFC_map[int(u)] for u in unique if int(u) in DFC_map.keys()]
        counts_normalized = counts / counts.sum()
        bottom = 0
        bar_width = 0.3  

        for idx, (label, count) in enumerate(zip(labels, counts_normalized)):
            axs[2].bar(0, count, bottom=bottom, label=label, width=bar_width)
            # Display the percentage next to each section
            percentage = "{:.1f}%".format(count*100)
            axs[2].text(0.01, bottom + count/2, percentage, ha='center', va='center')
            bottom += count

        
        axs[2].spines['right'].set_visible(False)
        axs[2].spines['top'].set_visible(False)

        axs[2].set_title("Distribution of Output Values", pad=10)  
        axs[2].set_ylabel("Percentage")
        axs[2].set_ylim(0, 1.2)  
        axs[2].set_xlim(-0.5, 0.5)  
        axs[2].text(0, 1.05, '100%', ha='center', va='center') 
        axs[2].set_xticks([]) 
        axs[2].set_yticks([])   
        axs[2].set_xticklabels([])
        axs[2].set_yticklabels([])   
        axs[2].legend(loc="upper left", bbox_to_anchor=(1,1))

        plt.tight_layout()
            
        plt.show()


    def test_visual(self, idx, model_output, transform=False): # test function: self = Class instance, idx = patch ID
        sample = self.__getitem__(idx, s2_bands=S2Bands.RGB, transform=transform) #get the patch object

        s2 = sample.get("s2") # shape is [3, 224, 224]
        #dfc = sample.get("dfc") GET CLASSIFIED DFC DATA FROM SAMPLE

        fig, axs = plt.subplots(1, 2, figsize=(25, 5)) # CHANGE SECOND PARAMETER TO ADJUST NUMBER OF ROWS OF SUBPLOTS
        img = np.moveaxis(s2.numpy(), 0, -1)
        img = img / img.max(axis=(0, 1))
        axs[0].imshow(img)
        axs[0].set_title("Sentinel-2 RGB")

        divider2 = make_axes_locatable(axs[1])
        cax2 = divider2.append_axes("right", size="5%", pad=0.05)
        dfc_data = model_output # see if works? same arrays printed to screen
        data_stat = dfc_data[dfc_data != 255] # if operation
        data_stat = data_stat[np.isnan(data_stat) == False] # if operation
        #mi, ma = int(np.min(data_stat)), int(np.max(data_stat))
        cmap = plt.get_cmap("RdBu", 8) # choose a colour map

        print(model_output.squeeze().numpy())

        dfc_plot = model_output.reshape([224, 224]).numpy()
        #dfc_plot[dfc_plot == 255] = np.nan

        mat = axs[1].matshow(dfc_plot, cmap=cmap, vmin=0 - 0.5, vmax=7 + 0.5) # create the plot
        cax2 = plt.colorbar(
            mat, ticks=np.arange(8), cax=cax2, orientation="vertical"
        )

        axs[1].set_title("Inference Output")
        axs[1].axis(False)

        plt.show()

    
    def cheeky(self, idx, transform=False): # test function: self = Class instance, idx = patch ID
        sample = self.__getitem__(idx, s2_bands=S2Bands.RGB, transform=transform) #get the patch object

        s2 = sample.get("s2")
        dfc = sample.get("dfc")

        fig, axs = plt.subplots(1, 2, figsize=(25, 5)) 
        img = np.moveaxis(s2.numpy(), 0, -1)
        img = img / img.max(axis=(0, 1))
        axs[0].imshow(img)
        axs[0].set_title("Sentinel-2 RGB")

        if dfc is not None:
            divider2 = make_axes_locatable(axs[1])
            cax2 = divider2.append_axes("right", size="5%", pad=0.05)
            dfc_data = dfc.squeeze()
            data_stat = dfc_data[dfc_data != 255] # if operation
            data_stat = data_stat[np.isnan(data_stat) == False] # if operation
            mi, ma = int(np.min(data_stat)), int(np.max(data_stat))
            cmap = plt.get_cmap("RdBu", ma - mi + 1) # choose a colour map

            dfc_plot = dfc.squeeze().copy()
            dfc_plot[dfc_plot == 255] = np.nan

            mat = axs[1].matshow(dfc_plot, cmap=cmap, vmin=mi - 0.5, vmax=ma + 0.5) # create the plot
            cax2 = plt.colorbar(
                mat, ticks=np.arange(mi, ma + 1), cax=cax2, orientation="vertical"
            )

            axs[1].set_title("DFC LC")
        else:
            axs[1].set_title("No HR LC available")
        axs[1].axis(False)

        plt.show()


    def visualize_observation(self, idx, transform=False):
        sample = self.__getitem__(idx, s2_bands=S2Bands.RGB, transform=transform)

        s1 = sample.get("s1")
        s2 = sample.get("s2")
        dfc = sample.get("dfc")

        fig, axs = plt.subplots(1, 4, figsize=(25, 5)) # CHANGE SECOND VALUE (CURRENTLY 4 TO ADJUST NUMBER OF SUBPLOTS)
        img = np.moveaxis(s2.numpy(), 0, -1)
        img = img / img.max(axis=(0, 1))
        axs[0].imshow(img)
        axs[0].set_title("Sentinel-2 RGB")
        axs[1].imshow(s1[0])
        axs[1].set_title("Sentinel-1 VV polarization")
        axs[2].imshow(s1[1])
        axs[2].set_title("Sentinel-2 VH polarization")

        if dfc is not None:
            divider2 = make_axes_locatable(axs[3])
            cax2 = divider2.append_axes("right", size="5%", pad=0.05)
            dfc_data = dfc.squeeze()
            data_stat = dfc_data[dfc_data != 255]
            data_stat = data_stat[np.isnan(data_stat) == False]
            mi, ma = int(np.min(data_stat)), int(np.max(data_stat))
            cmap = plt.get_cmap("RdBu", ma - mi + 1) # cmap short for colormap

            dfc_plot = dfc.squeeze().copy()
            dfc_plot[dfc_plot == 255] = np.nan

            # TEST CODE
            count = 0
            for i in dfc_plot:
                print(i)
                count += 1
            print(str(count) + " pixels in x axis.")
            print(str(dfc_plot[count - 1]) + " pixels in y axis")
            print(dfc.squeeze())

            mat = axs[3].matshow(dfc_plot, cmap=cmap, vmin=mi - 0.5, vmax=ma + 0.5) # create the plot
            cax2 = plt.colorbar(
                mat, ticks=np.arange(mi, ma + 1), cax=cax2, orientation="vertical"
            )

            axs[3].set_title("DFC LC")
        else:
            axs[3].set_title("No HR LC available")
        axs[3].axis(False)

        plt.show()

    def visualize_observation_old(self, idx, transform=False):
        """this does not handle 255 (ignore_index) values in the LC maps
        and no LC colorbars"""

        sample = self.__getitem__(idx, s2_bands=S2Bands.RGB, transform=transform)
        s1 = sample.get("s1")
        s2 = sample.get("s2")
        lc = sample.get("lc")
        dfc = sample.get("dfc")

        fig, axs = plt.subplots(1, 5, figsize=(25, 5))
        img = np.moveaxis(s2.numpy(), 0, -1)
        img = img / img.max(axis=(0, 1))
        axs[0].imshow(img)
        axs[0].set_title("Sentinel-2 RGB")
        axs[1].imshow(s1[0])
        axs[1].set_title("Sentinel-1 VV polarization")
        axs[2].imshow(s1[1])
        axs[2].set_title("Sentinel-2 VH polarization")
        lc_plot = lc.squeeze().copy()
        lc_plot[lc_plot == 255] = np.nan
        axs[3].imshow(lc_plot)
        # axs[3].set_title("MODIS LC\n" + sample.get("igbp_label_str") + "\n" + sample.get("dfc_label_str"))

        if dfc is not None:
            dfc_plot = dfc.squeeze().copy()
            dfc_plot[dfc_plot == 255] = np.nan
            axs[4].imshow(dfc_plot)
            axs[4].set_title("HR LC")
        else:
            axs[4].set_title("No HR LC available")
        plt.show()


