"""Real temporary Git/source/audio checks; no network or application execution."""
from copy import deepcopy
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
import wave

import build_walkthrough as build

class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='code-guide-test-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.repo=self.root/'repo';self.repo.mkdir()
        example=Path(__file__).resolve().parents[1]/'assets/example'
        shutil.copy2(example/'source/app.py',self.repo/'app.py')
        self.guide=json.loads((example/'guide.json').read_text())
        self.git('init','-q');self.git('config','user.name','Guide test');self.git('config','user.email','guide@example.invalid');self.commit()

    def git(self,*args):return subprocess.check_output(['git',*args],cwd=self.repo,text=True,stderr=subprocess.PIPE)
    def commit(self):
        self.git('add','.');self.git('-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false','commit','-qm','Fixture')
        return self.git('rev-parse','HEAD').strip()
    def load(self):
        path=self.root/'guide.json';path.write_text(json.dumps(self.guide));return build.load_guide(path)

    def test_committed_snapshot_and_explicit_worktree(self):
        (self.repo/'app.py').write_text((self.repo/'app.py').read_text()+'# Local-only edit\n')
        before=self.git('status','--porcelain')
        data=build.build_data(self.load(),self.repo)
        self.assertNotIn('Local-only',data['files'][0]['source'])
        local=build.build_data(self.load(),self.repo,worktree=True)
        self.assertIn('Local-only',local['files'][0]['source'])
        self.assertTrue(local['revision'].startswith('working tree'))
        self.assertEqual(before,self.git('status','--porcelain'))

    def test_anchors_ranges_targets_and_paths_are_checked(self):
        guide=self.load();guide['chapters'][1]['blocks'][0]['anchor']='return'
        with self.assertRaisesRegex(ValueError,'exactly once'):build.build_data(guide,self.repo)
        guide=self.load();guide['chapters'][1]['blocks'][0]['lines']=1000
        with self.assertRaisesRegex(ValueError,'exceed'):build.build_data(guide,self.repo)
        self.guide['chapters'][0]['narration'][0]['target']='missing'
        with self.assertRaisesRegex(ValueError,'Unknown narration block'):self.load()
        with self.assertRaises(ValueError):build.relative('../private.py')
        with self.assertRaises(ValueError):build.relative('.env')

    def test_removed_source_uses_explicit_base(self):
        base=self.git('rev-parse','HEAD').strip();self.git('rm','app.py');self.commit()
        data=build.build_data(self.load(),self.repo,base=base)
        self.assertTrue(data['files'][0]['deleted']);self.assertIn('def normalize',data['files'][0]['source'])

    def test_source_text_cannot_end_data_script_or_replace_renderer(self):
        source=(self.repo/'app.py').read_text()+'# </script><img src=x onerror=alert(1)> __SCRIPT__\n'
        (self.repo/'app.py').write_text(source);self.commit()
        data=build.build_data(self.load(),self.repo);html=build.render_html(data)
        payload=re.search(r'<script type="application/json" id="data">(.*?)</script>',html,re.S).group(1)
        self.assertEqual(json.loads(payload)['files'][0]['source'],source)
        self.assertNotIn('</script><img',html);self.assertEqual(html.count('const DATA=JSON.parse'),1)

    def test_loaded_file_paths_are_canonical_and_alias_duplicates_fail(self):
        for spelling in ('app.py','./app.py','.//./app.py'):
            with self.subTest(path=spelling):
                self.guide['files'][0]['path']=spelling
                self.assertEqual(self.load()['files'][0]['path'],'app.py')
        duplicate=deepcopy(self.guide['files'][0]);duplicate['path']='app.py'
        self.guide['files'].append(duplicate)
        with self.assertRaisesRegex(ValueError,'Duplicate source'):self.load()

    def test_exported_file_paths_match_snippet_flow_and_narration_references(self):
        # Exercise build_data directly too, without relying on load_guide mutation.
        for spelling in ('./app.py','.//./app.py'):
            self.guide['files'][0]['path']=spelling
            for worktree in (False,True):
                with self.subTest(path=spelling,worktree=worktree):
                    data=build.build_data(self.guide,self.repo,worktree=worktree)
                    paths={file['path'] for file in data['files']}
                    self.assertEqual(paths,{'app.py'})
                    for chapter in data['chapters']:
                        references=[*chapter['blocks'],*chapter.get('narration',[])]
                        references.extend(item for block in chapter['blocks'] for item in block.get('items',[]))
                        for reference in references:
                            if reference.get('file'):self.assertIn(reference['file'],paths)
                    self.assertEqual(self.guide['files'][0]['path'],spelling)

    def test_audio_is_embedded_and_stale_or_overlapping_cues_fail(self):
        guide=self.load();audio=self.root/'tone.wav'
        with wave.open(str(audio),'wb') as output:
            output.setparams((1,2,8000,0,'NONE','not compressed'));output.writeframes(b'\0\0'*8000)
        manifest={'script_hash':build.script_hash(guide),'voice':'Test fixture','chapters':{}}
        for chapter in guide['chapters']:
            manifest['chapters'][chapter['id']]={'file':'tone.wav','seconds':1,'cues':[
                {'segment':i,'start':i*.1,'end':i*.1+.09} for i in range(len(chapter['narration']))]}
        path=self.root/'narration.json';path.write_text(json.dumps(manifest))
        data=build.build_data(guide,self.repo,audio=path)
        self.assertTrue(data['chapters'][0]['audio'].startswith('data:audio/'))
        self.assertEqual(data['chapters'][1]['narration'][1]['line'],3)
        wrong=deepcopy(manifest);wrong['script_hash']='wrong';path.write_text(json.dumps(wrong))
        with self.assertRaisesRegex(ValueError,'does not match'):build.build_data(guide,self.repo,audio=path)
        wrong=deepcopy(manifest);wrong['chapters']['code']['cues'][1]['start']=0;path.write_text(json.dumps(wrong))
        with self.assertRaisesRegex(ValueError,'Overlapping'):build.build_data(guide,self.repo,audio=path)

if __name__=='__main__':unittest.main(verbosity=2)
