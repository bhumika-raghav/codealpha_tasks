function renderPost(p, me) {
  const isMine = me && me.id === p.user_id;
  return `
  <div class="post" data-id="${p.id}">
    <div class="post-header">
      <a href="/profile.html?id=${p.user_id}"><div class="avatar" style="background:${p.avatar_color}">${initials(p.display_name)}</div></a>
      <div class="names">
        <a href="/profile.html?id=${p.user_id}"><span class="display-name">${escapeHtml(p.display_name)}</span></a>
        <span class="username">@${escapeHtml(p.username)}</span>
      </div>
      <span class="time">${timeAgo(p.created_at)}</span>
    </div>
    <div class="post-content">${escapeHtml(p.content)}</div>
    <div class="post-actions">
      <button class="like-btn ${p.likedByMe ? 'liked' : ''}" data-id="${p.id}">
        ${p.likedByMe ? '❤' : '♡'} <span class="like-count">${p.likeCount}</span>
      </button>
      <button class="comment-toggle" data-id="${p.id}">💬 <span class="comment-count">${p.commentCount}</span></button>
      ${isMine ? `<button class="delete-btn" data-id="${p.id}">Delete</button>` : ''}
    </div>
    <div class="comments" id="comments-${p.id}">
      <div class="comment-list" id="comment-list-${p.id}"></div>
      <div class="comment-form">
        <input type="text" placeholder="Write a comment..." id="comment-input-${p.id}">
        <button class="primary" data-id="${p.id}" data-action="submit-comment">Send</button>
      </div>
    </div>
  </div>`;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}

function attachPostHandlers(me) {
  document.querySelectorAll('.like-btn').forEach(btn => {
    btn.onclick = async () => {
      const id = btn.dataset.id;
      const liked = btn.classList.contains('liked');
      const countEl = btn.querySelector('.like-count');
      if (liked) {
        await api('POST', `/api/posts/${id}/unlike`);
        btn.classList.remove('liked');
        btn.innerHTML = `♡ <span class="like-count">${Number(countEl.textContent) - 1}</span>`;
      } else {
        await api('POST', `/api/posts/${id}/like`);
        btn.classList.add('liked');
        btn.innerHTML = `❤ <span class="like-count">${Number(countEl.textContent) + 1}</span>`;
      }
    };
  });

  document.querySelectorAll('.delete-btn').forEach(btn => {
    btn.onclick = async () => {
      if (!confirm('Delete this post?')) return;
      await api('DELETE', `/api/posts/${btn.dataset.id}`);
      document.querySelector(`.post[data-id="${btn.dataset.id}"]`).remove();
    };
  });

  document.querySelectorAll('.comment-toggle').forEach(btn => {
    btn.onclick = async () => {
      const id = btn.dataset.id;
      const box = document.getElementById(`comments-${id}`);
      box.classList.toggle('open');
      if (box.classList.contains('open')) await loadComments(id);
    };
  });

  document.querySelectorAll('[data-action="submit-comment"]').forEach(btn => {
    btn.onclick = () => submitComment(btn.dataset.id);
  });
  document.querySelectorAll('[id^="comment-input-"]').forEach(input => {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const id = input.id.replace('comment-input-', '');
        submitComment(id);
      }
    });
  });
}

async function submitComment(id) {
  const input = document.getElementById(`comment-input-${id}`);
  const content = input.value.trim();
  if (!content) return;
  await api('POST', `/api/posts/${id}/comments`, { content });
  input.value = '';
  await loadComments(id);
  const countEl = document.querySelector(`.comment-toggle[data-id="${id}"] .comment-count`);
  countEl.textContent = Number(countEl.textContent) + 1;
}

async function loadComments(id) {
  const { comments } = await api('GET', `/api/posts/${id}/comments`);
  const list = document.getElementById(`comment-list-${id}`);
  list.innerHTML = comments.map(c => `
    <div class="comment">
      <div class="avatar small" style="background:${c.avatar_color}">${initials(c.display_name)}</div>
      <div class="bubble"><span class="cname">${escapeHtml(c.display_name)}</span>${escapeHtml(c.content)}</div>
    </div>
  `).join('') || '<div style="color:#999;font-size:13px;">No comments yet.</div>';
}
