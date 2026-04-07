def detect_gpu() -> dict:
    """Detect CUDA GPU and VRAM. Returns tier info."""
    try:
        import torch
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            vram_mb = props.total_mem // (1024 * 1024)
            return {
                "gpu_available": True,
                "gpu_name": props.name,
                "vram_mb": vram_mb,
                "recommended_tier": 1 if vram_mb >= 8192 else 0
            }
    except ImportError:
        pass

    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        if "CUDAExecutionProvider" in providers:
            return {
                "gpu_available": True,
                "gpu_name": "CUDA (via ONNX Runtime)",
                "vram_mb": 0,
                "recommended_tier": 0
            }
    except ImportError:
        pass

    return {
        "gpu_available": False,
        "gpu_name": None,
        "vram_mb": 0,
        "recommended_tier": 0
    }
