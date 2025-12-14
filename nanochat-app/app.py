from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import httpx
import numpy as np
import sys
import os

# Add current directory to path for nanochat import
sys.path.insert(0, '/app')

from simple_tokenizer import get_tokenizer

INFERENCE_URL = os.getenv("INFERENCE_URL", "https://nanochat-model-jeremycaine-dev.apps.rm2.thpm.p1.openshiftapps.com/v2/models/nanochat-model/infer")
tokenizer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tokenizer
    print("Loading tokenizer using nanochat code...")
    tokenizer = get_tokenizer()
    print("✓ Tokenizer loaded successfully")
    # Test it
    test = tokenizer.encode("Hello", allowed_special="all")
    print(f"✓ Tokenizer test: {test[:5]}")
    yield
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    max_tokens: int = 100
    temperature: float = 0.8
    top_k: int = 50

class ChatResponse(BaseModel):
    message: dict

def sample_token(logits, temperature, top_k):
    """Sample next token from logits"""
    logits = np.array(logits) / temperature
    
    if top_k > 0:
        indices = logits < np.partition(logits, -top_k)[-top_k]
        logits[indices] = -float('Inf')
    
    probs = np.exp(logits - np.max(logits))
    probs /= np.sum(probs)
    return np.random.choice(len(probs), p=probs)

@app.post("/chat/completions", response_model=ChatResponse)
async def chat_completions(request: ChatRequest):
    if tokenizer is None:
        raise HTTPException(status_code=503, detail="Tokenizer not loaded")
    
    try:
        # Build prompt
        prompt = ""
        for msg in request.messages:
            if msg.role == "user":
                prompt += f"<|user_start|>{msg.content}<|user_end|>"
            elif msg.role == "assistant":
                prompt += f"<|assistant_start|>{msg.content}<|assistant_end|>"
        prompt += "<|assistant_start|>"
        
        print(f"Prompt: {prompt}")
        
        # Tokenize
        input_ids = tokenizer.encode(prompt, allowed_special="all")
        generated = input_ids.copy()
        
        print(f"Input tokens: {len(input_ids)}")
        
        # Generate
        async with httpx.AsyncClient(timeout=60) as client:
            for i in range(request.max_tokens):
                inference_request = {
                    "inputs": [{
                        "name": "input_ids",
                        "shape": [1, len(generated)],
                        "datatype": "INT64",
                        "data": generated
                    }]
                }
                
                resp = await client.post(INFERENCE_URL, json=inference_request)
                resp.raise_for_status()
                
                result = resp.json()
                logits = result["outputs"][0]["data"][-65536:]
                
                next_tok = sample_token(logits, request.temperature, request.top_k)
                generated.append(int(next_tok))
                
                # Stop at assistant_end token
                if next_tok == 65531:
                    print(f"Stopped after {i+1} tokens")
                    break
        
        # Decode
        text = tokenizer.decode(generated)
        print(f"Generated: {text[:200]}")
        
        # Extract response
        response = text.split("<|assistant_start|>")[-1].replace("<|assistant_end|>", "").strip()
        
        return ChatResponse(message={"role": "assistant", "content": response})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok", "tokenizer_loaded": tokenizer is not None}

@app.get("/")
async def root():
    return {"message": "NanoChat API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
