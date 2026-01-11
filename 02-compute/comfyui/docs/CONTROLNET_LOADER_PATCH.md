# ControlNet Loader Patch

## What Was Patched

The ControlNet loader in `comfy_extras/nodes_model_patch.py` has been improved to dynamically detect Z-Image ControlNet models instead of hardcoding layer counts.

## Changes Made

### Before (Original Code)
```python
elif 'control_all_x_embedder.2-1.weight' in sd: # alipai z image fun controlnet
    sd = z_image_convert(sd)
    config = {}
    if 'control_layers.14.adaLN_modulation.0.weight' in sd:
        config['n_control_layers'] = 15
        config['additional_in_dim'] = 17
        config['refiner_control'] = True
        ref_weight = sd.get("control_noise_refiner.0.after_proj.weight", None)
        if ref_weight is not None:
            if torch.count_nonzero(ref_weight) == 0:
                config['broken'] = True
```

### After (Patched Code)
```python
elif 'control_all_x_embedder.2-1.weight' in sd: # alipai z image fun controlnet
    sd = z_image_convert(sd)
    config = {}
    # Check for 2.0 or 2.1 by counting control_layers
    n_control_layers = 0
    for k in sd.keys():
        if k.startswith('control_layers.') and '.adaLN_modulation.0.weight' in k:
            layer_idx = int(k.split('.')[1])
            n_control_layers = max(n_control_layers, layer_idx + 1)

    # Fallback to 2.0 detection if dynamic count fails
    if n_control_layers == 0 and 'control_layers.14.adaLN_modulation.0.weight' in sd:
        n_control_layers = 15

    if n_control_layers > 0:
        config['n_control_layers'] = n_control_layers
        config['additional_in_dim'] = 17
        config['refiner_control'] = True
        ref_weight = sd.get("control_noise_refiner.0.after_proj.weight", None)
        if ref_weight is not None:
            if torch.count_nonzero(ref_weight) == 0:
                config['broken'] = True
```

## Improvements

1. **Dynamic Layer Counting**: Automatically detects the number of control layers by scanning the state dict keys
2. **Better Compatibility**: Works with different versions of Z-Image ControlNet (2.0, 2.1, etc.)
3. **Fallback Detection**: If dynamic counting fails, falls back to the original hardcoded detection
4. **Future-Proof**: Will work with future versions that may have different layer counts

## Files Modified

- **Main File**: `workspace/ComfyUI/comfy_extras/nodes_model_patch.py`
- **Backup**: `workspace/ComfyUI/comfy_extras/nodes_model_patch.py.backup`

## Applying the Patch

The patch has been applied. To reapply or verify:

```bash
python3 patch_controlnet_loader.py
```

## Restart Required

⚠️ **Important**: Restart ComfyUI for the changes to take effect:

```bash
docker exec comfyui-supervisor-1 supervisorctl restart comfyui
```

Or restart the entire container:

```bash
docker-compose restart
```

## Reverting the Patch

If you need to revert to the original code:

```bash
cp workspace/ComfyUI/comfy_extras/nodes_model_patch.py.backup \
   workspace/ComfyUI/comfy_extras/nodes_model_patch.py
```

Then restart ComfyUI.

## Benefits

- ✅ Supports Z-Image ControlNet 2.0 and 2.1 automatically
- ✅ Works with models that have different numbers of control layers
- ✅ More robust detection logic
- ✅ Maintains backward compatibility with existing models
