from __future__ import annotations
from pathlib import Path
import argparse,json,torch,numpy as np
from crossbar_linear import CrossbarMLPLinear
from train_e2e_crossbar import make_targets,plant_mats

def feat(e0,e1,e2,x0,x1,x2,u,c):
    return torch.stack([e0/24,e1/24,e2/24,x0/24-1,x1/24-1,x2/24-1,u/24-1,2*c-1],dim=-1).clamp(-2,2)

def pretrain(m,steps=300,batch=4096):
    opt=torch.optim.AdamW(m.parameters(),lr=3e-3)
    for i in range(steps):
        x=torch.rand(batch)*48;e=torch.rand(batch)*40-20;e1=e+torch.randn(batch)*.3;e2=e1+torch.randn(batch)*.3;x1=(x+torch.randn(batch)*.3).clamp(0,48);x2=(x1+torch.randn(batch)*.3).clamp(0,48);u=(x+torch.randn(batch)*3).clamp(0,48);c=torch.rand(batch)*.6+.4
        z=feat(e,e1,e2,x,x1,x2,u,c);y=(x+e).clamp(0,48)/24-1;p=m(z).squeeze(1);loss=((p-y)**2).mean();opt.zero_grad();loss.backward();opt.step()
    return float(loss.detach())

def train(Ts,out,iters=42,B=40,T=160,seed=77,hidden=(32,16)):
    torch.manual_seed(seed);m=CrossbarMLPLinear(8,hidden);pre=pretrain(m);Ad,Bd=plant_mats(Ts);opt=torch.optim.AdamW(m.parameters(),lr=4e-4,weight_decay=2e-6);sch=torch.optim.lr_scheduler.CosineAnnealingLR(opt,T_max=iters);hist=[]
    for it in range(iters):
        target,conf,typ=make_targets(B,T,Ts,'cpu');x=(target[:,0]+torch.randn(B)*7).clamp(0,48);v=torch.randn(B)*80;u=x.clone();e1=torch.zeros_like(x);e2=torch.zeros_like(x);x1=x.clone();x2=x.clone();track=du=0.
        for k in range(T):
            c=conf[:,k];noise=torch.randn(B)*(.10/c.clamp(min=.15));e=target[:,k]-x+noise;meas=(x+e).clamp(0,48);e=meas-x;z=feat(e,e1,e2,x,x1,x2,u,c);un=(24*(m(z).squeeze(1)+1)).clamp(0,48);err=x-target[:,k];wk=.5+.5*k/(T-1);track+=wk*(err*err).mean();du+=((un-u)**2).mean();ns=torch.stack([x,v],1)@Ad.T+un[:,None]*Bd[None];x2=x1;x1=x;e2=e1;e1=e;u=un;x=ns[:,0].clamp(0,48);v=ns[:,1]
        terminal=((x-target[:,-1])**2).mean();track/=T;du/=T;loss=track+.25*terminal+8e-5*du;opt.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(m.parameters(),2);opt.step();sch.step()
        if it%7==0 or it==iters-1:rec={'iter':it,'loss':float(loss.detach()),'track_mse':float(track.detach()),'terminal_mse':float(terminal.detach())};hist.append(rec);print(rec,flush=True)
    out.parent.mkdir(exist_ok=True);torch.save({'state_dict':m.state_dict(),'in_dim':8,'hidden':hidden,'sample_period_s':Ts,'kind':'raw taps e/x + u + confidence; no velocity input','history':hist},out);out.with_suffix('.json').write_text(json.dumps(hist,indent=2));return out
if __name__=='__main__':train(2e-4,Path('linear_models/rawtap_e2e_200us.pt'))
