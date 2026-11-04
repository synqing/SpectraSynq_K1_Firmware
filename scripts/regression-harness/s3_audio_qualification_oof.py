#!/usr/bin/env python3
"""Reproduce frozen E2 OOF predictions, then score fixed E1 intersection.
No parameter search, no replacement model, no final-model predictions as OOF.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score
import tempo_lock_score as e2
import tempo_lock_verdict as verdict
import tempo_lane_scorer as scorer

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model",type=Path,required=True);p.add_argument("--out",type=Path,required=True)
    p.add_argument("--e1",type=Path,action="append",required=True);p.add_argument("--features",type=Path,nargs="+",required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    original_hash=scorer.sha256_file(a.model);model=json.loads(a.model.read_text())
    paths=a.features
    assert len(paths)==len(model["inputs"])
    assert all(scorer.sha256_file(p)==x["sha256"] for p,x in zip(paths,model["inputs"]))
    D,names,golds,metas=e2.load_sets(paths);X,y,ok,clip=D["X"],D["y"].astype(int),D["ok"],D["clip"]
    rng=np.random.default_rng(20261022);uclips=np.unique(clip)
    folds=dict(zip(uclips,rng.permutation(len(uclips))%model["folds"]))
    cv=np.zeros(len(y));fold_models=[]
    for f in range(model["folds"]):
        te=np.array([folds[c]==f for c in clip]);tr=~te & ok
        fitted=e2.fit(X[tr],y[tr],model["l2"]);fold_models.append(fitted)
        cv[te]=e2.predict(fitted,X[te]);print(f"reproduced fold {f+1}/{model['folds']}",flush=True)
    # Reproduce the recorded all-training coefficients only as an identity check.
    # They are never used for the cross-validated scores below.
    fitted=e2.fit(X[ok],y[ok],model["l2"])
    for key in ("mu","sd","w","b"):
        np.testing.assert_allclose(fitted[key],model["model"][key],rtol=1e-12,atol=1e-12)
    auc=float(roc_auc_score(y[ok],cv[ok]));right,wrong=e2.track_counts(cv,D,golds,model["theta"])
    assert (right,wrong)==(model["cv_pick"]["right"],model["cv_pick"]["wrong"])
    assert abs(auc-model["cv_emit_auc"])<1e-12
    # This recorded model selected the first legal grid value; no new grid search.
    assert model["theta"]==0.5 and verdict.wilson_upper(wrong,right+wrong)<=verdict.WRONG_MAX
    np.savez_compressed(a.out/"oof.npz",score=cv,gen=D["gen"],clip=clip,names=np.array(names),fold=np.array([folds[c] for c in clip]))
    (a.out/"fold-models.json").write_text(json.dumps(fold_models))
    e1={}
    for path in a.e1:
        for cid,c in json.loads(path.read_text())["clips"].items():
            assert cid not in e1;e1[cid]=c
    mask=np.zeros(len(y),dtype=bool);per={}
    for k,cid in enumerate(names):
        ix=clip==k;c=e1[cid]
        assert c["gen"]==D["gen"][ix].tolist() and c["bpm"]==D["bpm"][ix].tolist()
        mask[ix]=np.array(c["lock"],dtype=bool)
    combined=mask & ok & (cv>=model["theta"])
    cr,cw=e2.track_counts(combined.astype(float),D,golds,0.5)
    for k,cid in enumerate(names):
        ix=clip==k;per[cid]=scorer.score_clip({"gen":D["gen"][ix].tolist(),"bpm":D["bpm"][ix].tolist(),"lock":combined[ix].astype(int).tolist()},float(golds[k]))
    assert scorer.sha256_file(a.model)==original_hash
    doc={"scope":"available 551 of registered 552 training clips; V2 sealed", "model_sha256":original_hash,
         "reproduction":{"coefficients_match":True,"cv_emit_auc":auc,"right":right,"wrong":wrong,"theta":model["theta"]},
         "intersection":{"right":cr,"wrong":cw,"n":len(names),"wilson_upper":verdict.wilson_upper(cw,cr+cw),"coverage":cr/len(names)},
         "e1_inputs":[{"path":str(p),"sha256":scorer.sha256_file(p)} for p in a.e1],"per_clip":per}
    r=doc["intersection"];doc["observed_entry_met"]=r["wilson_upper"]<=verdict.WRONG_MAX and r["coverage"]>=verdict.COVER_MIN
    (a.out/"result.json").write_text(json.dumps(doc,indent=2));print(json.dumps({k:v for k,v in doc.items() if k!="per_clip"}))
    return int(not doc["observed_entry_met"])
if __name__=="__main__":raise SystemExit(main())
