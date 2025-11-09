# /neural-ops/app.py
from fastapi import FastAPI, Request, HTTPException
import torch
from helical_operator import HelicalOperator, build_simple_ring_neighbors

app = FastAPI()

model = HelicalOperator(d_model=1536, n_layers=4, nhead=8)
model.eval()

def to_3d(x):
    """
    Accepts list/ndarray shaped:
      - (d)            -> (1, 1, d)
      - (L, d)         -> (1, L, d)
      - (B, L, d)      -> (B, L, d)
    Returns a float32 torch tensor (B, L, d).
    """
    t = torch.tensor(x, dtype=torch.float32)
    if t.ndim == 1:        # (d)
        t = t.unsqueeze(0).unsqueeze(0)     # (1,1,d)
    elif t.ndim == 2:      # (L,d)
        t = t.unsqueeze(0)                  # (1,L,d)
    elif t.ndim == 3:      # (B,L,d)
        pass
    else:
        raise ValueError(f"Expected 1/2/3 dims, got {t.ndim}")
    return t

@app.post("/process")
async def process_embeddings(request: Request):
    payload = await request.json()
    if "A_embeddings" not in payload or "B_embeddings" not in payload:
        raise HTTPException(400, "Provide A_embeddings and B_embeddings.")

    try:
        A = to_3d(payload["A_embeddings"])  # (B,L,d)
        B = to_3d(payload["B_embeddings"])  # (B,L,d)
    except Exception as e:
        raise HTTPException(400, f"Bad embeddings shape: {e}")

    # simple sanity checks
    if A.shape[0] != B.shape[0]:
        raise HTTPException(400, f"Batch mismatch: A{A.shape} vs B{B.shape}")
    if A.shape[2] != B.shape[2]:
        raise HTTPException(400, f"Dim mismatch: A d={A.shape[2]} vs B d={B.shape[2]}")

    Bsz, L, d = A.shape
    if L == 0:
        raise HTTPException(400, "Empty sequence (L=0).")

    # K must be <= L
    k = min(3, L)
    neighbor_indices = build_simple_ring_neighbors(L, k=k)  # (L,k)

    with torch.no_grad():
        A_out, B_out, fused = model(A, B, neighbor_indices, neighbor_indices, return_fused=True)

    return {
        "A_out": A_out.tolist(),
        "B_out": B_out.tolist(),
        "fused": fused.tolist() if fused is not None else []
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
