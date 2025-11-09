import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple

# ---------------------------
# Utility: neighbor gather
# ---------------------------
def gather_neighbors(x: torch.Tensor, neighbor_indices: torch.Tensor) -> torch.Tensor:
    """
    Gather neighbor vectors for each sequence position.
    - x: (B, L, d)
    - neighbor_indices: either (L, K) or (B, L, K) of int indices
    returns: (B, L, K, d)
    """
    B, L, d = x.shape
    if neighbor_indices.dim() == 2:
        idx = neighbor_indices.unsqueeze(0).expand(B, -1, -1)  # (B, L, K)
    else:
        idx = neighbor_indices  # assume (B,L,K)
    # expand x to (B, L, L, d) and gather along dim=2
    x_exp = x.unsqueeze(1).expand(-1, L, -1, -1)  # (B,L,L,d)
    idx_exp = idx.unsqueeze(-1).expand(-1, -1, -1, d)  # (B,L,K,d)
    nbrs = torch.gather(x_exp, 2, idx_exp)  # (B, L, K, d)
    return nbrs

# ---------------------------
# Strand Transformer block
# ---------------------------
class StrandEncoderLayer(nn.Module):
    """Transformer-ish encoder layer for one strand (self-attention + FFN)."""
    def __init__(self, d_model: int, nhead: int = 4, dim_feedforward: int = 1024, dropout: float = 0.1):
        super().__init__()
        self.self_attn = nn.MultiheadAttention(d_model, nhead, dropout=dropout, batch_first=True)
        self.norm1 = nn.LayerNorm(d_model)
        self.ff = nn.Sequential(
            nn.Linear(d_model, dim_feedforward),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(dim_feedforward, d_model),
            nn.Dropout(dropout),
        )
        self.norm2 = nn.LayerNorm(d_model)

    def forward(self, x: torch.Tensor, attn_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        attn_out, _ = self.self_attn(x, x, x, attn_mask=attn_mask)
        x = self.norm1(x + attn_out)
        x2 = self.ff(x)
        x = self.norm2(x + x2)
        return x

# ---------------------------
# Cross-pairing layer
# ---------------------------
class CrossPairingLayer(nn.Module):
    """
    Cross-attention between two strands plus local neighbor message passing.
    Ensures nodes are connected to local neighbors (degree >= K) and cross-pairing.
    """
    def __init__(self, d_model: int, nhead: int = 4, neighbor_k: int = 3):
        super().__init__()
        self.cross_attn_A = nn.MultiheadAttention(d_model, nhead, batch_first=True)
        self.cross_attn_B = nn.MultiheadAttention(d_model, nhead, batch_first=True)
        self.normA = nn.LayerNorm(d_model)
        self.normB = nn.LayerNorm(d_model)
        self.msg_lin = nn.Linear(d_model, d_model)
        self.neighbor_k = neighbor_k

    def forward(self,
                A: torch.Tensor,
                B: torch.Tensor,
                neighbor_indices_A: torch.Tensor,
                neighbor_indices_B: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        A, B: (B, L, d)
        neighbor_indices_*: (L,K) or (B,L,K)
        """
        # cross attention: A queries B, B queries A
        attnA, _ = self.cross_attn_A(A, B, B)  # (B,L,d)
        attnB, _ = self.cross_attn_B(B, A, A)

        # local neighbor aggregation
        nbrsA = gather_neighbors(A, neighbor_indices_A).mean(dim=2)  # (B,L,d)
        nbrsB = gather_neighbors(B, neighbor_indices_B).mean(dim=2)

        aggA = self.msg_lin(nbrsA)
        aggB = self.msg_lin(nbrsB)

        A_out = self.normA(A + attnA + aggA)
        B_out = self.normB(B + attnB + aggB)
        return A_out, B_out

# ---------------------------
# Convergence / fusion layer
# ---------------------------
class ConvergenceLayer(nn.Module):
    """Collects global summaries and optionally broadcasts fused signal back to strands."""
    def __init__(self, d_model: int, bottleneck: int = 256, inject: bool = True):
        super().__init__()
        self.inject = inject
        self.read_mlp = nn.Sequential(
            nn.Linear(d_model, bottleneck),
            nn.GELU(),
            nn.Linear(bottleneck, d_model),
        )
        self.fuse = nn.Sequential(
            nn.LayerNorm(2 * d_model),
            nn.Linear(2 * d_model, d_model),
            nn.GELU(),
            nn.Linear(d_model, d_model),
        )
        self.broadcast = nn.Linear(d_model, d_model)

    def forward(self, A: torch.Tensor, B: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        readA = A.mean(dim=1)
        readB = B.mean(dim=1)
        readA = self.read_mlp(readA)
        readB = self.read_mlp(readB)
        fused = self.fuse(torch.cat([readA, readB], dim=-1))  # (B, d)
        if self.inject:
            Bsz, L, d = A.shape
            bc = self.broadcast(fused).unsqueeze(1).expand(-1, L, -1)
            A = A + bc
            B = B + bc
        return A, B, fused

# ---------------------------
# Helical Operator (main)
# ---------------------------
class HelicalOperator(nn.Module):
    """
    Helical neural operator implementing:
     - per-strand encoding (Transformer-like)
     - cross-pairing / twist (cross-attention with rolled offsets)
     - local neighbor message passing (gather_neighbors)
     - periodic convergence/fusion layers
    """
    def __init__(self,
                 d_model: int = 256,
                 n_layers: int = 6,
                 nhead: int = 4,
                 neighbor_k: int = 3,
                 conv_every: int = 3,
                 inject_on_conv: bool = True):
        super().__init__()
        self.d_model = d_model
        self.n_layers = n_layers
        self.conv_every = conv_every
        self.strand_layers = nn.ModuleList([StrandEncoderLayer(d_model, nhead) for _ in range(n_layers)])
        self.cross_layers = nn.ModuleList([CrossPairingLayer(d_model, nhead, neighbor_k) for _ in range(n_layers)])
        n_convs = (n_layers // conv_every) + (1 if (n_layers % conv_every) != 0 else 0)
        self.convergences = nn.ModuleList([ConvergenceLayer(d_model, inject=inject_on_conv) for _ in range(n_convs)])
        self.final_norm = nn.LayerNorm(d_model)

    def forward(self,
                A: torch.Tensor,
                B: torch.Tensor,
                neighbor_indices_A: torch.Tensor,
                neighbor_indices_B: torch.Tensor,
                return_fused: bool = True) -> Tuple[torch.Tensor, torch.Tensor, Optional[torch.Tensor]]:
        """
        Inputs:
          - A, B: (B, L, d_model) strand embeddings (batch_size, seq_len, d)
          - neighbor_indices_*: (L, K) or (B, L, K)
        Returns:
          - A_out, B_out: (B, L, d)
          - fused_tokens: (B, num_convs, d) if return_fused True else None
        Notes:
          - You can precompute neighbor_indices from domain graph (temporal, semantic, causal).
          - For the 'twist' mapping we roll B by a layer-dependent offset before cross-attn.
        """
        Bsz, L, d = A.shape
        fused_list = []
        conv_i = 0
        for li in range(self.n_layers):
            # 1) per-strand encode
            A = self.strand_layers[li](A)
            B = self.strand_layers[li](B)

            # 2) twist offset: rotate B to simulate helical pairing
            twist = (li * 2) % L
            if twist != 0:
                B_shifted = B.roll(shifts=twist, dims=1)
            else:
                B_shifted = B

            # 3) cross-pairing + local messages (neighbor indices same shape)
            A, B_shift_out = self.cross_layers[li](A, B_shifted, neighbor_indices_A, neighbor_indices_B)

            # 4) unshift B back
            if twist != 0:
                B = B_shift_out.roll(shifts=-twist, dims=1)
            else:
                B = B_shift_out

            # 5) optional convergence
            if (li + 1) % self.conv_every == 0:
                A, B, fused = self.convergences[conv_i](A, B)
                fused_list.append(fused)
                conv_i += 1

        A = self.final_norm(A)
        B = self.final_norm(B)
        fused_out = torch.stack(fused_list, dim=1) if (len(fused_list) > 0 and return_fused) else None
        return A, B, fused_out

# ---------------------------
# Heads: per-node and pooled
# ---------------------------
class PerNodeRelevanceHead(nn.Module):
    """
    Produces per-node weights in [0,1] and an aggregated item score.
    - input: A_out, B_out, optionally fused tokens
    - output: per_node_weights (B, L), item_score (B,)
    """
    def __init__(self, d_model: int, hidden: int = 256, smoothness_lambda: float = 0.01):
        super().__init__()
        self.node_mlp = nn.Sequential(
            nn.LayerNorm(d_model * 2),
            nn.Linear(d_model * 2, hidden),
            nn.GELU(),
            nn.Linear(hidden, 1)
        )
        self.agg_mlp = nn.Sequential(
            nn.LayerNorm(d_model * 2),
            nn.Linear(d_model * 2, hidden),
            nn.GELU(),
            nn.Linear(hidden, 1)
        )
        self.smoothness_lambda = smoothness_lambda

    def forward(self, A: torch.Tensor, B: torch.Tensor, fused: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        A,B: (B,L,d)
        fused: (B, num_convs, d) or None
        returns:
          - per_node_weights: (B, L) in [0,1]
          - item_score: (B,)
        """
        Bsz, L, d = A.shape
        # node-level features: concat A_i and B_i
        AB = torch.cat([A, B], dim=-1)  # (B,L,2d)
        node_logits = self.node_mlp(AB).squeeze(-1)  # (B,L)
        per_node = torch.sigmoid(node_logits)  # [0,1] per node

        # aggregated score: pool features weighted by per_node
        weighted = (per_node.unsqueeze(-1) * AB).mean(dim=1)  # (B, 2d)
        if fused is not None:
            fused_mean = fused.mean(dim=1)  # (B, d)
            # append fused_mean (project to 2d if shapes mismatch)
            fused_proj = fused_mean.repeat(1, 1) if fused_mean.shape[-1] == weighted.shape[-1] else fused_mean
            agg_input = torch.cat([weighted, fused_mean], dim=-1)
        else:
            agg_input = weighted
        item_logit = self.agg_mlp(agg_input).squeeze(-1)
        item_score = torch.sigmoid(item_logit)  # (B,)
        return per_node, item_score

class HelixRelevanceHead(nn.Module):
    """Simple pooled score head (no per-node outputs)."""
    def __init__(self, d_model: int, hidden: int = 256):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.LayerNorm(d_model * 2),
            nn.Linear(d_model * 2, hidden),
            nn.GELU(),
            nn.Linear(hidden, 1)
        )

    def forward(self, A: torch.Tensor, B: torch.Tensor, fused: Optional[torch.Tensor] = None) -> torch.Tensor:
        pa = A.mean(dim=1)
        pb = B.mean(dim=1)
        if fused is not None:
            fused_mean = fused.mean(dim=1)
            z = torch.cat([pa, pb + fused_mean], dim=-1)
        else:
            z = torch.cat([pa, pb], dim=-1)
        score = torch.sigmoid(self.mlp(z).squeeze(-1))
        return score

# ---------------------------
# Dynamic gating optional module
# ---------------------------
class DynamicGating(nn.Module):
    """
    Small gating MLP that produces a scalar gate in [0,1] per item (or per-node if expanded).
    Inputs: pooled feature (B,d), metadata (B, m) e.g., detector score, author reputation, etc.
    """
    def __init__(self, feat_dim: int, meta_dim: int = 4, hidden: int = 128, clamp: Tuple[float,float] = (0.01, 0.99)):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(feat_dim + meta_dim, hidden),
            nn.ReLU(),
            nn.LayerNorm(hidden),
            nn.Linear(hidden, hidden//2),
            nn.ReLU(),
            nn.Linear(hidden//2, 1)
        )
        self.clamp = clamp

    def forward(self, pooled_feat: torch.Tensor, meta: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        pooled_feat: (B, d)
        meta: (B, meta_dim) or None
        returns gate: (B,) in [clamp_min, clamp_max]
        """
        if meta is None:
            meta = pooled_feat.new_zeros((pooled_feat.size(0), 0))
        inp = torch.cat([pooled_feat, meta], dim=-1)
        logit = self.net(inp).squeeze(-1)
        gate = torch.sigmoid(logit)
        gate = gate.clamp(self.clamp[0], self.clamp[1])
        return gate

# ---------------------------
# Example quick helpers
# ---------------------------
def build_simple_ring_neighbors(L: int, k: int = 3, wrap: bool = True) -> torch.Tensor:
    """
    Build simple neighbor indices guaranteeing degree >= k: left, right, then skips.
    Returns (L, k) tensor of indices.
    """
    nbrs = []
    for i in range(L):
        arr = []
        left = (i - 1) % L if wrap else max(0, i-1)
        right = (i + 1) % L if wrap else min(L-1, i+1)
        arr.extend([left, right])
        add_offset = 2
        while len(arr) < k:
            arr.append((i + add_offset) % L if wrap else min(L-1, i + add_offset))
            add_offset += 1
        nbrs.append(arr[:k])
    return torch.tensor(nbrs, dtype=torch.long)
