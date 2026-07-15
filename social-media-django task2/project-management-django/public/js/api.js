async function api(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Request failed');
  return data;
}

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const then = new Date(dateStr).getTime();
  const diff = Math.floor((Date.now() - then) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
  if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
  return Math.floor(diff / 86400) + 'd ago';
}

function initials(name) {
  return (name || '?').trim().charAt(0).toUpperCase();
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}

function wsUrl(path) {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${location.host}${path}`;
}

async function renderNavbar(activePage) {
  const { user } = await api('GET', '/api/me');
  if (!user) { window.location.href = '/index.html'; return null; }

  const nav = document.getElementById('navbar');
  if (nav) {
    nav.innerHTML = `
      <div class="brand">TaskFlow</div>
      <div class="links">
        <a href="/dashboard.html" class="${activePage === 'dashboard' ? 'active' : ''}">Projects</a>
        <button class="bell" id="bellBtn">🔔<span class="dot" id="notifDot" style="display:none;">•</span></button>
        <span style="font-weight:600;">${escapeHtml(user.display_name)}</span>
        <div class="avatar small" style="background:${user.avatar_color}">${initials(user.display_name)}</div>
        <button id="logoutBtn">Logout</button>
      </div>
      <div class="notif-dropdown" id="notifDropdown"></div>
    `;
    document.getElementById('logoutBtn').onclick = async () => {
      await api('POST', '/api/logout');
      window.location.href = '/index.html';
    };
    document.getElementById('bellBtn').onclick = async () => {
      const dropdown = document.getElementById('notifDropdown');
      dropdown.classList.toggle('open');
      if (dropdown.classList.contains('open')) {
        const { notifications } = await api('GET', '/api/notifications');
        dropdown.innerHTML = notifications.map(n => `
          <div class="notif-item"><a href="${n.link || '#'}">${escapeHtml(n.message)}</a><div style="color:#999;font-size:11px;margin-top:2px;">${timeAgo(n.created_at)}</div></div>
        `).join('') || '<div class="notif-item">No notifications yet.</div>';
        await api('POST', '/api/notifications/read');
        document.getElementById('notifDot').style.display = 'none';
      }
    };
    checkNotifs();
    connectNotificationSocket();
  }
  return user;
}

async function checkNotifs() {
  const { notifications } = await api('GET', '/api/notifications');
  const unread = notifications.some(n => !n.read);
  const dot = document.getElementById('notifDot');
  if (dot) dot.style.display = unread ? 'flex' : 'none';
}

// A single WebSocket connection (per page load) that receives personal
// notification pushes from Django Channels. Reconnects once if dropped.
let notifSocket;
function connectNotificationSocket() {
  if (notifSocket && notifSocket.readyState === WebSocket.OPEN) return notifSocket;
  notifSocket = new WebSocket(wsUrl('/ws/notifications/'));
  notifSocket.onmessage = () => {
    const dot = document.getElementById('notifDot');
    if (dot) dot.style.display = 'flex';
  };
  notifSocket.onclose = () => { notifSocket = null; };
  return notifSocket;
}

// One WebSocket per open project board; used only on project.html.
function connectProjectSocket(projectId, onEvent) {
  const socket = new WebSocket(wsUrl(`/ws/project/${projectId}/`));
  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onEvent(data.type, data.payload);
  };
  return socket;
}
