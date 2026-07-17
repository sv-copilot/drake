/**
 * AutomationControlPanel
 * Renders per-project automation toggles and a global pause/resume button.
 */

class AutomationControlPanel {
  constructor(container) {
    this.container = container;
    this.isPausedGlobally = false;
  }

  async render() {
    this.container.innerHTML = ''; // reset
    const projects = await this.fetchProjects();

    // Render project list
    const list = document.createElement('ul');
    list.className = 'project-list';
    projects.forEach(project => {
      const item = document.createElement('li');
      item.className = 'project-item';

      const label = document.createElement('label');
      label.className = 'toggle-label';
      label.textContent = project.name;

      const toggle = document.createElement('input');
      toggle.type = 'checkbox';
      toggle.className = 'project-toggle';
      toggle.checked = project.automation_enabled;
      toggle.dataset.projectId = project.id;
      toggle.addEventListener('change', (e) => this.handleToggleChange(e, project.id));

      if (this.isPausedGlobally) {
        toggle.disabled = true;
        label.style.opacity = '0.5';
      }

      item.appendChild(toggle);
      item.appendChild(label);
      list.appendChild(item);
    });
    this.container.appendChild(list);

    // Global pause/resume button
    const pauseBtn = document.createElement('button');
    pauseBtn.id = 'global-pause-btn';
    pauseBtn.className = 'global-pause-btn';
    pauseBtn.textContent = this.isPausedGlobally ? '▶ RESUME ALL' : '⏸ PAUSE ALL';
    pauseBtn.addEventListener('click', () => this.handleGlobalPause());
    this.container.appendChild(pauseBtn);
  }

  async fetchProjects() {
    const response = await fetch('/api/projects/automation-status');
    if (!response.ok) throw new Error('Failed to fetch projects');
    return response.json();
  }

  async handleToggleChange(event, projectId) {
    const enabled = event.target.checked;
    try {
      await fetch(`/api/projects/${projectId}/automation`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });
    } catch (err) {
      console.error('Toggle update failed:', err);
      // Revert UI on error
      event.target.checked = !enabled;
    }
  }

  async handleGlobalPause() {
    const newPausedState = !this.isPausedGlobally;
    try {
      if (newPausedState) {
        await fetch('/api/automation/pause', { method: 'POST' });
      } else {
        await fetch('/api/automation/resume', { method: 'POST' });
      }
    } catch (err) {
      console.error('Global pause/resume failed:', err);
      return;
    }

    this.isPausedGlobally = newPausedState;

    // Disable/enable all toggles
    const toggles = this.container.querySelectorAll('.project-toggle');
    toggles.forEach(toggle => {
      toggle.disabled = this.isPausedGlobally;
      const label = toggle.nextElementSibling;
      if (label) {
        label.style.opacity = this.isPausedGlobally ? '0.5' : '1';
      }
    });

    // Update button text
    const pauseBtn = this.container.querySelector('#global-pause-btn');
    if (pauseBtn) {
      pauseBtn.textContent = this.isPausedGlobally ? '▶ RESUME ALL' : '⏸ PAUSE ALL';
    }
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { AutomationControlPanel };
}
