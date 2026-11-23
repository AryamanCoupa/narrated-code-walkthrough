'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const rendererSource = fs.readFileSync(path.join(__dirname, '../assets/walkthrough.js'), 'utf8');

// Run the complete renderer with a small DOM adapter that records its markup.
// Real browser checks cover interaction, layout, and playback separately.
function renderer() {
  const flow = {id: 'flow', type: 'flow', items: [
    {id: 'first', title: 'First', text: 'Read <input>', file: 'example.txt', line: 1, end_line: 2},
    {id: 'last', title: 'Last', text: 'Return the result.'},
  ]};
  const data = {
    id: 'fixture', title: 'Example', audience: 'Developer', minutes: 1, revision: '12345678',
    files: [{path: 'example.txt', purpose: 'Fictional source',
      source: '-- SQL comment\n- YAML item\n+ unary expression',
      diff: '--- a/example.txt\n+++ b/example.txt\n@@ -1 +1 @@\n-old\n+new'}],
    chapters: [{id: 'example', title: 'Example', summary: 'A fictional flow', minutes: 1,
      blocks: [flow, {id: 'snippet', type: 'code', file: 'example.txt', line: 1, end_line: 3}],
      narration: []}],
  };
  const elements = new Map();
  function element(selector) {
    if (!elements.has(selector)) elements.set(selector, {
      innerHTML: '', textContent: '', style: {}, dataset: {}, value: '',
      classList: {toggle() {}}, pause() {}, removeAttribute() {},
      querySelector: child => child.startsWith('[data-line=') ? null : element(selector + ' ' + child),
      querySelectorAll: () => [],
    });
    return elements.get(selector);
  }
  const context = vm.createContext({
    document: {getElementById: () => ({textContent: JSON.stringify(data)}),
      querySelector: element, addEventListener() {}, body: element('body')},
    localStorage: {getItem: () => null}, location: {hash: ''}, history: {replaceState() {}},
    URLSearchParams,
  });
  vm.runInContext(rendererSource, context);
  return {context, element, flow};
}

test('chapter snippets keep SQL, YAML and unary prefixes as normal source', () => {
  const {element} = renderer();
  const html = element('#main').innerHTML;
  assert.ok(html.includes('-- SQL comment'));
  assert.ok(html.includes('- YAML item'));
  assert.ok(html.includes('+ unary expression'));
  assert.doesNotMatch(html, /class="line[^"\n]*\b(?:added|removed)\b/);
  assert.match(html, /class="line selected"/);
});

test('explorer colors only explicit PR diffs and clears colors in full source', () => {
  const {context, element} = renderer();
  context.sourceFile('example.txt');
  assert.doesNotMatch(element('#source').innerHTML, /\b(?:added|removed)\b/);
  context.sourceFile('example.txt', 1, 1, true);
  const diff = element('#source').innerHTML;
  assert.equal((diff.match(/class="line added"/g) || []).length, 1);
  assert.equal((diff.match(/class="line removed"/g) || []).length, 1);
  assert.doesNotMatch(diff, /\bselected\b/);
  context.sourceFile('example.txt');
  assert.doesNotMatch(element('#source').innerHTML, /\b(?:added|removed)\b/);
});

test('the first flow node exposes its source range before any click', () => {
  const {element} = renderer();
  const html = element('#main').innerHTML;
  assert.match(html, /data-node="first" aria-pressed="true"/);
  assert.ok(html.includes('Read &lt;input&gt;'));
  assert.ok(html.includes('data-open-file="example.txt" data-line="1" data-end-line="2">Inspect related source'));
});

test('selecting flow nodes updates the same detail markup without stale links', () => {
  const {context, element, flow} = renderer();
  const detail = element('[data-block="flow"] [data-flow-detail]');
  context.selectNode('flow', 'first');
  assert.ok(detail.innerHTML.includes('Read &lt;input&gt;'));
  assert.ok(detail.innerHTML.includes('data-open-file="example.txt" data-line="1" data-end-line="2">Inspect related source'));
  context.selectNode('flow', 'last');
  assert.equal(detail.innerHTML, '<p>Return the result.</p>');
  assert.doesNotMatch(context.renderBlock({...flow, items: [flow.items[1]]}), /Inspect related source/);
});
