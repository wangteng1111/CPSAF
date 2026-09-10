from __future__ import annotations
from pathlib import Path
import csv, torch, numpy as np
from crossbar_linear import CrossbarMLPLinear
from evaluate_mlp_fast import plant_discrete,rmse,settle,overshoot,revs
from cpsaf_ath_teacher import target_signal,confidence_signal,PlantConfig

TS=2e-4

def load_model(path,kind):
    ck=torch.load(path,map_location='cpu',weights_only=False);m=CrossbarMLPLinear(ck['in_dim'],tuple(ck['hidden']));m.load_state_dict(ck['state_dict']);m.eval();layers=[]
    for mod in m.net:
        if isinstance(mod,torch.nn.Linear):layers.append((mod.weight.detach().numpy().astype(float),mod.bias.detach().numpy().astype(float)))
    def forward(z):
        a=np.asarray(z,float)
        for j,(W,b) in enumerate(layers):
            a=W@a+b
            if j<len(layers)-1:a=np.tanh(a)
        return float(np.clip(24*(a[0]+1),0,48))
    if kind=='state7':
        def pol(eh,xh,x,v,u,c):
            z=[eh[-1]/24,eh[-2]/24,eh[-3]/24,x/24-1,v/10000,u/24-1,2*c-1];return forward(z)
    else:
        def pol(eh,xh,x,v,u,c):
            z=[eh[-1]/24,eh[-2]/24,eh[-3]/24,x/24-1,xh[-2]/24-1,xh[-3]/24-1,u/24-1,2*c-1];return forward(z)
    return pol

def simulate(controller,kind='static',freq=10,noise=.15,dur=.4,step=.05,seed=0,confkind='nominal'):
    t=np.arange(int(dur/TS)+1)*TS;target=target_signal(t,kind,freq,step);conf=confidence_signal(t,confkind);Ad,Bd=plant_discrete(TS,PlantConfig());st=np.array([float(target[0]),0.]);u=st[0];rng=np.random.default_rng(seed);eh=[0.,0.,0.];xh=[st[0],st[0],st[0]];xs=[];us=[]
    for i in range(len(t)):
        x,v=st;c=float(conf[i]);e=target[i]-x+rng.normal(0,noise/max(c,.15));meas=np.clip(x+e,0,48);e=float(meas-x);eh.append(e);eh=eh[-3:];xh.append(x);xh=xh[-3:]
        if controller=='ideal_position':u=float(meas)
        else:u=controller(eh,xh,x,v,u,c)
        xs.append(x);us.append(u);st=Ad@st+Bd*u
    return {'t':t,'target':target,'x':np.array(xs),'u':np.array(us)}

def main():
    root=Path(__file__).resolve().parent
    ctrls={'ideal_position':'ideal_position','crossbar_state7':load_model(root/'linear_models/e2e_200us_ft.pt','state7'),'crossbar_rawtap8':load_model(root/'linear_models/rawtap_e2e_200us.pt','rawtap8')}
    rows=[]
    for name,ctl in ctrls.items():
        for f in [10,20]:
            rr=[simulate(ctl,'sine',f,.15,.4,seed=s) for s in range(8)];rows.append(dict(controller=name,test=f'track_{f}Hz',value=float(np.mean([rmse(r,.08) for r in rr]))))
        rr=[simulate(ctl,'static',10,.15,.4,seed=s) for s in range(8)];rows += [dict(controller=name,test='static_rmse',value=float(np.mean([rmse(r,.08) for r in rr]))),dict(controller=name,test='static_x_jitter',value=float(np.mean([np.std(r['x'][r['t']>=.08]-24) for r in rr]))),dict(controller=name,test='static_u_jitter',value=float(np.mean([np.std(r['u'][r['t']>=.08]) for r in rr]))),dict(controller=name,test='static_reversals',value=float(np.mean([revs(r,.08) for r in rr])))]
        ss=[];ov=[]
        for q in np.linspace(0,TS,10,endpoint=False):
            st=.05+q;r=simulate(ctl,'step',10,0,.13,st,0);ss.append(settle(r,st));ov.append(overshoot(r,st))
        rows += [dict(controller=name,test='step_settle_ms',value=float(np.nanmean(ss))),dict(controller=name,test='step_overshoot',value=float(np.mean(ov)))]
        rr=[simulate(ctl,'mixed',10,.15,.62,seed=s,confkind='dropout') for s in range(8)];rows.append(dict(controller=name,test='mixed_dropout_rmse',value=float(np.mean([rmse(r,.08) for r in rr]))))
    out=root/'results_mlp'/'crossbar_meta_5khz.csv';out.parent.mkdir(exist_ok=True)
    with out.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=['controller','test','value']);w.writeheader();w.writerows(rows)
    for r in rows:print(r)
if __name__=='__main__':main()
