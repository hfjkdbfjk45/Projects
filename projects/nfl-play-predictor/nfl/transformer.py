"""Causal PyTorch sequence classifier; no outcome fields enter model inputs."""
import torch
from torch import nn

class PlayTransformer(nn.Module):
    def __init__(self, n_features=8, width=32, heads=4, layers=2, max_length=8):
        super().__init__()
        self.max_length=max_length
        self.projection=nn.Linear(n_features,width)
        self.position=nn.Embedding(max_length,width)
        layer=nn.TransformerEncoderLayer(width,heads,dim_feedforward=width*2,dropout=.1,batch_first=True)
        self.encoder=nn.TransformerEncoder(layer,layers,enable_nested_tensor=False)
        self.classifier=nn.Linear(width,1)

    def forward(self,x,lengths):
        if x.ndim!=3 or x.shape[1]>self.max_length or torch.any(lengths<1):
            raise ValueError("Invalid sequence shape")
        positions=torch.arange(x.shape[1],device=x.device)
        padding=positions[None,:]>=lengths[:,None]
        causal=torch.triu(torch.ones(x.shape[1],x.shape[1],device=x.device,dtype=torch.bool),diagonal=1)
        hidden=self.projection(x)+self.position(positions)[None,:,:]
        hidden=self.encoder(hidden,mask=causal,src_key_padding_mask=padding)
        final=hidden[torch.arange(x.shape[0],device=x.device),lengths-1]
        return self.classifier(final).squeeze(-1)


class TransformerPredictor:
    def __init__(self,checkpoint,metadata):
        self.model=PlayTransformer(**metadata["architecture"])
        self.model.load_state_dict(torch.load(checkpoint,map_location="cpu",weights_only=True))
        self.model.eval()
        self.metadata=metadata

    def predict(self,contexts):
        from .core import features
        if not isinstance(contexts,list) or not contexts:
            raise ValueError("contexts must be a nonempty chronological list of pre-snap situations")
        seq=[features(c)[1:] for c in contexts[-self.model.max_length:]]
        x=torch.tensor([seq],dtype=torch.float32)
        with torch.inference_mode():
            p=torch.sigmoid(self.model(x,torch.tensor([len(seq)]))).item()
        return dict(prediction="pass" if p>=.5 else "run",pass_probability=p,run_probability=1-p,
                    model="causal transformer",data_source=self.metadata["data_source"],context_length=len(seq))
