/* ══════════════════════════════════════════════
   DRAG AND DROP / PYWEBVIEW BRIDGE
══════════════════════════════════════════════ */
let D = {};

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const fileName = document.getElementById('file-name');
const dropText = document.getElementById('drop-text');
const pwdInput = document.getElementById('pdf-password');
const analyzeBtn = document.getElementById('analyze-btn');
const spinner = document.getElementById('analyze-spinner');
const btnText = document.getElementById('analyze-text');
const errorMsg = document.getElementById('error-msg');

let selectedFile = null;

// File Selection Handlers
dropZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => handleFile(e.target.files[0]));
dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
  e.preventDefault(); dropZone.classList.remove('dragover');
  if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});

function handleFile(file) {
  if (!file) return;
  selectedFile = file;
  dropText.style.display = 'none';
  fileName.textContent = file.name;
  fileName.style.display = 'block';
  checkForm();
}

pwdInput.addEventListener('input', checkForm);

function checkForm() {
  analyzeBtn.disabled = !(selectedFile && pwdInput.value.length > 0);
}

analyzeBtn.addEventListener('click', async () => {
  if (!selectedFile) return;
  
  errorMsg.style.display = 'none';
  spinner.style.display = 'block';
  btnText.textContent = 'Processing...';
  analyzeBtn.disabled = true;
  
  try {
    const reader = new FileReader();
    reader.onload = async (e) => {
      // Get base64 string without the data URI prefix
      const b64_data = e.target.result.split(',')[1];
      const pwd = pwdInput.value;
      
      // Call Python backend via pywebview
      const response = await window.pywebview.api.analyze_pdf(b64_data, pwd);
      
      if (response.success) {
        document.getElementById('upload-screen').style.display = 'none';
        document.getElementById('dashboard-app').style.display = 'flex';
        initDashboard(response.data);
      } else {
        showError(response.error || "Failed to parse PDF.");
      }
    };
    reader.readAsDataURL(selectedFile);
  } catch (err) {
    showError("An unexpected error occurred.");
  }
});

function showError(msg) {
  errorMsg.textContent = msg;
  errorMsg.style.display = 'block';
  spinner.style.display = 'none';
  btnText.textContent = 'Analyze';
  analyzeBtn.disabled = false;
}

/* ══════════════════════════════════════════════
   DATA & HELPERS
══════════════════════════════════════════════ */
const fmt = n => Number(n || 0).toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtS = n => { n = Number(n || 0); if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M'; if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'; return n.toFixed(0); };
const cls = (el, on, ...off) => { el.classList.add(on); off.forEach(c => el.classList.remove(c)); };

function initDashboard(data) {
  D = data;
  
  // Meta
  document.getElementById('meta-period').textContent = D.meta.statement_period;
  document.getElementById('tx-count-badge').textContent = D.kpis.tx_count.toLocaleString() + ' transactions';
/* ── NAV ── */
function go(id, btn) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('s-' + id).classList.add('active');
  btn.classList.add('active');
}

/* ════════════════════════════════════════════════════════════════════════
    CHART DEFAULTS
═══════════════════════════════════════════════════════════════════════ */
Chart.defaults.color = '#6C757D';
Chart.defaults.borderColor = 'rgba(0,0,0,0.06)';
Chart.defaults.font.family = "'DM Sans', sans-serif";
Chart.defaults.plugins.tooltip.backgroundColor = '#212529';
Chart.defaults.plugins.tooltip.borderColor = 'rgba(255,255,255,0.1)';
Chart.defaults.plugins.tooltip.borderWidth = 1;
Chart.defaults.plugins.tooltip.padding = 12;
Chart.defaults.plugins.tooltip.titleFont = { family: "'JetBrains Mono',monospace", size: 10 };
Chart.defaults.plugins.tooltip.bodyFont = { family: "'DM Sans',sans-serif", size: 12 };

const PAL = ['#EE3540', '#FFD700', '#10B981', '#3B82F6', '#8B5CF6', '#F59E0B', '#06B6D4', '#84CC16', '#EC4899', '#6366F1'];

/* ══════════════════════════════════════════════
   KPI CARDS
══════════════════════════════════════════════ */
const k = D.kpis;
const kpis = [
  { l: 'Total Received', v: 'KES ' + fmt(k.total_in), s: D.meta.statement_period, vc: 'var(--green)', acc: 'var(--green)' },
  { l: 'Total Spent', v: 'KES ' + fmt(k.total_out), s: 'Withdrawals + payments', vc: 'var(--red)', acc: 'var(--red)' },
  { l: 'Net Flow', v: 'KES ' + fmt(k.net), s: k.net >= 0 ? '▲ Surplus' : '▼ Deficit', vc: k.net >= 0 ? 'var(--green)' : 'var(--red)', acc: k.net >= 0 ? 'var(--green)' : 'var(--red)' },
  { l: 'Transactions', v: k.tx_count.toLocaleString(), s: 'Unique receipts', vc: 'var(--blue)', acc: 'var(--blue)' },
  { l: 'Fees Paid', v: 'KES ' + fmt(k.total_fees), s: 'Transaction costs', vc: 'var(--gold)', acc: 'var(--gold)' },
  { l: 'Largest Receive', v: 'KES ' + fmt(k.biggest_in), s: 'Single transaction', vc: 'var(--green)', acc: 'var(--green)' },
  { l: 'Largest Payment', v: 'KES ' + fmt(k.biggest_out), s: 'Single transaction', vc: 'var(--red)', acc: 'var(--red)' },
  { l: 'Avg. Spend', v: 'KES ' + fmt(k.avg_spend), s: 'Per outgoing transaction', vc: 'var(--gold)', acc: 'var(--gold)' },
  { l: 'Avg. Receive', v: 'KES ' + fmt(k.avg_receive), s: 'Per incoming transaction', vc: 'var(--green)', acc: 'var(--green)' },
  { l: 'Closing Balance', v: 'KES ' + fmt(k.closing_balance), s: 'As of last transaction', vc: 'var(--blue)', acc: 'var(--blue)' },
];
const grid = document.getElementById('kpi-grid');
kpis.forEach((c, i) => {
  const el = document.createElement('div');
  el.className = `kpi su d${Math.min(i + 1, 6)}`;
  el.style.setProperty('--accent', c.acc);

  let trend = '';
  if (c.l === 'Net Flow') {
    trend = k.net > 0 ? '↑' : '↓';
  }

  el.innerHTML = `
    <div class="kpi-header">
      <span class="kpi-label">${c.l}</span>
      ${trend ? `<span class="kpi-trend" style="color:${c.vc}">${trend}</span>` : ''}
    </div>
    <div class="kpi-value" style="color:${c.vc}">${c.v}</div>
    <div class="kpi-sub">${c.s}</div>
  `;
  grid.appendChild(el);
});

/* ══════════════════════════════════════════════
   MONTHLY CHART
══════════════════════════════════════════════ */
const months = D.monthly.map(r => r.month || r.month_key);
document.getElementById('month-ct').textContent = months.length + ' months';
document.getElementById('bal-ct').textContent = D.balance_series.length + ' data points';
new Chart(document.getElementById('monthlyChart'), {
  type: 'bar',
  data: {
    labels: months, datasets: [
      { label: 'Income', data: D.monthly.map(r => r.total_in), backgroundColor: 'rgba(0,232,122,.75)', borderRadius: 5, borderSkipped: false },
      { label: 'Spending', data: D.monthly.map(r => r.total_out), backgroundColor: 'rgba(255,71,87,.75)', borderRadius: 5, borderSkipped: false },
    ]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top', labels: { usePointStyle: true, padding: 14, font: { size: 11 } } },
      tooltip: { callbacks: { label: ctx => ' KES ' + fmt(ctx.raw) } }
    },
    scales: {
      x: { grid: { display: false }, ticks: { maxRotation: 45, font: { size: 10 } } },
      y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { callback: v => 'KES ' + fmtS(v), font: { size: 10 } } }
    }
  }
});

/* ══════════════════════════════════════════════
   DONUT CHART (fixed height container)
══════════════════════════════════════════════ */
let donutC;
function buildDonut(type) {
  const src = type === 'out' ? D.cat_out : D.cat_in;
  const labels = src.map(r => r.category), values = src.map(r => r.total);
  if (donutC) donutC.destroy();
  donutC = new Chart(document.getElementById('donutChart'), {
    type: 'doughnut',
    data: { labels, datasets: [{ data: values, backgroundColor: PAL, borderWidth: 2, borderColor: '#0c1220', hoverOffset: 6 }] },
    options: {
      responsive: true, maintainAspectRatio: false, cutout: '63%',
      plugins: {
        legend: { position: 'right', labels: { usePointStyle: true, padding: 8, font: { size: 10 }, boxWidth: 10 } },
        tooltip: {
          callbacks: {
            label: ctx => {
              const tot = values.reduce((a, b) => a + b, 0);
              return ` KES ${fmt(ctx.raw)}  (${((ctx.raw / tot) * 100).toFixed(1)}%)`;
            }
          }
        }
      }
    }
  });
}
buildDonut('out');
function switchDonut(type, btn) {
  document.querySelectorAll('#s-overview .itab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  buildDonut(type);
}

/* ══════════════════════════════════════════════
   BALANCE LINE — all transactions, no sampling
══════════════════════════════════════════════ */
new Chart(document.getElementById('balanceChart'), {
  type: 'line',
  data: {
    labels: D.balance_series.map(r => r.date_str),
    datasets: [{
      label: 'Balance', data: D.balance_series.map(r => r.balance),
      borderColor: '#3d8bff',
      backgroundColor: ctx => {
        const g = ctx.chart.ctx.createLinearGradient(0, 0, 0, 160);
        g.addColorStop(0, 'rgba(61,139,255,0.18)'); g.addColorStop(1, 'rgba(61,139,255,0)');
        return g;
      },
      fill: true, tension: .25, pointRadius: 0, pointHoverRadius: 4, borderWidth: 2,
    }]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: { display: false }, tooltip: {
        mode: 'index', intersect: false,
        callbacks: { label: ctx => ' Balance: KES ' + fmt(ctx.raw) }
      }
    },
    scales: {
      x: { display: false },
      y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { callback: v => 'KES ' + fmtS(v), font: { size: 10 } } }
    }
  }
});

/* ══════════════════════════════════════════════
   TOP RECIPIENTS & SENDERS
══════════════════════════════════════════════ */
function renderHBars(containerId, data, color, prefix = '-') {
  const el = document.getElementById(containerId);
  if (!data.length) { el.innerHTML = '<div style="color:var(--text-muted);font-size:11px;padding:10px 0;">No data extracted — names may not match M-Pesa patterns</div>'; return; }
  const max = data[0].total;
  el.innerHTML = '';
  data.forEach((r, i) => {
    const pct = ((r.total / max) * 100).toFixed(1);
    el.innerHTML += `<div class="hbar-row">
      <span class="hbar-rank">${i + 1}</span>
      <span class="hbar-name" title="${r.person}">${r.person}</span>
      <div class="hbar-track"><div class="hbar-fill" style="background:${color}" data-w="${pct}"></div></div>
      <span class="hbar-val" style="color:${color}">${prefix}KES ${fmtS(r.total)}</span>
      <span class="hbar-cnt">${r.count}×</span>
    </div>`;
  });
  // Animate after paint
  setTimeout(() => el.querySelectorAll('.hbar-fill').forEach(f => f.style.width = f.dataset.w + '%'), 50);
}
renderHBars('top-recipients', D.top_recipients, 'var(--red)', '−');
renderHBars('top-senders', D.top_senders, 'var(--green)', '+');

/* ══════════════════════════════════════════════
   DAY OF WEEK
══════════════════════════════════════════════ */
const dowEl = document.getElementById('dow-grid');
const maxDow = Math.max(...D.dow.map(r => r.spent), 1);
D.dow.forEach(r => {
  const pct = ((r.spent / maxDow) * 100).toFixed(1);
  const row = document.createElement('div');
  row.className = 'dow-r';
  row.innerHTML = `<span class="dow-lbl">${(r.day || '').slice(0, 3).toUpperCase()}</span>
    <div class="dow-track"><div class="dow-fill" style="background:linear-gradient(90deg,#005c33,var(--green))" data-w="${pct}"></div></div>
    <span class="dow-val">KES ${fmtS(r.spent)} · ${r.count}×</span>`;
  dowEl.appendChild(row);
});
setTimeout(() => document.querySelectorAll('.dow-fill').forEach(f => f.style.width = f.dataset.w + '%'), 100);

/* ══════════════════════════════════════════════
   HOURLY HEATMAP
══════════════════════════════════════════════ */
const hmEl = document.getElementById('hm-wrap');
const hourMap = {};
D.hourly.forEach(r => hourMap[r.hour] = r);
const maxHour = Math.max(...D.hourly.map(r => r.spent), 1);
for (let h = 0; h < 24; h++) {
  const row = hourMap[h] || { spent: 0, count: 0 };
  const intensity = row.spent / maxHour;
  const cell = document.createElement('div');
  cell.className = 'hm-cell';
  const alpha = intensity > 0 ? (0.08 + intensity * 0.72) : 0.04;
  cell.style.background = `rgba(255,71,87,${alpha.toFixed(2)})`;
  const label = h === 0 ? '12am' : h < 12 ? h + 'am' : h === 12 ? '12pm' : (h - 12) + 'pm';
  cell.innerHTML = `<span>${label}</span>
    <div class="hm-tip">${label}<br>KES ${fmt(row.spent)}<br>${row.count} transactions</div>`;
  hmEl.appendChild(cell);
}

/* ══════════════════════════════════════════════
   CATEGORY CHARTS
══════════════════════════════════════════════ */
new Chart(document.getElementById('catChart'), {
  type: 'bar',
  data: {
    labels: D.cat_out.map(r => r.category),
    datasets: [{ label: 'Spent', data: D.cat_out.map(r => r.total), backgroundColor: PAL, borderRadius: 5, borderSkipped: false }]
  },
  options: {
    indexAxis: 'y', responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ` KES ${fmt(ctx.raw)} (${D.cat_out[ctx.dataIndex]?.pct || 0}%)` } } },
    scales: {
      x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { callback: v => 'KES ' + fmtS(v), font: { size: 9 } } },
      y: { grid: { display: false }, ticks: { font: { size: 10 } } }
    }
  }
});

// Net flow bar
function buildNetChart(canvasId) {
  return new Chart(document.getElementById(canvasId), {
    type: 'bar',
    data: {
      labels: D.monthly.map(r => r.month || r.month_key),
      datasets: [{
        label: 'Net',
        data: D.monthly.map(r => r.net || r.total_in - r.total_out),
        backgroundColor: D.monthly.map(r => (r.net || r.total_in - r.total_out) >= 0 ? 'rgba(0,232,122,.75)' : 'rgba(255,71,87,.75)'),
        borderRadius: 4, borderSkipped: false
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ' KES ' + fmt(ctx.raw) } } },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 9 }, maxRotation: 45 } },
        y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { callback: v => 'KES ' + fmtS(v), font: { size: 9 } } }
      }
    }
  });
}
buildNetChart('netChart');

/* ══════════════════════════════════════════════
   PEOPLE
══════════════════════════════════════════════ */
const peopleArr = Object.values(D.people);
document.getElementById('pcount-lbl').textContent = peopleArr.length + ' People';
let pSortMode = 'total', pSelected = null;
let pFiltered = [...peopleArr];

const AV_COLORS = [
  ['#00e87a', '#000'], ['#3d8bff', '#000'], ['#ffcc00', '#000'],
  ['#ff4757', '#fff'], ['#a855f7', '#fff'], ['#ff8c00', '#000'],
];
function avColor(name) {
  let h = 0; for (let c of name) h = (h * 31 + c.charCodeAt(0)) & 0xfffff;
  return AV_COLORS[h % AV_COLORS.length];
}
function avInitials(name) { return name.split(' ').map(w => w[0] || '').join('').slice(0, 2).toUpperCase(); }

function psort(mode, btn) {
  pSortMode = mode;
  document.querySelectorAll('.psort-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  if (mode === 'sent') pFiltered.sort((a, b) => b.total_sent - a.total_sent);
  else if (mode === 'recv') pFiltered.sort((a, b) => b.total_received - a.total_received);
  else pFiltered.sort((a, b) => (b.total_sent + b.total_received) - (a.total_sent + a.total_received));
  renderPlist();
}

function pfilter() {
  const q = document.getElementById('psearch').value.toLowerCase();
  pFiltered = q ? peopleArr.filter(p => p.name.toLowerCase().includes(q)) : [...peopleArr];
  psort(pSortMode, document.querySelector('.psort-btn.active'));
}

let pChartRef = null;
function renderPlist() {
  const el = document.getElementById('plist');
  if (!pFiltered.length) { el.innerHTML = '<div style="padding:16px;text-align:center;color:var(--text-muted);font-size:11px;">No results</div>'; return; }
  el.innerHTML = '';
  pFiltered.forEach(p => {
    const [bg, fg] = avColor(p.name);
    const net = p.net; const nc = net >= 0 ? 'var(--green)' : 'var(--red)';
    const div = document.createElement('div');
    div.className = 'pitem' + (pSelected === p.name ? ' active' : '');
    div.dataset.name = p.name;
    div.innerHTML = `<div class="pav" style="background:${bg};color:${fg}">${avInitials(p.name)}</div>
      <div class="pinfo">
        <div class="pname">${p.name}</div>
        <div class="pmeta">${p.tx_count}tx · ${p.last_tx}</div>
      </div>
      <div class="pnet" style="color:${nc}">${net >= 0 ? '+' : ''}KES ${fmtS(Math.abs(net))}</div>`;
    div.onclick = () => showPerson(p.name);
    el.appendChild(div);
  });
}
psort('total', document.querySelector('.psort-btn.active'));

function showPerson(name) {
  pSelected = name;
  document.querySelectorAll('.pitem').forEach(el => el.classList.toggle('active', el.dataset.name === name));
  const p = D.people[name];
  if (!p) return;
  const [bg, fg] = avColor(name);
  const net = p.net; const nc = net >= 0 ? 'var(--green)' : 'var(--red)';

  // Monthly breakdown for this person
  const mmap = {};
  p.transactions.forEach(tx => {
    if (!tx.date) return;
    // Extract "Jan 2024" style
    const parts = tx.date.split(' ');
    if (parts.length >= 3) { const mk = parts[1] + ' ' + parts[2]; if (!mmap[mk]) mmap[mk] = { in: 0, out: 0 }; mmap[mk].in += tx.paid_in; mmap[mk].out += tx.withdrawn; }
  });
  const pm = Object.keys(mmap).sort((a, b) => new Date('1 ' + a) - new Date('1 ' + b));

  document.getElementById('pdetail').innerHTML = `
    <div class="pdetail-header">
      <div class="pdetail-av" style="background:${bg};color:${fg}">${avInitials(name)}</div>
      <div>
        <div class="pdetail-name">${name}</div>
        <div class="pdetail-since">First: ${p.first_tx} · Last: ${p.last_tx}</div>
      </div>
    </div>
    <div class="pstats">
      <div class="pstat"><div class="pstat-l">You Sent</div><div class="pstat-v" style="color:var(--red)">KES ${fmt(p.total_sent)}</div></div>
      <div class="pstat"><div class="pstat-l">You Received</div><div class="pstat-v" style="color:var(--green)">KES ${fmt(p.total_received)}</div></div>
      <div class="pstat"><div class="pstat-l">Net (you)</div><div class="pstat-v" style="color:${nc}">${net >= 0 ? '+' : ''}KES ${fmt(Math.abs(net))}</div></div>
    </div>
    ${pm.length > 1 ? `<div style="margin-bottom:14px"><div style="font-family:var(--font-display);font-size:10px;font-weight:700;color:var(--text-muted);letter-spacing:1px;text-transform:uppercase;margin-bottom:10px;">Monthly History with ${name.split(' ')[0]}</div><div class="ch" style="height:110px"><canvas id="pchart"></canvas></div></div>` : ''}
    <div>
      <div style="font-family:var(--font-display);font-size:10px;font-weight:700;color:var(--text-muted);letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;">All ${p.tx_count} Transactions</div>
      <div class="tscroll" style="max-height:240px">
        <table>
          <thead><tr><th>Date</th><th>Details</th><th>In</th><th>Out</th><th>Balance</th></tr></thead>
          <tbody>${p.transactions.map(tx => `<tr>
            <td class="mono-sm" style="white-space:nowrap">${tx.date}</td>
            <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px" title="${tx.details}">${tx.details}</td>
            <td class="in-v">${tx.paid_in > 0 ? fmt(tx.paid_in) : ''}</td>
            <td class="out-v">${tx.withdrawn > 0 ? fmt(tx.withdrawn) : ''}</td>
            <td class="mono-sm">${fmt(tx.balance)}</td>
          </tr>`).join('')}</tbody>
        </table>
      </div>
    </div>`;

  if (pm.length > 1) {
    setTimeout(() => {
      if (pChartRef) pChartRef.destroy();
      pChartRef = new Chart(document.getElementById('pchart'), {
        type: 'bar',
        data: {
          labels: pm, datasets: [
            { label: 'Received', data: pm.map(m => mmap[m].in), backgroundColor: 'rgba(0,232,122,.75)', borderRadius: 3, borderSkipped: false },
            { label: 'Sent', data: pm.map(m => mmap[m].out), backgroundColor: 'rgba(255,71,87,.75)', borderRadius: 3, borderSkipped: false },
          ]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { position: 'top', labels: { usePointStyle: true, padding: 8, font: { size: 9 } } }, tooltip: { callbacks: { label: ctx => ' KES ' + fmt(ctx.raw) } } },
          scales: { x: { grid: { display: false }, ticks: { font: { size: 9 }, maxRotation: 45 } }, y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { callback: v => 'KES ' + fmtS(v), font: { size: 9 } } } }
        }
      });
    }, 30);
  }
}

/* ══════════════════════════════════════════════
   TRANSACTIONS TABLE
══════════════════════════════════════════════ */
const allTx = D.all_tx;
document.getElementById('tx-total-ct').textContent = allTx.length.toLocaleString() + ' transactions';
let txCatFilter = null;

// Category filter buttons
const cats = [...new Set(allTx.map(r => r.category).filter(Boolean))].sort();
const frow = document.getElementById('tx-filters');
const allBtn = document.createElement('button');
allBtn.className = 'fbtn active'; allBtn.textContent = 'All';
allBtn.onclick = () => { txCatFilter = null; document.querySelectorAll('.fbtn').forEach(b => b.classList.remove('active')); allBtn.classList.add('active'); txFilter(); };
frow.appendChild(allBtn);
cats.forEach(cat => {
  const b = document.createElement('button'); b.className = 'fbtn'; b.textContent = cat;
  b.onclick = () => { txCatFilter = cat; document.querySelectorAll('.fbtn').forEach(x => x.classList.remove('active')); b.classList.add('active'); txFilter(); };
  frow.appendChild(b);
});

function txFilter() {
  const q = document.getElementById('txq').value.toLowerCase();
  let rows = allTx;
  if (txCatFilter) rows = rows.filter(r => r.category === txCatFilter);
  if (q) rows = rows.filter(r =>
    (r.details || '').toLowerCase().includes(q) ||
    (r.category || '').toLowerCase().includes(q) ||
    (r.receipt_no || '').toLowerCase().includes(q) ||
    (r.date_str || '').toLowerCase().includes(q) ||
    String(r.paid_in).includes(q) || String(r.withdrawn).includes(q)
  );
  renderTxTable(rows);
}

function renderTxTable(rows) {
  const shown = rows.slice(0, 1000);
  document.getElementById('tx-body').innerHTML = shown.map(r => `<tr>
    <td class="mono-sm" style="white-space:nowrap">${r.date_str || ''}</td>
    <td class="mono-sm">${r.receipt_no || ''}</td>
    <td style="max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px" title="${r.details || ''}">${r.details || ''}</td>
    <td><span class="cat-pill">${r.category || ''}</span></td>
    <td class="in-v">${r.paid_in > 0 ? fmt(r.paid_in) : ''}</td>
    <td class="out-v">${r.withdrawn > 0 ? fmt(r.withdrawn) : ''}</td>
    <td class="mono-sm">${fmt(r.balance || 0)}</td>
  </tr>`).join('');
  const totalIn = rows.reduce((a, r) => a + r.paid_in, 0);
  const totalOut = rows.reduce((a, r) => a + r.withdrawn, 0);
  document.getElementById('tx-showing').textContent = `Showing ${shown.length.toLocaleString()} of ${rows.length.toLocaleString()} transactions`;
  document.getElementById('tx-sum').textContent = `In: KES ${fmt(totalIn)} · Out: KES ${fmt(totalOut)}`;
}
txFilter();

/* ══════════════════════════════════════════════
   INSIGHTS PAGE
══════════════════════════════════════════════ */
const icards = [];
D.insights.forEach(ins => {
  if (ins.type === 'best_month') icards.push({ icon: '🏆', l: 'Best Month', v: ins.month, s: 'Net KES ' + fmt(ins.value), vc: 'var(--green)' });
  if (ins.type === 'worst_month') icards.push({ icon: '📉', l: 'Toughest Month', v: ins.month, s: 'Net KES ' + fmt(ins.value), vc: 'var(--red)' });
  if (ins.type === 'biggest_receive') icards.push({ icon: '💰', l: 'Biggest Single Receive', v: 'KES ' + fmt(ins.value), s: ins.date, vc: 'var(--green)' });
  if (ins.type === 'biggest_spend') icards.push({ icon: '💸', l: 'Biggest Single Spend', v: 'KES ' + fmt(ins.value), s: ins.date, vc: 'var(--red)' });
  if (ins.type === 'most_active_day') icards.push({ icon: '📅', l: 'Most Active Day', v: ins.day, s: ins.count + ' transactions', vc: 'var(--blue)' });
  if (ins.type === 'surplus_months') icards.push({ icon: '📊', l: 'Surplus Months', v: `${ins.value} / ${ins.total}`, s: 'Months you earned more than spent', vc: ins.value > ins.total / 2 ? 'var(--green)' : 'var(--red)' });
  if (ins.type === 'top_category') icards.push({ icon: '🏷', l: 'Top Spend Category', v: ins.category, s: `KES ${fmt(ins.value)} (${ins.pct}%)`, vc: 'var(--yellow)' });
  if (ins.type === 'people_count') icards.push({ icon: '👥', l: 'People Transacted With', v: ins.value.toLocaleString(), s: 'Unique counterparties found', vc: 'var(--purple)' });
});
const ig = document.getElementById('insight-grid');
icards.forEach(c => {
  ig.innerHTML += `<div class="icard"><div class="icard-icon">${c.icon}</div>
    <div><div class="icard-l">${c.l}</div>
    <div class="icard-v" style="--vc:${c.vc};color:var(--vc)">${c.v}</div>
    <div class="icard-s">${c.s}</div></div></div>`;
});

buildNetChart('netChart2');

new Chart(document.getElementById('catInChart'), {
  type: 'doughnut',
  data: { labels: D.cat_in.map(r => r.category), datasets: [{ data: D.cat_in.map(r => r.total), backgroundColor: PAL, borderWidth: 2, borderColor: '#0c1220', hoverOffset: 5 }] },
  options: {
    responsive: true, maintainAspectRatio: false, cutout: '60%',
    plugins: {
      legend: { position: 'right', labels: { usePointStyle: true, padding: 8, font: { size: 10 }, boxWidth: 10 } },
      tooltip: { callbacks: { label: ctx => ` KES ${fmt(ctx.raw)} (${D.cat_in[ctx.dataIndex]?.pct || 0}%)` } }
    }
  }
});

new Chart(document.getElementById('catOutBig'), {
  type: 'bar',
  data: {
    labels: D.cat_out.map(r => r.category), datasets: [
      { label: 'Amount Spent', data: D.cat_out.map(r => r.total), backgroundColor: PAL, borderRadius: 5, borderSkipped: false },
    ]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ` KES ${fmt(ctx.raw)}  ·  ${D.cat_out[ctx.dataIndex]?.pct || 0}%  ·  ${D.cat_out[ctx.dataIndex]?.count || 0} transactions` } } },
    scales: { x: { grid: { display: false }, ticks: { font: { size: 10 } } }, y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { callback: v => 'KES ' + fmtS(v), font: { size: 10 } } } }
  }
});

  // Expose global functions to window so HTML event handlers can reach them
  window.go = go;
  window.switchDonut = switchDonut;
  window.psort = psort;
  window.pfilter = pfilter;
  window.txFilter = txFilter;

} // end initDashboard