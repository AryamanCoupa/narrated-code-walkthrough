#!/usr/bin/env python3
"""Build an offline HTML code guide; never import or execute explained source."""
import argparse
import base64
from copy import deepcopy
import hashlib
import json
import math
import mimetypes
from pathlib import Path, PurePosixPath
import re
import subprocess

ASSETS = Path(__file__).resolve().parents[1] / 'assets'
ID = re.compile(r'[a-z][a-z0-9-]*\Z')

def require(condition, message):
    if not condition:
        raise ValueError(message)

def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), label + ' needs nonempty text')
    return value

def identifier(value, label):
    require(isinstance(value, str) and bool(ID.fullmatch(value)), label + ' is not a valid ID')

def relative(value):
    text(value, 'path')
    path = PurePosixPath(value)
    require(not path.is_absolute() and '..' not in path.parts and '\\' not in value, 'Use repository-relative paths: '+value)
    require('.git' not in path.parts and not path.name.startswith('.env') and path.suffix.lower() not in {'.pem','.key'}, 'Do not embed environment/private-key files: '+value)
    return path.as_posix()

def script_hash(guide):
    script = [{'id':c['id'], 'narration':c.get('narration',[])} for c in guide['chapters']]
    return hashlib.sha256(json.dumps(script,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def load_guide(path):
    guide = json.loads(Path(path).read_text(encoding='utf-8'))
    require(isinstance(guide,dict) and guide.get('version') == 1,'Expected guide version 1')
    for key in ('title','summary','audience'):text(guide.get(key),key)
    require(type(guide.get('minutes')) in (int,float) and math.isfinite(guide['minutes']) and guide['minutes']>0,'minutes must be positive')
    require(isinstance(guide.get('files'),list) and guide['files'],'Select source files explicitly')
    paths=set()
    for file in guide['files']:
        path=relative(file['path']);require(path not in paths,'Duplicate source '+path);paths.add(path)
        file['path']=path
        text(file.get('purpose'),'file purpose')
    require(isinstance(guide.get('chapters'),list) and guide['chapters'],'Add chapters')
    ids=set()
    for chapter in guide['chapters']:
        identifier(chapter.get('id'),'chapter.id');require(chapter['id'] not in ids,'Duplicate chapter ID');ids.add(chapter['id'])
        text(chapter.get('title'),'chapter title');text(chapter.get('summary'),'chapter summary')
        require(type(chapter.get('minutes')) in (int,float) and math.isfinite(chapter['minutes']) and chapter['minutes']>0,'chapter minutes must be positive')
        require(isinstance(chapter.get('blocks'),list) and chapter['blocks'],'Add chapter blocks')
        blocks={}
        for block in chapter['blocks']:
            identifier(block.get('id'),'block.id');require(block['id'] not in blocks,'Duplicate block ID');blocks[block['id']]=block
            require(block.get('type') in ('text','code','flow','cards'),'Unsupported block type')
            if block['type']=='text':text(block.get('text'),'block text')
            if block['type']=='code':require(block.get('file') in paths,'Code block references unlisted file');text(block.get('explanation'),'code explanation')
            if block['type'] in ('flow','cards'):
                require(isinstance(block.get('items'),list) and block['items'],'Add block items')
                node_ids=set()
                for item in block['items']:
                    text(item.get('title'),'item title');text(item.get('text'),'item text')
                    if block['type']=='flow':
                        identifier(item.get('id'),'flow item ID');require(item['id'] not in node_ids,'Duplicate flow item');node_ids.add(item['id'])
                    if item.get('file'):require(item['file'] in paths,'Flow item references unlisted file')
        require(isinstance(chapter.get('narration',[]),list),'narration must be a list')
        for cue in chapter.get('narration',[]):
            text(cue.get('text'),'spoken text');text(cue.get('label'),'cue label')
            require(bool(cue.get('target')) != bool(cue.get('file')),'A cue needs either target or file')
            if cue.get('file'):require(cue['file'] in paths,'Narration references unlisted file')
            else:
                require(cue['target'] in blocks,'Unknown narration block '+str(cue['target']))
                if cue.get('node'):require(any(n.get('id')==cue['node'] for n in blocks[cue['target']].get('items',[])),'Unknown flow node')
        if chapter.get('quiz'):
            quiz=chapter['quiz'];text(quiz.get('question'),'quiz question');text(quiz.get('explanation'),'quiz explanation')
            require(isinstance(quiz.get('choices'),list) and 2<=len(quiz['choices'])<=5,'Quiz needs 2–5 choices')
            for choice in quiz['choices']:text(choice,'quiz choice')
            require(type(quiz.get('answer')) is int and 0<=quiz['answer']<len(quiz['choices']),'Invalid quiz answer')
    require(abs(sum(c['minutes'] for c in guide['chapters'])-guide['minutes'])<.01,'Chapter minutes must total guide minutes')
    return guide

def git(repo,*args,optional=False):
    result=subprocess.run(['git',*args],cwd=repo,text=True,encoding='utf-8',capture_output=True)
    if result.returncode:
        if optional:return None
        raise ValueError(result.stderr.strip() or 'Git command failed')
    return result.stdout

def commit(repo,revision):
    return git(repo,'rev-parse','--verify','--end-of-options',revision+'^{commit}').strip()

def resolve_reference(value,files,default_lines=1):
    file=files[value['file']];lines=file['source'].splitlines()
    require(bool(value.get('anchor')) != bool(value.get('line')),'Use exactly one anchor or line in '+value['file'])
    if value.get('anchor'):
        text(value['anchor'],'anchor')
        matches=[i+1 for i,line in enumerate(lines) if value['anchor'] in line]
        require(len(matches)==1,'Anchor must match exactly once: '+value['file']+' / '+value['anchor'])
        start=matches[0]
    else:start=value['line']
    require(type(start) is int and 1<=start<=len(lines),'Source line is out of bounds')
    require(not ('lines' in value and 'end_line' in value),'Choose lines or end_line')
    count=value.get('lines',default_lines)
    require(type(count) is int and count>0,'lines must be a positive integer')
    end=value.get('end_line',min(len(lines),start+count-1))
    require(type(end) is int and start<=end<=len(lines),'Source range is out of bounds')
    if 'lines' in value:require(start+count-1<=len(lines),'Requested lines exceed source file')
    value['line'],value['end_line']=start,end

def build_data(guide,repo,revision='HEAD',base=None,worktree=False,audio=None):
    data=deepcopy(guide);repo=Path(repo).resolve()
    head=commit(repo,revision);base_sha=commit(repo,base) if base else None
    files={}
    for item in data['files']:
        path=relative(item['path']);deleted=False
        if worktree:
            source_path=(repo/path).resolve()
            require(source_path.is_relative_to(repo),'Source symlink leaves repository')
            # A link with an ordinary name must not expose an excluded in-repository target.
            relative(source_path.relative_to(repo).as_posix())
            source=source_path.read_text(encoding='utf-8')
        else:
            source=git(repo,'show',head+':'+path,optional=True)
            if source is None and base_sha:
                source=git(repo,'show',base_sha+':'+path,optional=True);deleted=True
            require(source is not None,'Missing committed source: '+path)
        require('\0' not in source,'Binary source is not supported: '+path)
        files[path]={**item,'path':path,'source':source,'deleted':deleted,'group':item.get('group','Source'),
                     'diff':git(repo,'diff','--no-ext-diff','--unified=4',base_sha,head,'--',path) if base_sha and not worktree else ''}
    for chapter in data['chapters']:
        for block in chapter['blocks']:
            if block['type']=='code':resolve_reference(block,files,12)
            for item in block.get('items',[]):
                if item.get('file'):resolve_reference(item,files,1)
        for cue in chapter.get('narration',[]):
            if cue.get('file'):resolve_reference(cue,files,1)
    if audio:
        manifest_path=Path(audio).resolve();manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        require(manifest.get('script_hash')==script_hash(guide),'Narration does not match this guide; regenerate audio')
        for chapter in data['chapters']:
            segments=chapter.get('narration',[])
            require(bool(segments),'Every narrated chapter needs segments')
            record=manifest.get('chapters',{}).get(chapter['id']);require(isinstance(record,dict),'Missing chapter audio')
            seconds=record.get('seconds');require(type(seconds) in (int,float) and math.isfinite(seconds) and seconds>0,'Invalid audio duration')
            cues=record.get('cues');require(isinstance(cues,list) and len(cues)==len(segments),'Every segment needs a timing cue')
            previous=0
            for i,(cue,segment) in enumerate(zip(cues,segments)):
                require(cue.get('segment')==i,'Cues must be in segment order')
                start,end=cue.get('start'),cue.get('end')
                require(all(type(x) in (int,float) and math.isfinite(x) for x in (start,end)),'Invalid timing values')
                require(0<=previous<=start<end<=seconds+.1,'Overlapping or out-of-range audio cue')
                previous=end;segment.update(start=start,end=end)
            asset=(manifest_path.parent/record['file']).resolve()
            require(asset.is_relative_to(manifest_path.parent),'Audio file leaves manifest directory')
            mime=mimetypes.guess_type(asset)[0]
            require(mime and mime.startswith('audio/'),'Audio asset must have a supported audio extension')
            chapter['audio']='data:'+mime+';base64,'+base64.b64encode(asset.read_bytes()).decode('ascii')
            chapter['seconds']=seconds
        data['voice']=manifest.get('voice','Local narration')
    data['files']=list(files.values());data['revision']=('working tree at ' if worktree else '')+head
    data['base']=base_sha;data['id']=hashlib.sha256((head+json.dumps(guide,sort_keys=True)).encode()).hexdigest()[:16]
    return data

def render_html(data):
    content=(ASSETS/'walkthrough.html').read_text(encoding='utf-8')
    payload=json.dumps(data,ensure_ascii=False).replace('<','\\u003c')
    values={'__STYLE__':(ASSETS/'styles.css').read_text(encoding='utf-8'),'__DATA__':payload,'__SCRIPT__':(ASSETS/'walkthrough.js').read_text(encoding='utf-8')}
    for key in values:require(content.count(key)==1,'Invalid renderer template marker '+key)
    return re.sub(r'__(?:STYLE|DATA|SCRIPT)__',lambda match:values[match.group(0)],content)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--guide',required=True,type=Path);parser.add_argument('--repo',required=True,type=Path)
    parser.add_argument('--revision',default='HEAD');parser.add_argument('--base');parser.add_argument('--worktree',action='store_true')
    parser.add_argument('--audio',type=Path);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--overwrite',action='store_true')
    args=parser.parse_args()
    try:
        require(not args.output.exists() or args.overwrite,'Output exists; use --overwrite to rebuild')
        guide=load_guide(args.guide);data=build_data(guide,args.repo,args.revision,args.base,args.worktree,args.audio)
        html=render_html(data);args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(html,encoding='utf-8')
        print(json.dumps({'output':str(args.output.resolve()),'files':len(data['files']),'chapters':len(data['chapters']),
                          'reading_minutes':data['minutes'],'narrated':bool(args.audio),'script_hash':script_hash(guide)}))
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.exit(1,str(exc)+'\n')

if __name__=='__main__':main()
