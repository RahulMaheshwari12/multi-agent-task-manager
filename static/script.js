// ── API Base URL ──────────────────────────────────────
const API = '';

// ── XSS Protection ───────────────────────────────────
function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;')
              .replace(/'/g, '&#039;');
}

// ── Debounce for Search ──────────────────────────────
let searchTimeout;
function debouncedSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => searchTasks(), 300);
}

// ── Section Navigation ────────────────────────────────
function showSection(name, e) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.getElementById(`section-${name}`).classList.add('active');
    e.target.closest('.nav-item').classList.add('active');
    
    const titles = { tasks: 'All Tasks', overdue: 'Overdue Tasks', chat: 'AI Chat' };
    document.getElementById('page-title').textContent = titles[name];
    
    if (name === 'tasks') loadTasks();
    if (name === 'overdue') loadOverdue();
}

// ── Load Tasks ────────────────────────────────────────
async function loadTasks(status = '') {
    const container = document.getElementById('tasks-container');
    container.innerHTML = '<div class="loading">Loading tasks...</div>';
    
    try {
        const res = await fetch(`${API}/tasks?status=${status}`);
        const data = await res.json();
        renderTasks(data.tasks, 'tasks-container');
    } catch (err) {
        container.innerHTML = '<div class="loading">Failed to load tasks.</div>';
    }
}

// ── Load Overdue ──────────────────────────────────────
async function loadOverdue() {
    const container = document.getElementById('overdue-container');
    container.innerHTML = '<div class="loading">Loading overdue tasks...</div>';
    
    try {
        const res = await fetch(`${API}/tasks/overdue`);
        const data = await res.json();
        renderTasks(data.tasks, 'overdue-container');
    } catch (err) {
        container.innerHTML = '<div class="loading">Failed to load overdue tasks.</div>';
    }
}

// ── Render Tasks ──────────────────────────────────────
function renderTasks(tasks, containerId) {
    const container = document.getElementById(containerId);
    
    if (!tasks || tasks.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div style="font-size:2rem">📭</div>
                <p>No tasks found</p>
            </div>`;
        return;
    }
    
    container.innerHTML = tasks.map(task => `
        <div class="task-card" id="task-${task.id}">
            <div class="task-card-header">
                <div class="task-title">${escapeHTML(task.title)}</div>
                <span class="priority-badge priority-${task.priority}">${escapeHTML(task.priority)}</span>
            </div>
            <div class="task-meta">
                <span>👤 ${escapeHTML(task.assigned_to) || 'Unassigned'}</span>
                <span>📅 ${escapeHTML(task.due_date) || 'No due date'}</span>
            </div>
            <span class="status-badge status-${task.status}">${escapeHTML(task.status)}</span>
            ${task.description ? `<div class="task-meta">${escapeHTML(task.description)}</div>` : ''}
            <div class="task-actions">
                ${task.status !== 'completed' ? 
                    `<button class="btn-success" onclick="completeTask(${task.id})">✓ Complete</button>` : ''}
                <button class="btn-danger" onclick="deleteTask(${task.id})">🗑 Delete</button>
            </div>
        </div>
    `).join('');
}

// ── Filter Tasks ──────────────────────────────────────
function filterTasks(status, btn) {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    loadTasks(status);
}

// ── Search Tasks ──────────────────────────────────────
async function searchTasks() {
    const keyword = document.getElementById('searchInput').value.trim();
    if (!keyword) {
        loadTasks();
        return;
    }
    
    try {
        const res = await fetch(`${API}/tasks/search?keyword=${encodeURIComponent(keyword)}`);
        const data = await res.json();
        renderTasks(data.tasks, 'tasks-container');
    } catch (err) {
        console.error('Search failed:', err);
    }
}

// ── Create Task Modal ─────────────────────────────────
function openCreateModal() {
    document.getElementById('createModal').classList.add('open');
}

function closeModal() {
    document.getElementById('createModal').classList.remove('open');
    document.getElementById('taskTitle').value = '';
    document.getElementById('taskDescription').value = '';
    document.getElementById('taskPriority').value = 'medium';
    document.getElementById('taskAssigned').value = '';
    document.getElementById('taskDueDate').value = '';
}

async function createTask() {
    const title = document.getElementById('taskTitle').value.trim();
    if (!title) {
        alert('Task title is required');
        return;
    }
    
    const body = {
        title,
        description: document.getElementById('taskDescription').value,
        priority: document.getElementById('taskPriority').value,
        assigned_to: document.getElementById('taskAssigned').value,
        due_date: document.getElementById('taskDueDate').value
    };
    
    try {
        const res = await fetch(`${API}/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await res.json();
        if (data.success) {
            closeModal();
            loadTasks();
        }
    } catch (err) {
        alert('Failed to create task');
    }
}

// ── Complete Task ─────────────────────────────────────
async function completeTask(taskId) {
    try {
        const res = await fetch(`${API}/tasks/${taskId}/complete`, {
            method: 'PATCH'
        });
        const data = await res.json();
        if (data.success) loadTasks();
    } catch (err) {
        alert('Failed to complete task');
    }
}

// ── Delete Task ───────────────────────────────────────
async function deleteTask(taskId) {
    if (!confirm('Delete this task?')) return;
    
    try {
        const res = await fetch(`${API}/tasks/${taskId}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (data.success) loadTasks();
    } catch (err) {
        alert('Failed to delete task');
    }
}

// ── Chat ──────────────────────────────────────────────
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message) return;
    
    // Add user message
    addChatMessage(message, 'user');
    input.value = '';
    
    // Add loading
    const loadingId = 'loading-' + Date.now();
    addChatMessage('Thinking...', 'bot', loadingId);
    
    try {
        const res = await fetch(`${API}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        const data = await res.json();
        
        // Remove loading
        document.getElementById(loadingId)?.remove();
        
        if (data.success) {
            addChatMessage(data.response, 'bot');
            // Refresh tasks if task was modified
            if (['create_task', 'complete_task', 'delete_task', 'update_task'].includes(data.intent)) {
                loadTasks();
            }
        } else {
            addChatMessage('Sorry, something went wrong.', 'bot');
        }
    } catch (err) {
        document.getElementById(loadingId)?.remove();
        addChatMessage('Failed to connect to server.', 'bot');
    }
}

function addChatMessage(text, sender, id = null) {
    const messages = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = `chat-message ${sender}`;
    if (id) div.id = id;
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = text;
    div.appendChild(bubble);
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
}

// ── Init ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadTasks();
});