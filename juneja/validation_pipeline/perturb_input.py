# AUTOGENERATED! DO NOT EDIT! File to edit: perturb_input.ipynb.

# %% auto 0
__all__ = ['apply_grey_patch', 'occu_perturb', 'noise_perturb_image', 'noise_perturb']

# %% perturb_input.ipynb 1
import numpy as np
from tensorflow import keras

# def apply_grey_patch(path, image, top_left_x, top_left_y, patch_size):


def apply_grey_patch(image, top_left_x, top_left_y, patch_size):
    patched_image = np.array(image, copy=True)
    patched_image[top_left_y:top_left_y + patch_size,
                  top_left_x:top_left_x + patch_size, :] = 0
#     img = keras.preprocessing.image.array_to_img(patched_image)
#     print(path)
#     img.save(path)
    return patched_image

# %% perturb_input.ipynb 2
import os
# import preprocess

#have a version with multiple occlusion blocks
# def occu_perturb(img_path, out_path, gt_saliency_map):
def occu_perturb(img_arr, gt_saliency_map):
  
    PATCH_SIZE = 60
#     image = preprocess.img_to_tensor(img_path)

#     image = keras.preprocessing.image.load_img(img_path, target_size=(300, 300))
#     image = keras.preprocessing.image.img_to_array(image)
    
    i = 0
    occluded_img_list = []
    for top_left_x in range(0, img_arr.shape[0], PATCH_SIZE):
        for top_left_y in range(0, img_arr.shape[1], PATCH_SIZE):
            # Apply the patch and display the image
#             path = out_path+'/'+ 'occluded_img_'+str(i)+'.jpg'
            
#           patched_image = apply_grey_patch(path,image, top_left_x, top_left_y, PATCH_SIZE)
            patched_image = apply_grey_patch(img_arr, top_left_x, top_left_y, PATCH_SIZE)
            occluded_img_list.append(patched_image)
            patched_image = patched_image.astype('float32') / 255.0
            i+=1
    return occluded_img_list

# %% perturb_input.ipynb 3
def noise_perturb_image(img_tensor, saliency_map, perturbation_strength=0.05, saliency_threshold=0.5, num_iterations=1, perturbation_prob=0.1):
    
    image = img_tensor.to(saliency_map.device)
    saliency_values = saliency_map.view(-1)
    threshold = torch.kthvalue(saliency_values, int((1 - saliency_threshold) * saliency_values.size(0)) + 1).values
    mask = torch.gt(saliency_map, threshold).float()
    
    # Perturb the image for a given number of iterations only at a random subset of the mask where the value is 1
    perturbed_image = image.clone()
    
    for i in range(num_iterations):
        perturbation_mask = (mask == 1) * (torch.rand_like(mask) < perturbation_prob).float()
        noise = torch.randn_like(perturbed_image) * perturbation_strength
        perturbation_mask = perturbation_mask.to(perturbed_image.device)  # Move perturbation_mask to the same device as perturbed_image
        noise = noise.to(perturbed_image.device)  # Move noise to the same device as perturbed_image
        perturbed_image = perturbed_image + perturbation_mask * noise
        perturbed_image = torch.clamp(perturbed_image, 0, 1)
    return perturbed_image

# %% perturb_input.ipynb 4
from preprocess import img_to_tensor
import torch
import matplotlib.pyplot as plt

# from run_pipe import inference

def noise_perturb(img_path, out_dir, gt_saliency_map):
    img_tensor = img_to_tensor(img_path)
    saliency_threshold = 0.5
    perturbation_strength = 0.1
    perturbation_prob = 0.1
    for i in range(10):
        perturbed_tensor = noise_perturb_image(img_tensor, gt_saliency_map, perturbation_strength, saliency_threshold, 1, perturbation_prob)
        image_array = perturbed_tensor.squeeze().permute(1,2,0).detach().cpu().numpy()
        image_array = (image_array - np.min(image_array)) / (np.max(image_array) - np.min(image_array))    
        fig, ax = plt.subplots()
        ax.imshow(image_array, cmap = 'turbo', alpha = 0.8)
        plt.axis('off')
        fig.savefig(f"{out_dir}/{i}_noise.jpeg")

        perturbation_strength -= 0.01
        saliency_threshold += 0.005
        
#         inference(perturbed_tensor, model, out_dir, sal_method)

#         perturbed_tensor = perturbed_tensor.type_as(gpu_reference_tensor)
#         saliency_map_perturbed, perturbed_idx = wrapped_model(perturbed_tensor)
        
#         with torch.no_grad():
#             output = model(perturbed_tensor)
#             perturbed_class = torch.argmax(output).item()
#             prob = torch.softmax(output, dim=1)[0, perturbed_class].item()
#             img = reverse_normalize(perturbed_tensor)
#             heatmap = visualize(img, saliency_map_perturbed)
#             hm = (heatmap.squeeze().numpy().transpose(1, 2, 0))
            
#             ax.imshow(hm, cmap='turbo', alpha = 0.8)
#             ax.set_title(f"Class: {classes[perturbed_idx]}({prob*100:.2f}%)")
#             fig.savefig(f"{out_dir}/saliency/after_noise/{i}_{idx2label[idx].replace(' ','-')}.jpeg")
#             plt.show()
