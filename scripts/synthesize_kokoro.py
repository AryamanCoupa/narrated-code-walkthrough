#!/usr/bin/env python3
"""Create local narration with measured per-segment timings; no model downloads."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from build_walkthrough import load_guide, require, script_hash

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--guide',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--model',type=Path,required=True);parser.add_argument('--voices',type=Path,required=True)
    parser.add_argument('--voice',required=True);parser.add_argument('--format',choices=['mp3','wav'],default='mp3')
    parser.add_argument('--ffmpeg',default='ffmpeg');parser.add_argument('--threads',type=int,default=4)
    args=parser.parse_args()
    try:
        guide=load_guide(args.guide)
        require(args.model.is_file() and args.voices.is_file(),'Supply existing local model and voice files')
        require(1<=args.threads<=32,'threads must be between 1 and 32')
        require(any(c.get('narration') for c in guide['chapters']),'At least one chapter needs narration segments')
        encoder=shutil.which(args.ffmpeg) if args.format=='mp3' else None
        require(args.format=='wav' or encoder,'Install ffmpeg or use --format wav')
        import numpy as np
        import onnxruntime as rt
        import soundfile as sf
        from kokoro_onnx import Kokoro
        rt.disable_telemetry_events()
        options=rt.SessionOptions();options.intra_op_num_threads=args.threads;options.inter_op_num_threads=1
        session=rt.InferenceSession(str(args.model),sess_options=options,providers=['CPUExecutionProvider'])
        model=Kokoro.from_session(session,str(args.voices))
        require(args.voice in model.get_voices(),'Unknown voice. Available: '+', '.join(model.get_voices()))
        out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True);manifest_path=out/'narration.json'
        old=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        records=old.get('chapters',{})
        model_meta=[str(args.model.resolve()),args.model.stat().st_size,args.model.stat().st_mtime_ns,
                    str(args.voices.resolve()),args.voices.stat().st_size,args.voices.stat().st_mtime_ns]
        result={'version':1,'script_hash':script_hash(guide),'voice':args.voice,'engine':'Local Kokoro','chapters':{}}
        for chapter in (c for c in guide['chapters'] if c.get('narration')):
            segments=chapter['narration'];digest=hashlib.sha256(json.dumps([args.voice,args.format,model_meta,segments],sort_keys=True).encode()).hexdigest()
            existing=records.get(chapter['id'],{})
            if existing.get('cache_hash')==digest and (out/existing['file']).is_file():
                result['chapters'][chapter['id']]=existing;print(chapter['id'],'cached',flush=True);continue
            print('Generating',chapter['id'],len(segments),'segments',flush=True)
            waves=[];cues=[];offset=0;rate=24000
            for i,segment in enumerate(segments):
                samples,sr=model.create(segment['text'],voice=args.voice,speed=1.0,lang='en-us')
                require(sr==rate and len(samples)>0 and np.isfinite(samples).all(),'Invalid synthesized audio')
                cues.append({'segment':i,'start':offset/rate,'end':(offset+len(samples))/rate})
                waves.append(samples);offset+=len(samples)
                if i<len(segments)-1:
                    silence=np.zeros(round(rate*.3),dtype=np.float32);waves.append(silence);offset+=len(silence)
            wave=np.concatenate(waves);require(float(np.sqrt(np.mean(wave*wave)))>.001,'Audio is silent')
            wav=out/(chapter['id']+'.wav');sf.write(wav,wave,rate);asset=wav
            if encoder:
                asset=out/(chapter['id']+'.mp3')
                subprocess.run([encoder,'-y','-hide_banner','-loglevel','error','-i',str(wav),'-codec:a','libmp3lame','-b:a','64k',str(asset)],check=True)
            result['chapters'][chapter['id']]={'file':asset.name,'seconds':offset/rate,'cues':cues,'cache_hash':digest}
            manifest_path.write_text(json.dumps(result,indent=2),encoding='utf-8')
            print(chapter['id'],round(offset/rate,1),'seconds',flush=True)
        manifest_path.write_text(json.dumps(result,indent=2),encoding='utf-8')
        print('Narration manifest:',manifest_path)
    except (ValueError,OSError,ImportError,subprocess.CalledProcessError) as exc:parser.exit(1,str(exc)+'\n')

if __name__=='__main__':main()
