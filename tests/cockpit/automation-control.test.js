/**
 * Tests for AutomationControlPanel UI.
 * Run with: npx mocha tests/cockpit/automation-control.test.js
 * Expected failure before implementation: module not found.
 */

const { JSDOM } = require('jsdom');
const assert = require('assert');
const { AutomationControlPanel } = require('../../cockpit/js/automation-control.js');

describe('AutomationControlPanel', function () {
  let dom;
  let document;
  let panel;
  let fetchCalled;
  let originalFetch;

  const mockProjects = [
    { id: 'proj-1', name: 'Alpha', automation_enabled: true },
    { id: 'proj-2', name: 'Beta', automation_enabled: false },
  ];

  beforeEach(() => {
    dom = new JSDOM(`<!DOCTYPE html>
      <html>
      <head><meta charset="utf-8"></head>
      <body>
        <div id="control-panel"></div>
      </body>
      </html>
    `);
    document = dom.window.document;
    global.document = document; // make DOM API available to the module
    global.window = dom.window;

    fetchCalled = {
      url: null,
      method: null,
      body: null,
    };

    // Stub fetch
    global.fetch = async (url, options = {}) => {
      fetchCalled.url = url;
      fetchCalled.method = options.method || 'GET';
      fetchCalled.body = options.body;
      if (url === '/api/projects/automation-status') {
        return {
          ok: true,
          json: async () => mockProjects,
        };
      }
      if (url.startsWith('/api/projects/') && url.endsWith('/automation')) {
        return { ok: true, json: async () => ({}) };
      }
      if (url === '/api/automation/pause') {
        return { ok: true, json: async () => ({}) };
      }
      return { ok: false };
    };

    const container = document.getElementById('control-panel');
    panel = new AutomationControlPanel(container);
  });

  afterEach(() => {
    global.document = originalFetch;
  });

  describe('render()', () => {
    it('should fetch projects and render toggle switches', async () => {
      await panel.render();

      const switches = document.querySelectorAll('.project-toggle');
      assert.strictEqual(switches.length, mockProjects.length, 'should render one toggle per project');

      const firstToggle = document.querySelector('.project-toggle[data-project-id="proj-1"]');
      assert(firstToggle, 'toggle for Proj-1 should exist');
      assert.strictEqual(firstToggle.checked, true, 'Proj-1 automation_enabled should be reflected');

      const secondToggle = document.querySelector('.project-toggle[data-project-id="proj-2"]');
      assert(secondToggle, 'toggle for Proj-2 should exist');
      assert.strictEqual(secondToggle.checked, false, 'Proj-2 automation_enabled should be reflected');
    });

    it('should render a global pause button', async () => {
      await panel.render();

      const pauseBtn = document.querySelector('#global-pause-btn');
      assert(pauseBtn, 'global pause button should exist');
    });
  });

  describe('toggleProject()', () => {
    it('should call API to enable automation for a project', async () => {
      await panel.render();

      const toggle = document.querySelector('.project-toggle[data-project-id="proj-2"]');
      // Simulate user click: toggle from false to true
      toggle.checked = true;
      const event = new dom.window.Event('change', { bubbles: true });
      toggle.dispatchEvent(event);

      // Allow event handler time to execute (it's async but we need to wait)
      await new Promise(resolve => setTimeout(resolve, 10));

      assert.strictEqual(fetchCalled.url, '/api/projects/proj-2/automation');
      assert.strictEqual(fetchCalled.method, 'PUT');
      const body = JSON.parse(fetchCalled.body);
      assert.strictEqual(body.enabled, true);
    });

    it('should call API to disable automation', async () => {
      await panel.render();

      const toggle = document.querySelector('.project-toggle[data-project-id="proj-1"]');
      toggle.checked = false;
      const event = new dom.window.Event('change', { bubbles: true });
      toggle.dispatchEvent(event);

      await new Promise(resolve => setTimeout(resolve, 10));

      assert.strictEqual(fetchCalled.url, '/api/projects/proj-1/automation');
      assert.strictEqual(fetchCalled.method, 'PUT');
      assert.strictEqual(JSON.parse(fetchCalled.body).enabled, false);
    });
  });

  describe('pauseAll()', () => {
    it('should call global pause API', async () => {
      await panel.render();

      const pauseBtn = document.querySelector('#global-pause-btn');
      const event = new dom.window.Event('click', { bubbles: true });
      pauseBtn.dispatchEvent(event);

      await new Promise(resolve => setTimeout(resolve, 10));

      assert.strictEqual(fetchCalled.url, '/api/automation/pause');
      assert.strictEqual(fetchCalled.method, 'POST');
    });

    it('should disable all project toggles after pausing', async () => {
      await panel.render();

      const pauseBtn = document.querySelector('#global-pause-btn');
      pauseBtn.dispatchEvent(new dom.window.Event('click', { bubbles: true }));
      await new Promise(resolve => setTimeout(resolve, 10));

      const toggles = document.querySelectorAll('.project-toggle');
      toggles.forEach(toggle => {
        assert.strictEqual(toggle.disabled, true, 'Toggle should be disabled after global pause');
      });
      assert.strictEqual(pauseBtn.textContent.includes('RESUME'), true, 'Button should change to Resume');
    });

    it('should resume all on second click', async () => {
      await panel.render();

      const pauseBtn = document.querySelector('#global-pause-btn');
      pauseBtn.dispatchEvent(new dom.window.Event('click', { bubbles: true }));
      await new Promise(resolve => setTimeout(resolve, 10));

      // Second click to resume
      pauseBtn.dispatchEvent(new dom.window.Event('click', { bubbles: true }));
      await new Promise(resolve => setTimeout(resolve, 10));

      const toggles = document.querySelectorAll('.project-toggle');
      toggles.forEach(toggle => {
        assert.strictEqual(toggle.disabled, false, 'Toggle should be reenabled after resume');
      });
      assert.strictEqual(pauseBtn.textContent.includes('PAUSE ALL'), true);
    });
  });
});
