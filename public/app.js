const app = document.querySelector('#app');
const toastEl = document.querySelector('#toast');

const state = { user: null, requests: [], caretakers: [], authMode: 'login', authRole: 'family', filter: 'all', familyView: 'requests', selectedSkill: 'Any', highlightRequestId: null, timerInterval: null, watchInterval: null, theme: localStorage.getItem('caresathi-theme') || 'light' };
document.documentElement.dataset.theme = state.theme;

const esc = (value = '') => String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const money = value => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);
const fmtDate = value => new Date(`${value}T00:00:00`).toLocaleDateString('en-IN', { weekday:'short', day:'numeric', month:'short' });
const titleCase = value => value.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
const skillList = ['Any','Night vigil','Post-op mobility','Dementia & elder companion','General companionship'];

function skillMatch(skills = '', needed = 'Any') {
  if (!needed || needed === 'Any') return 85;
  return skills.split('|').map(s => s.trim().toLowerCase()).includes(needed.toLowerCase()) ? 100 : 35;
}

function notify(message, error = false) {
  toastEl.textContent = message;
  toastEl.className = `toast show${error ? ' error' : ''}`;
  clearTimeout(notify.timer);
  notify.timer = setTimeout(() => toastEl.className = 'toast', 2800);
}

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Something went wrong');
  return data;
}

function logo(light = false) {
  return `<a class="logo ${light ? 'logo-light' : ''}" href="#/" aria-label="CareSathi home"><span class="logo-mark"><svg viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="12.5" r="3.2"/><path d="M9.5 17c0-4.5 5.1-6.7 8.2-2.8l2.3 3 2.3-3c3.1-3.9 8.2-1.7 8.2 2.8 0 6.6-10.5 13.2-10.5 13.2S9.5 23.6 9.5 17Z"/></svg></span><span class="logo-word">Care<span>Sathi</span></span></a>`;
}

function themeButton() {
  const next = state.theme === 'light' ? 'dark' : 'light';
  return `<button class="theme-toggle" data-theme-toggle aria-label="Switch to ${next} mode" title="Switch to ${next} mode"><span class="sun">☼</span><span class="moon">☾</span></button>`;
}

function bindTheme() {
  document.querySelectorAll('[data-theme-toggle]').forEach(button => button.onclick = () => {
    state.theme = state.theme === 'light' ? 'dark' : 'light';
    document.documentElement.dataset.theme = state.theme;
    localStorage.setItem('caresathi-theme', state.theme);
    button.setAttribute('aria-label', `Switch to ${state.theme === 'light' ? 'dark' : 'light'} mode`);
  });
}

function landing() {
  app.innerHTML = `<div class="shell">
    <header class="container"><nav class="nav">${logo()}<div class="nav-links"><a href="#how">How it works</a><a href="#safety">Safety</a><a href="#about">About us</a></div><div class="nav-actions">${themeButton()}<button class="btn btn-ghost" data-auth="login">Sign in</button><button class="btn btn-primary" data-auth="register">Find a CareSathi</button></div></nav></header>
    <main>
      <section class="hero"><div class="container hero-grid"><div>
        <div class="eyebrow">Trusted hospital companionship</div>
        <h1>Care, when family <em>can't be there.</em></h1>
        <p class="lead">Connect with verified, compassionate attendants for your loved ones in hospital—by the hour, exactly when you need them.</p>
        <div class="hero-actions"><button class="btn btn-primary" data-auth="register">Find a caretaker <span>→</span></button><button class="btn btn-outline" data-caretaker>Become a CareSathi</button></div>
        <div class="trust-line"><div class="avatar-stack"><span class="mini-avatar av1">AV</span><span class="mini-avatar av2">IS</span><span class="mini-avatar av3">MJ</span></div><span>Trusted attendants · Clear hourly pricing · Direct updates</span></div>
      </div><div class="hero-visual" aria-label="Hospital caretaker illustration"><div class="photo-panel"><div class="illustration-head"></div><div class="illustration-hair"></div><div class="illustration-body"></div><div class="illustration-scarf"></div></div><div class="float-card verified-card"><div class="card-label"><span class="pulse"></span>Verification status</div><div class="card-value">ID verified</div></div><div class="float-card care-card"><div class="icon-box">24</div><div><div class="card-label">Support available</div><div class="card-value">Day & night</div></div></div></div></div></section>
      <section class="stats-bar"><div class="container stats"><div class="stat"><strong id="stat-caretakers">3+</strong><span>verified caretakers</span></div><div class="stat"><strong>4.9/5</strong><span>average care rating</span></div><div class="stat"><strong id="stat-completed">140+</strong><span>care shifts completed</span></div><div class="stat"><strong>₹100–₹250</strong><span>typical hourly range</span></div></div></section>
      <section class="section" id="how"><div class="container"><div class="section-head center"><div class="eyebrow">Simple and reassuring</div><h2>Help is only a few steps away</h2><p class="section-copy">Create a request in minutes. A nearby CareSathi can accept and meet your family at the hospital.</p></div><div class="steps"><article class="step-card"><div class="step-no">01</div><h3>Share care needs</h3><p>Tell us the hospital, shift timings, and the kind of non-clinical support your loved one needs.</p></article><article class="step-card"><div class="step-no">02</div><h3>Connect locally</h3><p>Your request appears to available CareSathis in the same city with transparent rates and details.</p></article><article class="step-card"><div class="step-no">03</div><h3>Stay reassured</h3><p>Track the assignment from acceptance to completion and keep the caretaker's contact handy.</p></article></div></div></section>
      <section class="section safety" id="safety"><div class="container safety-grid"><div class="safety-panel"><div class="shield">✓</div><h3>Safety at every step</h3><p>A safer experience starts with visible identity status, clear scope, and accountable shift tracking.</p></div><div><div class="eyebrow">Built for trust</div><h2>Your loved one deserves dependable company</h2><p class="section-copy">CareSathi is designed for companionship and everyday bedside assistance—not clinical or emergency care.</p><div class="checks"><div class="check"><span class="check-icon">✓</span><div><h3>Verified profiles</h3><p>Identity and background verification status is clearly visible before booking.</p></div></div><div class="check"><span class="check-icon">✓</span><div><h3>Defined care scope</h3><p>Care details, time, hospital, and hourly payout are agreed upfront.</p></div></div><div class="check"><span class="check-icon">✓</span><div><h3>Tracked assignments</h3><p>Every request moves through accepted, active, and completed stages.</p></div></div></div></div></div></section>
      <section class="cta" id="about"><div class="container"><div class="cta-box"><div><h2>A little support can bring a family a lot of peace.</h2><p>Create a care request today or earn by being there for someone.</p></div><button class="btn" data-auth="register">Get started →</button></div></div></section>
    </main><footer><div class="container footer-inner">${logo()}<span>Non-clinical support only · In an emergency, contact hospital staff immediately.</span><div class="footer-links"><a href="#safety">Safety</a><a href="#how">How it works</a></div></div></footer>
  </div>`;
  bindLanding();
  api('/api/stats').then(s => { document.querySelector('#stat-caretakers').textContent = `${s.caretakers}+`; document.querySelector('#stat-completed').textContent = `${s.completed}+`; }).catch(()=>{});
}

function bindLanding() {
  bindTheme();
  document.querySelectorAll('[data-auth]').forEach(el => el.onclick = () => { state.authMode = el.dataset.auth; auth(); });
  document.querySelectorAll('[data-caretaker]').forEach(el => el.onclick = () => { state.authMode = 'register'; state.authRole = 'caretaker'; auth(); });
}

function auth() {
  const register = state.authMode === 'register';
  app.innerHTML = `<div class="auth-page"><aside class="auth-aside">${logo(true)}<div class="auth-quote"><div class="eyebrow" style="color:#c5ddd7">Care that feels close</div><h1>${register ? 'Join a network built around kindness.' : 'Welcome back to your circle of care.'}</h1><p>${register ? 'Whether you need a trusted companion or want to offer your time, CareSathi helps people show up for each other.' : 'Sign in to manage requests, track assignments, and keep care moving.'}</p><div class="auth-points"><span class="auth-point">Identity-first profiles</span><span class="auth-point">Local opportunities</span><span class="auth-point">Clear hourly rates</span></div></div><small style="color:#89aaa2;position:relative;z-index:1">Non-clinical hospital attendance platform</small></aside><main class="auth-main"><div class="auth-box"><div class="auth-top"><button class="back-link" data-home>← Back to home</button>${themeButton()}</div><h2>${register ? 'Create your account' : 'Welcome back'}</h2><p class="muted">${register ? 'Choose how you want to use CareSathi.' : 'Enter your details to continue.'}</p>
    <div class="role-tabs"><button class="role-tab ${state.authRole==='family'?'active':''}" data-role="family">I need a caretaker</button><button class="role-tab ${state.authRole==='caretaker'?'active':''}" data-role="caretaker">I am a caretaker</button></div>
    <form id="auth-form">${register ? `<div class="form-grid"><div class="field full"><label>Full name</label><input name="name" autocomplete="name" placeholder="Your full name" required></div><div class="field"><label>Phone number</label><input name="phone" inputmode="numeric" autocomplete="tel" placeholder="10-digit number" required></div><div class="field"><label>City</label><input name="city" placeholder="e.g. Pune" required></div></div>` : ''}<div class="field"><label>Email address</label><input type="email" name="email" autocomplete="email" placeholder="you@example.com" required></div><div class="field"><label>Password</label><input type="password" name="password" autocomplete="${register?'new-password':'current-password'}" placeholder="Minimum 6 characters" minlength="6" required></div>${!register ? `<div class="demo-box">Demo: <strong>${state.authRole==='family'?'family@demo.in':'asha@demo.in'}</strong> · Password: <strong>demo123</strong></div>` : `<p class="form-note">By continuing, you agree to use CareSathi only for lawful, non-clinical support.</p>`}<button class="btn btn-primary btn-block" type="submit">${register ? 'Create account' : 'Sign in'} →</button></form><p class="form-switch">${register?'Already have an account?':'New to CareSathi?'} <button class="link-button" data-switch>${register?'Sign in':'Create account'}</button></p></div></main></div>`;
  document.querySelector('[data-home]').onclick = landing;
  document.querySelector('[data-switch]').onclick = () => { state.authMode = register ? 'login' : 'register'; auth(); };
  document.querySelectorAll('[data-role]').forEach(el => el.onclick = () => { state.authRole = el.dataset.role; auth(); });
  document.querySelector('#auth-form').onsubmit = submitAuth;
  bindTheme();
}

async function submitAuth(event) {
  event.preventDefault();
  const button = event.target.querySelector('button[type="submit"]');
  button.disabled = true; button.textContent = 'Please wait…';
  const data = Object.fromEntries(new FormData(event.target)); data.role = state.authRole;
  try {
    const result = await api(`/api/${state.authMode}`, { method:'POST', body:JSON.stringify(data) });
    state.user = result.user; notify(`Welcome, ${state.user.name.split(' ')[0]}`); await dashboard();
  } catch (error) { notify(error.message, true); button.disabled = false; button.textContent = state.authMode === 'register' ? 'Create account →' : 'Sign in →'; }
}

async function dashboard() {
  try {
    state.requests = await api('/api/requests');
    if (state.user.role === 'family') state.caretakers = await api('/api/caretakers');
  } catch (e) { if (e.message.includes('sign in')) return auth(); notify(e.message, true); }
  const family = state.user.role === 'family';
  const active = state.requests.filter(r => ['accepted','in_progress'].includes(r.status)).length;
  const completed = state.requests.filter(r => r.status === 'completed').length;
  const open = state.requests.filter(r => r.status === 'open').length;
  const heading = family && state.familyView === 'caretakers' ? 'Top CareSathis near you' : (family ? 'Care requests' : 'Available near you');
  const panelControls = family
    ? `<div class="view-switch"><button class="pill ${state.familyView==='requests'?'active':''}" data-view="requests">My requests</button><button class="pill ${state.familyView==='caretakers'?'active':''}" data-view="caretakers">Find caretakers</button></div>`
    : `<div class="filter-pills">${['all','open','active','completed'].map(f=>`<button class="pill ${state.filter===f?'active':''}" data-filter="${f}">${titleCase(f)}</button>`).join('')}</div>`;
  app.innerHTML = `<div class="app-shell"><header class="app-nav"><div class="container app-nav-inner">${logo()}<div class="app-nav-actions">${themeButton()}<button class="btn btn-ghost btn-sm" data-refresh>Refresh</button><div class="user-chip"><div class="user-avatar">${esc(state.user.name.split(' ').map(x=>x[0]).slice(0,2).join(''))}</div><div class="user-meta"><strong>${esc(state.user.name)}</strong><span>${state.user.role}</span></div></div><button class="btn btn-outline btn-sm" data-logout>Sign out</button></div></div></header><main class="dashboard"><div class="container"><div class="dash-head"><div><h1>${family ? 'Your care circle' : 'Care opportunities'}</h1><p>${family ? 'Manage support and discover trusted local CareSathis.' : `Showing requests near ${esc(state.user.city)}.`}</p></div>${family ? '<button class="btn btn-primary" data-new>+ Create care request</button>' : ''}</div><div class="summary-grid"><div class="summary-card"><div class="summary-icon">${family?'●':'₹'}</div><div><strong>${family?active:open}</strong><span>${family?'active assignments':'open requests nearby'}</span></div></div><div class="summary-card"><div class="summary-icon">✓</div><div><strong>${family?completed:state.user.jobs_completed}</strong><span>completed shifts</span></div></div><div class="summary-card"><div class="summary-icon">${family?'⌁':'★'}</div><div><strong>${family?state.requests.length:(state.user.rating || 'New')}</strong><span>${family?'total care requests':'caretaker rating'}</span></div></div></div><div class="content-grid"><section class="panel"><div class="panel-title"><h2 id="panel-heading">${heading}</h2>${panelControls}</div><div class="request-list" id="request-list"></div></section><aside class="sidebar-stack">${family ? `<div class="info-card"><h3>Care profile</h3><p>Add clear details so CareSathis can understand the support required before accepting.</p><div class="progress-track"><div class="progress-fill"></div></div><small>Profile readiness · 72%</small></div>` : `<div class="info-card"><h3>${state.user.verified?'Verified profile':'Verification pending'}</h3><p>${state.user.verified?'Your verified status helps families book with greater confidence.':'Complete identity verification before a public launch.'}</p><div class="progress-track"><div class="progress-fill" style="width:${state.user.verified?100:45}%"></div></div><small>${state.user.verified?'Ready to accept':'Finish profile setup'}</small></div>`}<div class="info-card light"><h3>Need immediate help?</h3><p>CareSathis cannot provide medical care. Contact the nursing station or hospital emergency team for urgent needs.</p></div></aside></div></div></main></div>`;
  renderMainContent(); bindDashboard(); bindTheme();
}

function renderMainContent() {
  const heading = document.querySelector('#panel-heading');
  if (state.user.role === 'family' && state.familyView === 'caretakers') {
    heading.textContent = 'Top CareSathis near you';
    renderCaretakers();
  } else {
    heading.textContent = state.user.role === 'family' ? 'Care requests' : 'Available near you';
    renderRequests();
  }
}

function requestMatches(r) {
  if (state.filter === 'all') return true;
  if (state.filter === 'active') return ['accepted','in_progress'].includes(r.status);
  return r.status === state.filter;
}

function renderRequests() {
  clearInterval(state.timerInterval);
  const list = document.querySelector('#request-list');
  const rows = state.requests.filter(requestMatches);
  if (!rows.length) { list.innerHTML = `<div class="empty"><div class="empty-icon">⌁</div><h3>No requests here yet</h3><p>${state.user.role==='family'?'Create a request whenever your family needs support.':'New nearby requests will appear here.'}</p></div>`; return; }
  list.innerHTML = rows.map(requestCard).join('');
  list.querySelectorAll('[data-action]').forEach(btn => btn.onclick = () => {
    if (btn.dataset.action === 'start') return showOtpModal(btn.dataset.id);
    if (btn.dataset.action === 'complete') return showEndShiftModal(btn.dataset.id);
    if (btn.dataset.action === 'release') return showReleaseModal(btn.dataset.id);
    performAction(btn.dataset.id, btn.dataset.action).catch(async e => { notify(e.message, true); await dashboard(); });
  });
  list.querySelectorAll('[data-rate]').forEach(btn => btn.onclick = () => showRatingModal(btn.dataset.id, btn.dataset.person));
  list.querySelectorAll('[data-watch-link]').forEach(btn => btn.onclick = () => showWatchShareModal(btn.dataset.id));
  updateTimers();
  state.timerInterval = setInterval(updateTimers, 1000);
}

function requestCard(r) {
  const family = state.user.role === 'family';
  const actions = [];
  if (!family && r.status === 'open') actions.push(`<button class="btn btn-primary btn-sm" data-action="accept" data-id="${r.id}">Accept request</button>`);
  if (!family && r.status === 'accepted' && r.caretaker_id === state.user.id) {
    actions.push(`<button class="btn btn-outline btn-sm" data-action="release" data-id="${r.id}">Release request</button>`);
    actions.push(`<button class="btn btn-dark btn-sm" data-action="start" data-id="${r.id}">Enter OTP & start</button>`);
  }
  if (!family && r.status === 'in_progress' && r.caretaker_id === state.user.id) actions.push(`<button class="btn btn-primary btn-sm" data-action="complete" data-id="${r.id}">End shift</button>`);
  if (family && ['open','accepted'].includes(r.status)) actions.push(`<button class="btn btn-outline btn-sm" data-action="cancel" data-id="${r.id}">Cancel</button>`);
  if (family && r.status === 'in_progress' && !r.end_requested) actions.push(`<button class="btn btn-outline btn-sm" data-action="request_end" data-id="${r.id}">Request early end</button>`);
  if (family && !['cancelled','open'].includes(r.status)) actions.push(`<button class="btn btn-outline btn-sm" data-watch-link data-id="${r.id}">Share live watch</button>`);
  if (r.status === 'completed' && !r.my_rating) actions.push(`<button class="btn btn-primary btn-sm" data-rate data-id="${r.id}" data-person="${esc(family ? (r.caretaker_name || 'CareSathi') : (r.family_name || 'family'))}">Rate experience</button>`);
  if (r.status === 'completed' && r.my_rating) actions.push(`<span class="rated-chip">Your rating ★ ${r.my_rating}</span>`);
  const action = `<div class="card-actions">${actions.join('')}</div>`;
  const caretaker = family && r.caretaker_name ? `<div class="request-notes" style="margin-top:8px"><strong>CareSathi:</strong> ${esc(r.caretaker_name)} · ${esc(r.caretaker_phone || '')} ${r.caretaker_rating ? `· ★ ${r.caretaker_rating}` : ''}</div>` : '';
  const familyReputation = !family && r.family_name ? `<div class="request-notes" style="margin-top:8px"><strong>Family contact:</strong> ${esc(r.family_name)} ${r.family_rating_count ? `· ★ ${r.family_rating} (${r.family_rating_count})` : '· New to CareSathi'}</div>` : '';
  const releaseNotice = family && r.status === 'open' && r.last_release_reason ? `<div class="release-notice"><strong>Returned to the marketplace by ${esc(r.last_released_by || 'a CareSathi')}</strong><span>${esc(r.last_release_reason)}</span></div>` : '';
  const neededSkill = `<div class="skill-needed"><span>Needed</span><strong>${esc(r.skill_needed || 'General companionship')}</strong>${!family ? `<b>${skillMatch(state.user.skills,r.skill_needed)}% match</b>` : ''}</div>`;
  const otp = family && r.status === 'accepted' && r.start_otp ? `<div class="otp-card"><span>Shift start OTP</span><strong>${esc(r.start_otp)}</strong><small>Share only when the CareSathi arrives.</small></div>` : '';
  const timer = r.status === 'in_progress' ? `<div class="live-shift ${r.end_requested?'end-alert':''}"><span class="live-dot"></span><div><small>${r.end_requested ? 'Family has requested an early end' : 'Shift in progress'}</small><strong class="shift-timer" data-started="${esc(r.started_at)}">00:00:00</strong></div></div>` : '';
  const billed = r.status === 'completed' && r.actual_minutes ? `<div class="billing-result"><span>Actual time <strong>${formatMinutes(r.actual_minutes)}</strong></span><span>Final payout <strong>${money(r.final_amount)}</strong></span></div>` : '';
  const estimate = r.status === 'completed' && r.final_amount ? `<strong>${money(r.final_amount)}</strong> final · billed by minute` : `<strong>${money(r.hourly_rate * r.hours)}</strong> estimated · ${money(r.hourly_rate)}/hour`;
  return `<article class="request-card ${Number(state.highlightRequestId)===r.id?'new-request':''}" data-request-id="${r.id}"><div class="request-top"><div><h3>${esc(r.patient_name)}, ${r.patient_age}</h3><div class="location">${esc(r.hospital)} · ${esc(r.ward_room)}</div></div><span class="status status-${r.status}">${titleCase(r.status)}</span></div><div class="request-details"><div class="detail"><span>Date</span><strong>${fmtDate(r.care_date)}</strong></div><div class="detail"><span>Starts</span><strong>${esc(r.start_time)}</strong></div><div class="detail"><span>Booked for</span><strong>${r.hours} hours</strong></div><div class="detail"><span>Preference</span><strong>${esc(r.gender_preference)}</strong></div></div>${neededSkill}<div class="request-notes">${esc(r.support_notes || 'General companionship and bedside assistance.')}</div>${caretaker}${familyReputation}${releaseNotice}${otp}${timer}${billed}<div class="request-footer"><div class="earning">${estimate}</div>${action}</div></article>`;
}

function formatMinutes(minutes) {
  const hours = Math.floor(minutes / 60), mins = minutes % 60;
  return hours ? `${hours}h ${mins}m` : `${mins} min`;
}

function updateTimers() {
  document.querySelectorAll('.shift-timer').forEach(el => {
    const elapsed = Math.max(0, Math.floor((Date.now() - new Date(el.dataset.started).getTime()) / 1000));
    const h = String(Math.floor(elapsed / 3600)).padStart(2,'0');
    const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2,'0');
    const s = String(elapsed % 60).padStart(2,'0');
    el.textContent = `${h}:${m}:${s}`;
  });
}

function renderCaretakers() {
  clearInterval(state.timerInterval);
  const list = document.querySelector('#request-list');
  const local = state.caretakers.filter(c => c.nearby);
  const ordered = [...state.caretakers].sort((a,b) => (skillMatch(b.skills,state.selectedSkill)-skillMatch(a.skills,state.selectedSkill)) || (Number(b.nearby)-Number(a.nearby)) || (b.rating-a.rating));
  list.innerHTML = `<div class="matching-radar"><div><span>Specialized matching radar</span><strong>Find the right Saathi for this need</strong></div><select id="skill-radar" aria-label="Care skill needed">${skillList.map(skill=>`<option ${skill===state.selectedSkill?'selected':''}>${skill}</option>`).join('')}</select></div><div class="directory-note"><strong>${local.length} CareSathis near ${esc(state.user.city)}</strong><span>Ranked by skill match, location, verification, and rating.</span></div><div class="caretaker-grid">${ordered.map((c,index) => {const match=skillMatch(c.skills,state.selectedSkill);return `<article class="caretaker-card"><div class="caretaker-top"><div class="caretaker-avatar">${esc(c.name.split(' ').map(x=>x[0]).slice(0,2).join(''))}</div><div><h3>${esc(c.name)}</h3><div class="location">${esc(c.city)} ${c.verified?'· ID verified':''}</div></div><span class="match-score ${match===100?'perfect':''}">${match}% match</span></div><div class="credential-badge">${c.credential_verified?'✓ ':''}${esc(c.credential_badge)}</div><p>${esc(c.headline)}</p><div class="skill-badges">${esc(c.skills).split('|').map(skill=>`<span class="${skill===state.selectedSkill?'matched':''}">${skill}</span>`).join('')}</div><div class="tags">${esc(c.languages).split(', ').map(l=>`<span>${l}</span>`).join('')}</div><div class="caretaker-stats"><span><strong>★ ${c.rating || 'New'}</strong> ${c.rating_count||0} ratings</span><span><strong>${c.jobs_completed}</strong> shifts</span><span><strong>${c.experience_years} yr</strong> exp.</span></div><div class="caretaker-footer"><strong>${money(c.hourly_rate)}<small>/hour</small></strong><button class="btn btn-primary btn-sm" data-book>Request care</button></div></article>`}).join('')}</div>`;
  document.querySelector('#skill-radar').onchange = e => { state.selectedSkill=e.target.value; renderCaretakers(); };
  list.querySelectorAll('[data-book]').forEach(button => button.onclick = showRequestModal);
}

function bindDashboard() {
  document.querySelector('[data-logout]').onclick = async () => { await api('/api/logout',{method:'POST'}); state.user=null; landing(); };
  document.querySelector('[data-refresh]').onclick = dashboard;
  document.querySelectorAll('[data-filter]').forEach(el => el.onclick = () => { state.filter = el.dataset.filter; document.querySelectorAll('[data-filter]').forEach(x=>x.classList.toggle('active',x.dataset.filter===state.filter)); renderRequests(); });
  document.querySelectorAll('[data-view]').forEach(el => el.onclick = () => { state.familyView = el.dataset.view; document.querySelectorAll('[data-view]').forEach(x=>x.classList.toggle('active',x.dataset.view===state.familyView)); renderMainContent(); });
  const create = document.querySelector('[data-new]'); if (create) create.onclick = showRequestModal;
}

function showRequestModal() {
  const tomorrow = new Date(Date.now()+864e5).toISOString().slice(0,10);
  const wrap = document.createElement('div'); wrap.className='modal-wrap'; wrap.innerHTML=`<div class="modal"><div class="modal-head"><div><h2>Create a care request</h2><p class="muted" style="margin:5px 0 0">Share enough detail for a safe handover.</p></div><button class="close" data-close aria-label="Close">×</button></div><form id="request-form"><div class="form-grid"><div class="field"><label>Patient's name</label><input name="patient_name" required></div><div class="field"><label>Age</label><input name="patient_age" type="number" min="1" max="120" required></div><div class="field full"><label>Hospital</label><input name="hospital" placeholder="Hospital name" required></div><div class="field"><label>City</label><input name="city" value="${esc(state.user.city)}" required></div><div class="field"><label>Ward / room</label><input name="ward_room" placeholder="e.g. Ward B · Room 204" required></div><div class="field"><label>Date</label><input name="care_date" type="date" min="${tomorrow}" value="${tomorrow}" required></div><div class="field"><label>Start time</label><input name="start_time" type="time" value="20:00" required></div><div class="field"><label>Hours needed</label><input name="hours" type="number" min="1" max="24" value="8" required></div><div class="field"><label>Hourly rate (₹)</label><input name="hourly_rate" type="number" min="50" value="150" required></div><div class="field"><label>Caretaker preference</label><select name="gender_preference"><option>Any</option><option>Female preferred</option><option>Male preferred</option></select></div><div class="field"><label>Specialized need</label><select name="skill_needed">${skillList.filter(s=>s!=='Any').map(s=>`<option ${s===state.selectedSkill?'selected':''}>${s}</option>`).join('')}</select></div><div class="field full"><label>Support notes</label><textarea name="support_notes" placeholder="Mobility, meal, communication, or companionship needs. Do not include sensitive medical records."></textarea></div></div><label class="consent"><input type="checkbox" required><span>I understand this is non-clinical support. Medical tasks and emergencies remain the responsibility of hospital staff.</span></label><button class="btn btn-primary btn-block" type="submit">Publish request →</button></form></div>`;
  document.body.appendChild(wrap); const close=()=>wrap.remove(); wrap.querySelector('[data-close]').onclick=close; wrap.onclick=e=>{if(e.target===wrap)close()}; wrap.querySelector('form').onsubmit=async e=>{e.preventDefault();const btn=e.target.querySelector('button[type=submit]');btn.disabled=true;btn.textContent='Publishing…';const data=Object.fromEntries(new FormData(e.target));try{const created=await api('/api/requests',{method:'POST',body:JSON.stringify(data)});state.familyView='requests';state.filter='all';state.highlightRequestId=created.id;close();notify('Care request published — showing it below');await dashboard();requestAnimationFrame(()=>document.querySelector(`[data-request-id="${created.id}"]`)?.scrollIntoView({behavior:'smooth',block:'center'}));setTimeout(()=>{state.highlightRequestId=null},3500)}catch(err){notify(err.message,true);btn.disabled=false;btn.textContent='Publish request →'}};
}

function showOtpModal(id) {
  const wrap = document.createElement('div');
  wrap.className = 'modal-wrap';
  wrap.innerHTML = `<div class="modal compact-modal"><div class="otp-symbol">•••</div><div class="modal-head"><div><h2>Verify shift start</h2><p class="muted" style="margin:6px 0 0">Ask the patient's relative for the 6-digit OTP.</p></div><button class="close" data-close aria-label="Close">×</button></div><form><div class="field"><label>Start OTP</label><input class="otp-input" name="otp" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" placeholder="000000" autocomplete="one-time-code" required autofocus></div><p class="form-note">The paid timer starts only after successful verification.</p><button class="btn btn-primary btn-block" type="submit">Verify and start timer</button></form></div>`;
  document.body.appendChild(wrap);
  const close = () => wrap.remove();
  wrap.querySelector('[data-close]').onclick = close;
  wrap.onclick = e => { if (e.target === wrap) close(); };
  wrap.querySelector('form').onsubmit = async e => {
    e.preventDefault();
    const button = e.target.querySelector('button[type=submit]');
    button.disabled = true; button.textContent = 'Verifying…';
    const otp = new FormData(e.target).get('otp');
    try { await performAction(id, 'start', {otp}, false); close(); notify('OTP verified — shift timer started'); await dashboard(); }
    catch (error) { notify(error.message, true); button.disabled = false; button.textContent = 'Verify and start timer'; }
  };
}

function showEndShiftModal(id) {
  const request = state.requests.find(r => String(r.id) === String(id));
  const elapsed = request?.started_at ? Math.max(1, Math.ceil((Date.now() - new Date(request.started_at).getTime()) / 60000)) : 1;
  const amount = Math.max(1, Math.round((request?.hourly_rate || 0) * elapsed / 60));
  const wrap = document.createElement('div');
  wrap.className = 'modal-wrap';
  wrap.innerHTML = `<div class="modal compact-modal"><div class="modal-head"><div><h2>End this shift?</h2><p class="muted" style="margin:6px 0 0">The timer will stop and the final amount will be recorded.</p></div><button class="close" data-close aria-label="Close">×</button></div><div class="end-summary"><div><span>Time so far</span><strong>${formatMinutes(elapsed)}</strong></div><div><span>Current payout</span><strong>${money(amount)}</strong></div></div>${request?.end_requested?'<div class="early-end-note">The family has requested that this shift end early.</div>':''}<button class="btn btn-primary btn-block" data-confirm-end>End shift and calculate payout</button></div>`;
  document.body.appendChild(wrap);
  const close = () => wrap.remove();
  wrap.querySelector('[data-close]').onclick = close;
  wrap.onclick = e => { if (e.target === wrap) close(); };
  wrap.querySelector('[data-confirm-end]').onclick = async e => {
    e.target.disabled = true; e.target.textContent = 'Ending shift…';
    try { await performAction(id, 'complete', {}, false); close(); notify('Shift ended and payout calculated'); await dashboard(); }
    catch (error) { notify(error.message, true); e.target.disabled = false; e.target.textContent = 'End shift and calculate payout'; }
  };
}

function showReleaseModal(id) {
  const wrap=document.createElement('div');
  wrap.className='modal-wrap';
  wrap.innerHTML=`<div class="modal compact-modal"><div class="modal-head"><div><h2>Release this request?</h2><p class="muted" style="margin:6px 0 0">It will immediately become available to other matching CareSathis.</p></div><button class="close" data-close aria-label="Close">×</button></div><form><div class="field"><label>Reason</label><select name="reason_type" required><option value="">Choose a reason</option><option>Schedule conflict</option><option>Unable to reach the hospital</option><option>Family requirements changed</option><option>Personal emergency</option><option>Other</option></select></div><div class="field"><label>Additional details</label><textarea name="details" maxlength="400" placeholder="Give the family a clear, respectful explanation."></textarea></div><div class="release-warning">Your name and reason will be shown to the family. The start OTP will be cancelled.</div><button class="btn btn-primary btn-block" type="submit">Release to other CareSathis</button></form></div>`;
  document.body.appendChild(wrap);const close=()=>wrap.remove();wrap.querySelector('[data-close]').onclick=close;wrap.onclick=e=>{if(e.target===wrap)close()};
  wrap.querySelector('form').onsubmit=async e=>{e.preventDefault();const data=Object.fromEntries(new FormData(e.target));const reason=`${data.reason_type}${data.details?`: ${data.details}`:''}`;const button=e.target.querySelector('button[type=submit]');button.disabled=true;button.textContent='Releasing…';try{await performAction(id,'release',{reason},false);close();notify('Request released and available to other CareSathis');await dashboard()}catch(error){notify(error.message,true);button.disabled=false;button.textContent='Release to other CareSathis'}};
}

function showRatingModal(id, person) {
  const wrap = document.createElement('div');
  wrap.className = 'modal-wrap';
  wrap.innerHTML = `<div class="modal compact-modal"><div class="modal-head"><div><h2>Rate ${esc(person)}</h2><p class="muted" style="margin:6px 0 0">Your feedback builds trust on both sides.</p></div><button class="close" data-close aria-label="Close">×</button></div><form><div class="star-picker" role="radiogroup" aria-label="Rating">${[1,2,3,4,5].map(n=>`<button type="button" data-star="${n}" aria-label="${n} stars">★</button>`).join('')}</div><input type="hidden" name="stars" required><div class="field"><label>Short review (optional)</label><textarea name="review" maxlength="500" placeholder="How was the communication, behaviour, and overall experience?"></textarea></div><button class="btn btn-primary btn-block" type="submit" disabled>Submit rating</button></form></div>`;
  document.body.appendChild(wrap);
  const close=()=>wrap.remove(); wrap.querySelector('[data-close]').onclick=close; wrap.onclick=e=>{if(e.target===wrap)close()};
  wrap.querySelectorAll('[data-star]').forEach(star => star.onclick=()=>{const value=Number(star.dataset.star);wrap.querySelector('[name=stars]').value=value;wrap.querySelectorAll('[data-star]').forEach(s=>s.classList.toggle('selected',Number(s.dataset.star)<=value));wrap.querySelector('button[type=submit]').disabled=false});
  wrap.querySelector('form').onsubmit=async e=>{e.preventDefault();const button=e.target.querySelector('button[type=submit]');button.disabled=true;button.textContent='Saving…';const data=Object.fromEntries(new FormData(e.target));try{await performAction(id,'rate',data,false);close();notify('Thank you — rating submitted');await dashboard()}catch(error){notify(error.message,true);button.disabled=false;button.textContent='Submit rating'}};
}

async function showWatchShareModal(id) {
  try {
    const result = await performAction(id,'watch_link',{},false);
    const request = state.requests.find(r=>String(r.id)===String(id));
    const link = `${location.origin}/?watch=${encodeURIComponent(result.token)}`;
    const message = `CareSathi live watch for ${request.patient_name} · ${request.hospital}, ${request.ward_room}. Assigned CareSathi: ${request.caretaker_name || 'pending'}. Emergency: 112 · Ambulance: 108. Private link: ${link}`;
    const wrap=document.createElement('div');wrap.className='modal-wrap';wrap.innerHTML=`<div class="modal compact-modal"><div class="modal-head"><div><h2>Family live watch</h2><p class="muted" style="margin:6px 0 0">Anyone with this private link can view this room's care status.</p></div><button class="close" data-close aria-label="Close">×</button></div><div class="share-preview"><span>Private watch link</span><strong>${esc(request.hospital)} · ${esc(request.ward_room)}</strong><code>${esc(link)}</code></div><div class="share-actions"><button class="btn btn-dark" data-copy>Copy private link</button><a class="btn btn-whatsapp" target="_blank" rel="noopener" href="https://wa.me/?text=${encodeURIComponent(message)}">Share on WhatsApp</a></div><p class="privacy-note">Share only with trusted family. The link exposes patient location and assignment status.</p></div>`;
    document.body.appendChild(wrap);const close=()=>wrap.remove();wrap.querySelector('[data-close]').onclick=close;wrap.onclick=e=>{if(e.target===wrap)close()};wrap.querySelector('[data-copy]').onclick=async()=>{await navigator.clipboard.writeText(link);notify('Private watch link copied')};
  } catch(error) { notify(error.message,true); }
}

async function watchPage(token) {
  clearInterval(state.watchInterval);
  let details;
  try { details=await api(`/api/watch/${encodeURIComponent(token)}`); } catch(error) { app.innerHTML=`<div class="watch-page"><div class="watch-error">${logo()}<h1>Watch room unavailable</h1><p>${esc(error.message)}</p><a class="btn btn-dark" href="/">Return home</a></div></div>`;return; }
  const savedKey=localStorage.getItem(`watch-key-${token}`), savedName=localStorage.getItem(`watch-name-${token}`);
  if (!savedKey || !savedName) return watchJoinScreen(token,details);
  await api(`/api/watch/${encodeURIComponent(token)}/join`,{method:'POST',body:JSON.stringify({viewer_key:savedKey,name:savedName})});
  renderWatchRoom(token,details,savedKey,savedName);
}

function watchJoinScreen(token, details) {
  app.innerHTML=`<div class="watch-page"><div class="watch-join">${logo()}<div class="watch-lock">Private family room</div><h1>Stay close from anywhere.</h1><p>${esc(details.hospital)} · ${esc(details.ward_room)}</p><form><div class="field"><label>Your name</label><input name="name" placeholder="e.g. Anjali · Daughter" maxlength="50" required></div><button class="btn btn-primary btn-block">Join live watch</button></form><small>Only join if this link was shared with you by the patient's family.</small></div></div>`;
  app.querySelector('form').onsubmit=async e=>{e.preventDefault();const name=new FormData(e.target).get('name');const result=await api(`/api/watch/${encodeURIComponent(token)}/join`,{method:'POST',body:JSON.stringify({name})});localStorage.setItem(`watch-key-${token}`,result.viewer_key);localStorage.setItem(`watch-name-${token}`,name);await watchPage(token)};
}

function renderWatchRoom(token, details, viewerKey, viewerName) {
  const elapsed=details.started_at?`<strong class="shift-timer" data-started="${esc(details.started_at)}">00:00:00</strong>`:'<strong>Not started</strong>';
  app.innerHTML=`<div class="watch-page"><header class="watch-nav">${logo()}<span><i></i> Private live watch</span></header><main class="watch-container"><div class="watch-heading"><div><span class="eyebrow">Family care room</span><h1>${esc(details.patient_name)}</h1><p>${esc(details.hospital)} · ${esc(details.city)} · ${esc(details.ward_room)}</p></div><span class="status status-${details.status}">${titleCase(details.status)}</span></div><div class="watch-grid"><section class="watch-main-card"><div class="watch-status"><span class="live-dot"></span><div><small>Shift timer</small>${elapsed}</div></div><div class="assigned-saathi"><div class="caretaker-avatar">${details.caretaker_name?esc(details.caretaker_name.split(' ').map(x=>x[0]).join('')):'—'}</div><div><small>Assigned CareSathi</small><h3>${esc(details.caretaker_name||'Waiting for acceptance')}</h3><p>${details.caretaker_badge?`${details.caretaker_credential_verified?'✓ ':''}${esc(details.caretaker_badge)} · ★ ${details.caretaker_rating}`:'Assignment pending'}</p></div></div><div class="watch-detail-row"><span>Specialized need<strong>${esc(details.skill_needed)}</strong></span><span>Ward / room<strong>${esc(details.ward_room)}</strong></span></div></section><aside><div class="viewer-panel"><h3>Watching now <span>${details.viewers.length}</span></h3><div class="viewer-list">${details.viewers.map(v=>`<span><b>${esc(v.name.slice(0,1).toUpperCase())}</b>${esc(v.name)}</span>`).join('')||'<small>No other viewers connected</small>'}</div></div><div class="emergency-panel"><h3>Urgent numbers</h3>${details.emergency_numbers.map(n=>`<a href="tel:${n.number}"><span>${esc(n.label)}</span><strong>${n.number}</strong></a>`).join('')}<small>For ward-specific help, contact the hospital nursing station.</small></div></aside></div></main></div>`;
  updateTimers();clearInterval(state.watchInterval);state.watchInterval=setInterval(async()=>{try{await api(`/api/watch/${encodeURIComponent(token)}/join`,{method:'POST',body:JSON.stringify({viewer_key:viewerKey,name:viewerName})});const fresh=await api(`/api/watch/${encodeURIComponent(token)}`);renderWatchRoom(token,fresh,viewerKey,viewerName)}catch{}},15000);
}

async function performAction(id, action, body = {}, refresh = true) {
  const labels={accept:'Request accepted — start OTP sent to the family',start:'Shift started',complete:'Shift completed',cancel:'Request cancelled',release:'Request released to other CareSathis',request_end:'Caretaker notified to end the shift'};
  const result = await api(`/api/requests/${id}/${action}`,{method:'POST',body:JSON.stringify(body)});
  if (refresh) { notify(labels[action]); await dashboard(); }
  return result;
}

async function boot() {
  const watchToken=new URLSearchParams(location.search).get('watch');
  if (watchToken) return watchPage(watchToken);
  try { const data=await api('/api/me'); state.user=data.user; state.user ? dashboard() : landing(); } catch { landing(); }
}

boot();
