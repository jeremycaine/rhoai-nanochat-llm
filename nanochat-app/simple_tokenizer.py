"""
Simple tokenizer wrapper using tiktoken directly
"""
import tiktoken
import pickle
import os

def load_tokenizer():
    """Load the tiktoken encoding from pickle"""
    # Try /app/tokenizer first (OpenShift friendly)
    possible_paths = [
        '/app/tokenizer/tokenizer.pkl',
        './tokenizer/tokenizer.pkl',
        os.path.expanduser('~/.cache/nanochat/tokenizer/tokenizer.pkl'),
        '/root/.cache/nanochat/tokenizer/tokenizer.pkl'
    ]
    
    tokenizer_pkl = None
    for path in possible_paths:
        if os.path.exists(path):
            tokenizer_pkl = path
            print(f"Found tokenizer at: {path}")
            break
    
    if not tokenizer_pkl:
        raise FileNotFoundError(f"Could not find tokenizer.pkl in any of: {possible_paths}")
    
    with open(tokenizer_pkl, 'rb') as f:
        enc = pickle.load(f)
    
    # Get the data we need
    mergeable_ranks = enc.mergeable_ranks
    pattern = enc.pat_str
    
    # Hardcode special tokens (since pickle is broken)
    special_tokens = {
        '<|bos|>': 65527,
        '<|user_start|>': 65528,
        '<|user_end|>': 65529,
        '<|assistant_start|>': 65530,
        '<|assistant_end|>': 65531,
        '<|python_start|>': 65532,
        '<|python_end|>': 65533,
        '<|output_start|>': 65534,
        '<|output_end|>': 65535
    }
    
    # Create fresh encoding
    new_enc = tiktoken.Encoding(
        name="nanochat",
        pat_str=pattern,
        mergeable_ranks=mergeable_ranks,
        special_tokens=special_tokens
    )
    
    return new_enc

class NanoChatTokenizer:
    def __init__(self):
        self.enc = load_tokenizer()
        self.bos_token_id = 65527
        print("✓ Tokenizer initialized")
    
    def encode(self, text, allowed_special="all"):
        return self.enc.encode(text, allowed_special=allowed_special)
    
    def decode(self, tokens):
        return self.enc.decode(tokens)

def get_tokenizer():
    return NanoChatTokenizer()
