import rasterio
import matplotlib.pyplot as plt

# Can replace with the path to any of the patch files
patch_file = 'patches/patch_0_224.tif'

# Open the patch file
with rasterio.open(patch_file) as src:
    patch_data = src.read()

# Display the patch
plt.imshow(patch_data.transpose(1, 2, 0))
plt.title('Cropped Patch')
plt.axis('off')
plt.show()
