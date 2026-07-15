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
  const then = new Date(dateStr + 'Z').getTime();
  const diff = Math.floor((Date.now() - then) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
  if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
  return Math.floor(diff / 86400) + 'd ago';
}

function initials(name) {
  return (name || '?').trim().charAt(0).toUpperCase();
}

async function requireLogin() {
  const { user } = await api('GET', '/api/me');
  if (!user) { window.location.href = '/index.html'; return null; }
  return user;
}

async function renderNavbar(activePage) {
  const { user } = await api('GET', '/api/me');
  const nav = document.getElementById('navbar');
  if (!nav) return user;
  nav.innerHTML = `
    <div class="brand">SocialSphere</div>
    <div class="links">
      <a href="/feed.html" class="${activePage === 'feed' ? 'active' : ''}">Feed</a>
      <a href="/explore.html" class="${activePage === 'explore' ? 'active' : ''}">Explore</a>
      <a href="/profile.html?id=${user ? user.id : ''}" class="${activePage === 'profile' ? 'active' : ''}">Profile</a>
      <button id="logoutBtn">Logout</button>
    </div>
  `;
  document.getElementById('logoutBtn').onclick = async () => {
    await api('POST', '/api/logout');
    window.location.href = '/index.html';
  };
  return user;
}
