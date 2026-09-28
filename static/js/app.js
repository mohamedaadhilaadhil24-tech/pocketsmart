/* PocketSmart AI — application scripts */

/* ---------- feedback ---------- */

function toast(message, isError = false) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = message;
  el.classList.toggle("error", isError);
  el.classList.add("show");
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), 3200);
}

function setLoading(show) {
  const el = document.getElementById("loading");
  if (el) el.classList.toggle("show", show);
  document.querySelectorAll(".btn-submit").forEach((b) => (b.disabled = show));
}

function skeleton(containerId, count = 4) {
  const box = document.getElementById(containerId);
  if (!box) return;
  box.innerHTML = Array.from({ length: count }, () => '<div class="skeleton"></div>').join("");
}

/* ---------- api ---------- */

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    credentials: "same-origin",
    ...options,
  });
  let data = null;
  try { data = await res.json(); } catch (_) { /* empty body */ }
  if (!res.ok) {
    const detail = data && data.detail;
    const msg = typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? detail.map((d) => d.msg).join(", ")
        : `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

/* ---------- auth ---------- */

function bindAuthForms() {
  const registerForm = document.getElementById("register-form");
  if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      setLoading(true);
      try {
        await api("/register", {
          method: "POST",
          body: JSON.stringify({
            username: registerForm.username.value.trim(),
            email: registerForm.email.value.trim(),
            password: registerForm.password.value,
          }),
        });
        toast("Account created");
        setTimeout(() => (window.location.href = "/dashboard"), 450);
      } catch (err) { toast(err.message, true); }
      finally { setLoading(false); }
    });
  }

  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      setLoading(true);
      try {
        await api("/login", {
          method: "POST",
          body: JSON.stringify({
            username: loginForm.username.value.trim(),
            password: loginForm.password.value,
          }),
        });
        toast("Signed in");
        setTimeout(() => (window.location.href = "/dashboard"), 400);
      } catch (err) { toast(err.message, true); }
      finally { setLoading(false); }
    });
  }

  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try { await api("/logout", { method: "POST" }); } catch (_) {}
      window.location.href = "/";
    });
  }
}

/* ---------- formatting ---------- */

const fmt = (n) =>
  "₹" + Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 });

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}
const escapeAttr = escapeHtml;

/* ---------- results ---------- */

function renderResults(containerId, data) {
  const box = document.getElementById(containerId);
  if (!box) return;

  const total = data.items.reduce((s, i) => s + Number(i.price || 0), 0);
  const within = total <= data.budget;
  const pct = data.budget > 0 ? Math.round((total / data.budget) * 100) : 0;
  const badge = data.source === "gemini"
    ? '<span class="badge badge-gemini">Gemini</span>'
    : '<span class="badge badge-fallback">Fallback</span>';

  box.innerHTML = `
    <div class="result-summary">
      <div class="head">
        ${badge}
        <span class="badge badge-cat">${escapeHtml(data.domain)}</span>
      </div>
      <p class="lead">${escapeHtml(data.summary || "")}</p>
      <p class="meta">
        budget ${fmt(data.budget)} &nbsp;·&nbsp; ${data.items.length} items
        &nbsp;·&nbsp; <span class="${within ? "ok" : "over"}">${within ? "within budget" : "over budget"}</span>
      </p>
      <div class="bar" aria-hidden="true">
        <span class="${within ? "" : "over"}" style="width:${Math.min(pct, 100)}%"></span>
      </div>
      <div class="bar-cap"><span>${pct}% of budget used</span><span class="amt">${fmt(total)}</span></div>
    </div>
    <div id="items-list"></div>
    <div class="total-bar">
      <span>Total allocated</span>
      <span class="amt">${fmt(total)}</span>
    </div>
  `;

  const list = box.querySelector("#items-list");
  data.items.forEach((item, i) => {
    const el = document.createElement("div");
    el.className = "item-card";
    el.style.animationDelay = `${i * 70}ms`;
    el.innerHTML = `
      <div class="body">
        <div class="idx">${String(i + 1).padStart(2, "0")}</div>
        <div>
          <h4>${escapeHtml(item.name)}</h4>
          <div class="why">${escapeHtml(item.rationale || "")}</div>
          <div class="meta">
            <span class="pill cat-${escapeAttr(item.category)}"><span class="dotc"></span>${escapeHtml(item.category)}</span>
            <span class="pill plat">${escapeHtml(item.platform)}</span>
            ${item.url ? `<a href="${escapeAttr(item.url)}" target="_blank" rel="noopener">Open ↗</a>` : ""}
          </div>
        </div>
      </div>
      <div class="price">${fmt(item.price)}</div>
    `;
    list.appendChild(el);
  });

  box.scrollIntoView({ behavior: "smooth", block: "start" });
}

function bindPlanner(formId, endpoint, buildPayload, resultId = "results") {
  const form = document.getElementById(formId);
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    setLoading(true);
    skeleton(resultId);
    try {
      const payload = buildPayload(form);
      const data = await api(endpoint, { method: "POST", body: JSON.stringify(payload) });
      renderResults(resultId, data);
      toast("Recommendations generated");
    } catch (err) {
      document.getElementById(resultId).innerHTML = "";
      toast(err.message, true);
    } finally {
      setLoading(false);
    }
  });
}

/* ---------- item rows ---------- */

function initItemRows() {
  const wrap = document.getElementById("item-rows");
  if (!wrap) return;

  wrap.addEventListener("click", (e) => {
    if (e.target.classList.contains("remove-item")) {
      e.target.closest(".item-row")?.remove();
    }
  });

  document.getElementById("add-item")?.addEventListener("click", () => {
    const row = document.createElement("div");
    row.className = "item-row";
    row.innerHTML = `
      <input type="text" name="item-name" placeholder="Item name" />
      <input type="number" name="item-qty" min="1" value="1" aria-label="Quantity" />
      <button type="button" class="btn btn-ghost remove-item" aria-label="Remove">×</button>`;
    wrap.appendChild(row);
    row.querySelector("input").focus();
  });
}

/* ---------- dotted activity grid (reference calendar) ---------- */
function initDots() {
  document.querySelectorAll(".dots-grid").forEach((grid) => {
    if (grid.childElementCount) return;
    const total = 105; // 3 months × 7 cols × 5 rows
    const activity = Number(grid.dataset.activity || 0);
    const seed = (Date.now() / 86400000) | 0;
    const lit = Math.min(2 + activity * 2, 26);

    // deterministic pseudo-random picks
    const picks = new Set();
    let s = seed + 7;
    while (picks.size < lit) {
      s = (s * 1103515245 + 12345) & 0x7fffffff;
      picks.add(s % total);
    }

    const frag = document.createDocumentFragment();
    for (let i = 0; i < total; i++) {
      const dot = document.createElement("i");
      if (picks.has(i)) dot.className = "on";
      else if (i % 7 === 3) dot.className = "dim";
      frag.appendChild(dot);
    }
    grid.appendChild(frag);
  });
}

/* ---------- motion ---------- */

function initProgress() {
  const bar = document.getElementById("progress");
  if (!bar) return;
  const update = () => {
    const h = document.documentElement.scrollHeight - window.innerHeight;
    bar.style.width = h > 0 ? (window.scrollY / h) * 100 + "%" : "0%";
  };
  update();
  window.addEventListener("scroll", update, { passive: true });
  window.addEventListener("resize", update);
}

function initCardGlow() {
  document.querySelectorAll(".card, .process .step, .stat").forEach((el) => {
    el.addEventListener("pointermove", (e) => {
      const r = el.getBoundingClientRect();
      el.style.setProperty("--mx", `${e.clientX - r.left}px`);
      el.style.setProperty("--my", `${e.clientY - r.top}px`);
    });
  });
}

/* ---------- sidebar (mobile drawer) ---------- */
function initSidebar() {
  const sidebar = document.getElementById("sidebar");
  const burger = document.getElementById("burger");
  const scrim = document.getElementById("scrim");
  if (!sidebar) return;

  const setOpen = (open) => {
    sidebar.classList.toggle("open", open);
    if (scrim) scrim.classList.toggle("show", open);
    document.body.classList.toggle("nav-open", open);
  };
  const close = () => setOpen(false);

  burger?.addEventListener("click", () => setOpen(!sidebar.classList.contains("open")));
  scrim?.addEventListener("click", close);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
  sidebar.querySelectorAll("a").forEach((a) => a.addEventListener("click", close));
  window.addEventListener("resize", () => { if (window.innerWidth > 980) close(); });
}

/* ---------- hero cursor spotlight ---------- */
function initSpotlight() {
  document.querySelectorAll(".hero-band").forEach((hero) => {
    const spot = hero.querySelector(".spot");
    if (!spot) return;
    let raf = null, tx = 0, ty = 0, cx = 0, cy = 0;

    const loop = () => {
      cx += (tx - cx) * 0.14;
      cy += (ty - cy) * 0.14;
      spot.style.transform = `translate3d(${cx}px, ${cy}px, 0)`;
      raf = requestAnimationFrame(loop);
    };

    hero.addEventListener("pointermove", (e) => {
      const r = hero.getBoundingClientRect();
      tx = e.clientX - r.left;
      ty = e.clientY - r.top;
      if (!raf) { cx = tx; cy = ty; raf = requestAnimationFrame(loop); }
    });
    hero.addEventListener("pointerleave", () => {
      cancelAnimationFrame(raf);
      raf = null;
    });
  });
}

/* ---------- 3D tilt on preview tiles ---------- */
function initTilt() {
  const max = 9;
  document.querySelectorAll(".tilt").forEach((el) => {
    let raf = null, tX = 0, tY = 0, cX = 0, cY = 0;

    const loop = () => {
      cX += (tX - cX) * 0.16;
      cY += (tY - cY) * 0.16;
      el.style.transform = `perspective(760px) rotateX(${cY}deg) rotateY(${cX}deg) translateZ(0)`;
      if (Math.abs(tX - cX) > 0.01 || Math.abs(tY - cY) > 0.01) {
        raf = requestAnimationFrame(loop);
      } else { raf = null; }
    };
    const kick = () => { if (!raf) raf = requestAnimationFrame(loop); };

    el.addEventListener("pointermove", (e) => {
      const r = el.getBoundingClientRect();
      tX = ((e.clientX - r.left) / r.width - 0.5) * max;
      tY = -((e.clientY - r.top) / r.height - 0.5) * max;
      kick();
    });
    el.addEventListener("pointerleave", () => { tX = 0; tY = 0; kick(); });
  });
}

/* ---------- magnetic buttons ---------- */
function initMagnetic() {
  document.querySelectorAll(".magnetic").forEach((el) => {
    let raf = null, tX = 0, tY = 0, cX = 0, cY = 0;
    const strength = 0.28;

    const loop = () => {
      cX += (tX - cX) * 0.18;
      cY += (tY - cY) * 0.18;
      el.style.transform = `translate3d(${cX}px, ${cY}px, 0)`;
      if (Math.abs(tX - cX) > 0.05 || Math.abs(tY - cY) > 0.05) {
        raf = requestAnimationFrame(loop);
      } else { raf = null; }
    };
    const kick = () => { if (!raf) raf = requestAnimationFrame(loop); };

    el.addEventListener("pointermove", (e) => {
      const r = el.getBoundingClientRect();
      tX = (e.clientX - r.left - r.width / 2) * strength;
      tY = (e.clientY - r.top - r.height / 2) * strength;
      kick();
    });
    el.addEventListener("pointerleave", () => { tX = 0; tY = 0; kick(); });
  });
}

/* ---------- background parallax (mouse depth) ---------- */
function initParallax() {
  const field = document.querySelector(".bg-field");
  const grid = document.querySelector(".bg-grid");
  if (!field) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  let raf = null, mx = 0, my = 0, px = 0, py = 0;
  const loop = () => {
    px += (mx - px) * 0.06;
    py += (my - py) * 0.06;
    field.style.transform = `translate3d(${px}px, ${py}px, 0)`;
    if (grid) grid.style.transform = `translate3d(${px * 0.4}px, ${py * 0.4}px, 0)`;
    raf = requestAnimationFrame(loop);
  };

  window.addEventListener("pointermove", (e) => {
    mx = (e.clientX / window.innerWidth - 0.5) * -34;
    my = (e.clientY / window.innerHeight - 0.5) * -22;
    if (!raf) raf = requestAnimationFrame(loop);
  }, { passive: true });
}

function initReveal() {
  const els = document.querySelectorAll(".reveal");
  if (!els.length) return;
  if (!("IntersectionObserver" in window)) {
    els.forEach((el) => el.classList.add("in"));
    return;
  }
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      io.unobserve(entry.target);
      entry.target.classList.add("in");
    });
  }, { threshold: 0.1, rootMargin: "0px 0px -40px 0px" });

  // stagger siblings that share a parent (grid / process / stats)
  const groups = new Map();
  els.forEach((el) => {
    const p = el.parentElement;
    if (!groups.has(p)) groups.set(p, []);
    groups.get(p).push(el);
  });
  groups.forEach((list) => {
    if (list.length > 1) list.forEach((el, i) => (el.style.transitionDelay = `${i * 70}ms`));
  });

  els.forEach((el) => io.observe(el));
}

function initCounters() {
  const nums = document.querySelectorAll("[data-count]");
  if (!nums.length) return;
  if (!("IntersectionObserver" in window)) {
    nums.forEach((n) => {
      const s = n.dataset.suffix || "";
      n.innerHTML = n.dataset.count + (s ? `<span class="sfx">${s}</span>` : "");
    });
    return;
  }
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      io.unobserve(el);
      const target = Number(el.dataset.count);
      const suffix = el.dataset.suffix || "";
      const dur = 1100;
      const start = performance.now();
      const tick = (now) => {
        const p = Math.min((now - start) / dur, 1);
        const eased = 1 - Math.pow(1 - p, 3);
        el.innerHTML = Math.round(target * eased) +
          (suffix ? `<span class="sfx">${suffix}</span>` : "");
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
  }, { threshold: 0.5 });
  nums.forEach((n) => io.observe(n));
}

document.addEventListener("DOMContentLoaded", () => {
  initSidebar();
  bindAuthForms();
  initItemRows();
  initReveal();
  initCounters();
  initDots();
  initProgress();
  initCardGlow();
  initSpotlight();
  initTilt();
  initMagnetic();
  initParallax();
});
