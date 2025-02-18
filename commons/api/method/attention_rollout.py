# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../abid/api_notebooks/attention_rollout.ipynb.

# %% auto 0
__all__ = ['rollout', 'VITAttentionRollout', 'grad_rollout', 'VITAttentionGradRollout', 'vit_saliency_map']

# %% ../../../abid/api_notebooks/attention_rollout.ipynb 5
import numpy as np
import torch
from torchvision import transforms

# %% ../../../abid/api_notebooks/attention_rollout.ipynb 8
def rollout(attentions, discard_ratio, head_fusion):
    """
    Gets attention matrices and returns a saliency map by propagating attention values across ViT
    transformer layers.
    For more information, consult the documentation.
    
    input :
      - attentions : list (A list of square tensor containing self-attention value for q,k of each token)
      - discard_ratio : float32 (The percentage of attentions with low values that be dropped)
      - head_fusion : str ("mean", "max", "min" defines the mode of mixing attentions from different heads)
      
    return :
      - cls_mask : ndarray (Saliency map based on the classification token of DeiT)
      - token_mask : ndarray (Saliency map based on the knowledge distillation token of DeiT)
    """
    result = torch.eye(attentions[0].size(-1))
    with torch.no_grad():
        
        for attention in attentions: # Attention shape: (1, 3, 197, 197)
            if head_fusion == "mean":
                attention_heads_fused = attention.mean(axis=1)
            elif head_fusion == "max":
                attention_heads_fused = attention.max(axis=1)[0] # # shape: (1, 197, 197)
                # print(f"Shape before max is {attention.shape}, After: {attention.max(axis=1)}")
            elif head_fusion == "min":
                attention_heads_fused = attention.min(axis=1)[0]
            else:
                raise "Pick a proper head fusion mode"

            # Drop the lowest attentions, but
            # don't drop the class token
            # print(f"attention heads fused size : {attention_heads_fused.size(0)}")
            flat = attention_heads_fused.view(attention_heads_fused.size(0), -1) # Shape : (1, 197*197)
            _, indices = flat.topk(int(flat.size(-1)*discard_ratio), -1, False)
            # print(sum(1 if i == 0 else 0 for i in indices[0]))
            # print(indices.shape)
            indices = indices[indices != 0]
            flat[0, indices] = 0

            I = torch.eye(attention_heads_fused.size(-1))
            a = (attention_heads_fused + 1.0*I)/2
            a = a / a.sum(dim=-1) # Shape : (1, 197, 197)
            a = a[0]

            result = torch.matmul(a, result) # Shape: (1, 197, 197)
                                             # How much information do we get from the token j
                                             # in prev. layer (result) into the token i here (a)
    
    # Look at the total attention between the class token,
    # and the image patches
    cls_mask = result[0, 2:] # Shape : (196)
    token_mask = result[1, 2:] # Shape : (196)
    
    # In case of 224x224 image, this brings us from 196 to 14
    width = int(cls_mask.size(-1)**0.5)
    cls_mask = cls_mask.reshape(width, width).numpy() # Shape : (14, 14)
    cls_mask = cls_mask / np.max(cls_mask)
    
    width = int(token_mask.size(-1)**0.5)
    token_mask = token_mask.reshape(width, width).numpy() # Shape : (14, 14)
    token_mask = token_mask / np.max(token_mask)
    return cls_mask, token_mask

class VITAttentionRollout:
    def __init__(self, model, attention_layer_name='attn_drop', head_fusion="mean",
        discard_ratio=0.9):
        self.model = model
        self.head_fusion = head_fusion
        self.discard_ratio = discard_ratio
        for name, module in self.model.named_modules():
            if attention_layer_name in name:
                module.register_forward_hook(self.get_attention)

        self.attentions = []

    def get_attention(self, module, input, output):
        self.attentions.append(output.cpu())

    def __call__(self, input_tensor):
        self.attentions = []
        with torch.no_grad():
            output = self.model(input_tensor)

        return rollout(self.attentions, self.discard_ratio, self.head_fusion), output

# %% ../../../abid/api_notebooks/attention_rollout.ipynb 9
def grad_rollout(attentions, gradients, discard_ratio):
    """
    Gets attention matrices and returns a saliency map (based on a specific class label) by
    propagating attention values across ViT transformer layers.
    
    input :
      - attentions : list (A list of square tensor containing self-attention value for q,k of each token)
      - gradients : list (A list of class specific gradients collected through hooking with backward process of the model)
      - discard_ratio : float32 (The percentage of attentions with low values that be dropped)
      
    return :
      - mask : ndarray (Saliency map based on the classification token of DeiT)
    """
    result = torch.eye(attentions[0].size(-1))
    with torch.no_grad():
        for attention, grad in zip(attentions, gradients):                
            weights = grad
            attention_heads_fused = (attention*weights).mean(axis=1)
            attention_heads_fused[attention_heads_fused < 0] = 0

            # Drop the lowest attentions, but
            # don't drop the class token
            flat = attention_heads_fused.view(attention_heads_fused.size(0), -1)
            _, indices = flat.topk(int(flat.size(-1)*discard_ratio), -1, False)
            #indices = indices[indices != 0]
            flat[0, indices] = 0

            I = torch.eye(attention_heads_fused.size(-1))
            a = (attention_heads_fused + 1.0*I)/2
            a = a / a.sum(dim=-1)
            result = torch.matmul(a, result)
    
    # Look at the total attention between the class token,
    # and the image patches
    mask = result[0, 0 , 1 :]
    # In case of 224x224 image, this brings us from 196 to 14
    width = int(mask.size(-1)**0.5)
    mask = mask.reshape(width, width).numpy()
    mask = mask / np.max(mask)
    return mask

class VITAttentionGradRollout:
    def __init__(self, model, attention_layer_name='attn_drop',
        discard_ratio=0.9):
        self.model = model
        self.discard_ratio = discard_ratio
        for name, module in self.model.named_modules():
            if attention_layer_name in name:
                module.register_forward_hook(self.get_attention)
                module.register_backward_hook(self.get_attention_gradient)

        self.attentions = []
        self.attention_gradients = []

    def get_attention(self, module, input, output):
        self.attentions.append(output.cpu())

    def get_attention_gradient(self, module, grad_input, grad_output):
        self.attention_gradients.append(grad_input[0].cpu())

    def __call__(self, input_tensor, category_index):
        self.model.zero_grad()
        output = self.model(input_tensor)
        category_mask = torch.zeros(output.size()).to(device)
        category_mask[:, category_index] = 1
        loss = (output*category_mask).sum()
        loss.backward()

        return grad_rollout(attentions=self.attentions,
                            gradients=self.attention_gradients,
                            discard_ratio=self.discard_ratio)

# %% ../../../abid/api_notebooks/attention_rollout.ipynb 10
def vit_saliency_map(img, model, discard_ratio=0.9,
                     head_fusion='max', category_index=None, use_cuda=True):
    """
    Creates saliency map for an image using attention rollout within DeiT.
    
    input :
      - img : PIL Image (Image to be forwarded to the model)
      - model : function (DeiT model to be used)
      - discard_ratio : float32 (Optional parameter, defining the percentage of low values to be dropped)
      - head_fusion : str ("mean", "max", "min" defines the mode of mixing attentions from different heads)
      - category_index : int (Optional parameter, defining the label of the image)
      - use_cuda : boolean (Should cuda be used or not)
      
    return :
      - probs : torch.tensor (Probabilites distribution of the model)
      - cat_idx : int (Label predicted by the model)
      - masks : ndarray (Saliency generated through attention rollout process)
    """
    gpu_reference_tensor = next(model.parameters())

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
    ])
    
    input_tensor = transform(img).unsqueeze(0)
    if use_cuda: input_tensor = input_tensor.cuda()

    attention_rollout = VITAttentionRollout(model, head_fusion=head_fusion, 
                                            discard_ratio=discard_ratio)
    masks, output = attention_rollout(input_tensor)

    probs = torch.nn.functional.softmax(output, dim=1)
    cat_idx = torch.argmax(probs).item()
    
    return probs, cat_idx, masks
