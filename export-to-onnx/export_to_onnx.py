"""
Export nanochat model to ONNX format
"""
import torch
import torch.onnx
from pathlib import Path
from nanochat.checkpoint_manager import load_model

def export_nanochat_to_onnx(output_dir="./nanochat-onnx"):
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    print("Loading nanochat model...")
    device = torch.device("cpu")  # Export on CPU
    model, tokenizer, meta = load_model("sft", device, phase="eval", model_tag="d20", step=700)
    
    model.eval()
    
    model_config = meta.get('model_config', {})
    print(f"Model config: {model_config}")
    
    # Create dummy input
    batch_size = 1
    seq_length = 128  # Use smaller seq for export, model supports up to 2048
    dummy_input = torch.randint(0, model_config['vocab_size'], (batch_size, seq_length), dtype=torch.long)
    
    print(f"Dummy input shape: {dummy_input.shape}")
    
    # Test forward pass
    print("Testing forward pass...")
    with torch.no_grad():
        output = model(dummy_input)
        print(f"Output shape: {output.shape}")
    
    # Export to ONNX
    onnx_path = output_path / "model.onnx"
    print(f"\nExporting to ONNX: {onnx_path}")
    
    torch.onnx.export(
        model,
        dummy_input,
        str(onnx_path),
        input_names=['input_ids'],
        output_names=['logits'],
        dynamic_axes={
            'input_ids': {0: 'batch_size', 1: 'sequence_length'},
            'logits': {0: 'batch_size', 1: 'sequence_length'}
        },
        opset_version=14,
        do_constant_folding=True,
        verbose=False
    )
    
    print(f"✓ ONNX model exported!")
    
    # Save model config and tokenizer info
    import json
    config_path = output_path / "config.json"
    with open(config_path, 'w') as f:
        json.dump({
            'model_config': model_config,
            'architecture': 'nanochat-gpt',
            'onnx_opset': 14
        }, f, indent=2)
    
    print(f"✓ Config saved to {config_path}")
    
    # Copy tokenizer
    import shutil
    tokenizer_src = Path.home() / ".cache/nanochat/tokenizer"
    if tokenizer_src.exists():
        shutil.copy(tokenizer_src / "tokenizer.pkl", output_path / "tokenizer.pkl")
        shutil.copy(tokenizer_src / "token_bytes.pt", output_path / "token_bytes.pt")
        print(f"✓ Tokenizer files copied")
    
    # Check file size
    size_mb = onnx_path.stat().st_size / (1024*1024)
    print(f"\nONNX model size: {size_mb:.1f} MB")
    
    print(f"\n✓ Export complete!")
    print(f"Next: Convert to OpenVINO with:")
    print(f"  mo --input_model {onnx_path} --output_dir ./nanochat-openvino")
    
    return output_path

if __name__ == "__main__":
    export_nanochat_to_onnx()
