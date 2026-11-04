#!/usr/bin/env python3
"""Actual shipping integer GDFT versus independent complex DFT on shared PCM bytes.

The error bound follows recurrence rounding: each multiplication adds <1 input
unit, hence <=2 normalised amplitude units; final magnitude rounding contributes
<=2*sqrt(max_input/(N*abs(sin(omega))))+2/N. No tracker, audio-input or optical claim.
"""
import argparse,array,hashlib,importlib.util,json,math,subprocess
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]

def definition(source,name):
    start=source.index('void '+name+'(');brace=source.index('{',start);depth=0
    for i in range(brace,len(source)):
        depth+=(source[i]=='{')-(source[i]=='}')
        if depth==0:return source[start:i+1]
    raise ValueError('unterminated definition '+name)

def independent_reference(z,N,c):
    # +/-2 recurrences have exact coefficient products: no rounding-error
    # amplification. Use exact integer DC/alternating sums, never sin(0/pi).
    if abs(c)==32768:
        signs=np.ones(N,dtype=np.int64) if c>0 else np.where(np.arange(N)%2,-1,1)
        ref=abs(int(np.dot(z.astype(np.int64),signs)))*2/N
        return ref,2/N+2e-6*ref
    omega=math.acos(c/32768.0);S=float(np.max(np.abs(z)))
    ref=float(abs(np.dot(z,np.exp(-1j*omega*np.arange(N))))*2/N)
    return ref,2+2*math.sqrt(S/(N*abs(math.sin(omega))))+2/N+2e-6*ref

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    spec=importlib.util.spec_from_file_location('gdft_oracle',ROOT/'scripts/regression-harness/golden/oracle_gdft.py');o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o)
    o.DEFINES += ['K1_GDFT_INT64_MAGNITUDE_V1=1','K1_GDFT_INT64_RECURRENCE_V1=1','K1_GDFT_LANE4_V1=1','K1_GDFT_X2_CROSSOVER_BIN=40u']
    # Compile the actual boot-time initialiser as well as the transform. The
    # golden driver retains an older copied initialiser for its frozen baseline;
    # it is not authority for this current-source qualification.
    init_source=(o.FIRMWARE/'system/system.h').read_text()
    current_init=definition(init_source,'precompute_goertzel_constants').replace('void precompute_goertzel_constants(', 'static void host_precompute_goertzel_constants(',1)
    copied=definition(o.DRIVER,'host_precompute_goertzel_constants')
    o.DRIVER=o.DRIVER.replace('static '+copied,current_init,1)
    o.DRIVER=o.DRIVER[:o.DRIVER.index('int main()')]+r'''
int main() {
 CONFIG.SAMPLE_RATE=12800; CONFIG.NOTE_OFFSET=12; CONFIG.MOOD=0.5f;
 host_precompute_goertzel_constants();host_init_spectral_tilt_lut();noise_complete=true;
 printf("META %u\n",unsigned(SAMPLE_HISTORY_LENGTH));
 for(int i=0;i<NUM_FREQS;++i)printf("BIN %d %u %d\n",i,unsigned(frequencies[i].block_size),int(frequencies[i].coeff_q14));
 while(std::fread(sample_window,sizeof(int16_t),SAMPLE_HISTORY_LENGTH,stdin)==SAMPLE_HISTORY_LENGTH){
  process_GDFT();printf("MAG");for(int i=0;i<NUM_FREQS;++i)printf(" %.9g",double(magnitudes_normalized[i]));printf("\n");
 }
}
'''
    binary=o._compile(a.output);meta=subprocess.check_output([str(binary)],input=b'').decode();H=int(meta.splitlines()[0].split()[1]);bins=[list(map(int,l.split()[1:]))for l in meta.splitlines() if l.startswith('BIN')]
    t=np.arange(H,dtype=np.float64)/12800;cases=[('zero',np.zeros(H,dtype='<i2')),('dc',np.full(H,4096,dtype='<i2')),('nyquist',np.where(np.arange(H)%2,-32768,32767).astype('<i2'))]
    impulse=np.zeros(H,dtype='<i2');impulse[H//2]=16000;cases.append(('impulse',impulse))
    for f in (110,220,440,880,1760,3520):
        for amp in (256,4096,16000):cases.append((f'tone-{f}-{amp}',(amp*np.sin(2*np.pi*f*t)).astype('<i2')))
    chord=sum(np.sin(2*np.pi*f*t)for f in (220,277.182631,329.627557));cases.append(('chord',(5000*chord).astype('<i2')))
    pcm=b''.join(x.tobytes()for _,x in cases);(a.output/'inputs.s16le').write_bytes(pcm)
    with (a.output/'inputs.s16le').open('rb')as f,(a.output/'actual.txt').open('wb')as g:subprocess.run([str(binary)],stdin=f,stdout=g,check=True,timeout=30)
    raw=(a.output/'actual.txt').read_text();actual=[list(map(float,l.split()[1:]))for l in raw.splitlines()if l.startswith('MAG')];assert len(actual)==len(cases)
    records=[]
    for (name,x),mag in zip(cases,actual):
        errors=[]
        for i,N,c in bins:
            if i>=71:
                assert mag[i]==0,(name,i,mag[i]);continue
            z=(x[-1:-N-1:-1].astype(np.int64)>>6).astype(np.float64)
            ref,bound=independent_reference(z,N,c)
            err=abs(mag[i]-ref);assert math.isfinite(mag[i])and err<=bound,(name,i,mag[i],ref,bound)
            errors.append({'bin':i,'actual':mag[i],'reference':ref,'error':err,'bound':bound})
        records.append({'case':name,'max_error':max(e['error']for e in errors),'checks':errors})
    # Negative control: replacing a strong actual tone with zero must break this
    # same independent bound. No production code or fixture is changed.
    strong=[e for r in records for e in r['checks']if e['reference']>e['bound']*4]
    assert strong and all(abs(0-e['reference'])>e['bound']for e in strong)
    nyquist=[e for r in records for e in r['checks']if e['bin']==70]
    assert nyquist and all(e['bound']<0.1 for e in nyquist)
    assert all(abs((e['actual']+1)-e['reference'])>e['bound']for e in nyquist)
    centres=[{'bin':i,'window_samples':N,'coefficient_q14':c,'centre_hz':math.acos(c/32768.)*12800/(2*math.pi),'label_hz':55*2**((12+i)/12)} for i,N,c in bins if i<71]
    for b in centres:b['label_error_cents']=1200*math.log2(b['centre_hz']/b['label_hz'])
    out={'negative_nyquist_plus_one_rejected':True,'schema':'k1-s3-spectral/1','source_sha256':hashlib.sha256((o.FIRMWARE/'audio/k1_gdft_core.cpp').read_bytes()).hexdigest(),'initialiser_sha256':hashlib.sha256(definition(init_source,'precompute_goertzel_constants').encode()).hexdigest(),'defines':o.DEFINES,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'cases':records,'bin_centres':centres,'bins_compared':71,'above_nyquist_zero_bins':9,'negative_zeroed_strong_tone_rejected':True,'scope':'Actual boot initialiser and GDFT at12.8kHz; shared inputbytes, independent complex DFT, bounded integerrounding. Current rounded-k centres are approximate note labels; TRUE_CENTER remains excluded by the existing Captain decision. Input capture, AGC, general chords and musical beat correctness are separate.'}
    (a.output/'result.json').write_text(json.dumps(out,indent=2)+'\n');print(f'{len(records)} cases x71 safe bins;9 above-Nyquist bins zero; independent DFT bounds and negative control passed')
if __name__=='__main__':main()
