// main.js — 主流程：图片检测、批次概览与结果浏览。
import { predict, fetchConfig } from './api.js';
import { downloadCsv, teamName } from './exporter.js';
import { render, select, annotatedPng } from './renderer.js';
import { startCamera, stopCamera } from './camera.js';

const $ = s => document.querySelector(s);
let queue = [], results = [], current = -1;

const supported = f => /\.(jpg|jpeg|png|bmp)$/i.test(f.name);

// --------------------------------------------------------------------------- //
// 图片选择与检测
// --------------------------------------------------------------------------- //
function pick(files) {
  const valid = [...files].filter(supported);
  if (!valid.length) return alert('仅支持 JPG、JPEG、PNG、BMP 图片');
  queue = valid; results = []; current = -1;
  $('#detect-button').disabled = false;
  $('#export-button').disabled = true;
  $('#progress').max = valid.length; $('#progress').value = 0;
  $('#progress-text').textContent = `已选择 ${valid.length} 张图片，点击开始检测`;
  $('#analytics').className = 'analytics empty-analytics';
  $('#analytics').innerHTML = '<span>完成一批检测后，这里会显示批次概览</span>';
  $('#batch-list').innerHTML = valid.map((f, i) => `<button class="batch-row" data-index="${i}"><span class="file-name">${f.name}</span><em>待检测</em></button>`).join('');
}

async function run() {
  $('#detect-button').disabled = true;
  for (let i = 0; i < queue.length; i++) {
    $('#progress-text').textContent = `检测中 ${i + 1}/${queue.length}`;
    const row = document.querySelector(`[data-index="${i}"]`);
    try {
      const data = await predict(queue[i]);
      results[i] = { ...data, file: queue[i] };
      row.innerHTML = `<span>${data.image_id}</span><strong class="${data.status.toLowerCase()}">${data.status}</strong><em>${data.defect_count} 个缺陷 · ${data.inference_time_ms} ms</em>`;
    } catch (e) {
      results[i] = { image_id: queue[i].name, error: e.message, file: queue[i] };
      row.innerHTML = `<span>${queue[i].name}</span><em class="error">失败：${e.message}</em>`;
    }
    $('#progress').value = i + 1;
  }
  $('#progress-text').textContent = '批量检测完成';
  $('#export-button').disabled = !results.some(r => !r.error);
  const first = results.findIndex(r => !r.error);
  updateAnalytics();
  if (first >= 0) show(first);
}

// --------------------------------------------------------------------------- //
// 批次概览（BATCH INSIGHTS）
// --------------------------------------------------------------------------- //
function updateAnalytics() {
  const done = results.filter(r => r && !r.error);
  if (!done.length) return;
  const ng = done.filter(r => r.status === 'NG').length, ok = done.length - ng;
  const total = done.reduce((n, r) => n + r.defect_count, 0);
  const avg = done.reduce((n, r) => n + Number(r.inference_time_ms), 0) / done.length;
  const counts = {};
  done.flatMap(r => r.detections).forEach(d => counts[d.class_name_zh] = (counts[d.class_name_zh] || 0) + 1);
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const max = sorted[0]?.[1] || 1;
  $('#analytics').className = 'analytics';
  $('#analytics').innerHTML = `<div class="stat-card"><span>检测图片</span><strong>${done.length}</strong><small>已完成批次</small></div><div class="stat-card"><span>NG 图片</span><strong class="danger-text">${ng}</strong><small>NG 占比 ${Math.round(ng / done.length * 100)}%</small></div><div class="stat-card"><span>总缺陷数</span><strong>${total}</strong><small>平均 ${(total / done.length).toFixed(1)} / 张</small></div><div class="stat-card"><span>平均耗时</span><strong>${avg.toFixed(1)}<i> ms</i></strong><small>单张推理耗时</small></div><div class="distribution"><div class="distribution-head"><span>缺陷类别分布</span><b>${sorted.length ? sorted[0][0] : '无缺陷'}</b></div>${sorted.length ? sorted.map(([name, count]) => `<div class="bar-row"><span>${name}</span><div class="bar-track"><i style="width:${Math.max(8, count / max * 100)}%"></i></div><b>${count}</b></div>`).join('') : '<p class="muted">本批次未检出缺陷</p>'}</div>`;
}

// --------------------------------------------------------------------------- //
// 单图展示与浏览
// --------------------------------------------------------------------------- //
function show(i) {
  const item = results[i];
  if (!item || item.error) return;
  current = i;
  $('#empty-state').classList.add('hidden');
  $('#canvas-wrap').classList.remove('hidden');
  $('#save-image').classList.remove('hidden');
  $('#prev-image').classList.remove('hidden');
  $('#next-image').classList.remove('hidden');
  const order = browseOrder(); const position = order.indexOf(i);
  $('#image-counter').textContent = `${position + 1} / ${order.length}`;
  $('#prev-image').disabled = position <= 0;
  $('#next-image').disabled = position >= order.length - 1;
  render(item.file, item);
  $('#verdict').textContent = item.status;
  $('#verdict').className = `verdict ${item.status.toLowerCase()}`;
  $('#defect-count').textContent = item.defect_count;
  $('#infer-time').textContent = `${item.inference_time_ms} ms`;
  $('#image-meta').textContent = `${item.image_id} · 原图 ${item.shape[1]} × ${item.shape[0]} px`;
  document.querySelectorAll('.batch-row').forEach(x => x.classList.toggle('selected', +x.dataset.index === i));
  $('#detection-list').innerHTML = item.detections.length ? `<div class="detection-header"><span>类别</span><span>置信度</span></div>${item.detections.map((d, j) => { const level = d.confidence < 0.4 ? 'low' : d.confidence < 0.7 ? 'medium' : 'high'; const tone = ({ Hole: 'hole', Ink: 'ink', Broken_Filament: 'filament', Surface_Crack: 'crack' })[d.class_name] || 'default'; return `<button class="detection target-${tone}" data-det="${j}"><b>${d.class_name_zh}</b><span class="confidence-${level}">${d.confidence.toFixed(2)}</span><small>(${d.x_min}, ${d.y_min}) → (${d.x_max}, ${d.y_max}) px</small></button>`; }).join('')}` : '<p class="ok-message">未检出缺陷，判定为 OK。</p>';
  document.querySelectorAll('[data-det]').forEach(b => b.onclick = () => { select(+b.dataset.det); document.querySelectorAll('[data-det]').forEach(x => x.classList.remove('active')); b.classList.add('active'); });
}
function browseOrder() { return results.map((item, index) => item && !item.error ? index : null).filter(index => index !== null); }
function findNeighbor(index, direction) { const order = browseOrder(); const position = order.indexOf(index); const target = position + direction; return target >= 0 && target < order.length ? order[target] : null; }
function move(direction) { const next = findNeighbor(current, direction); if (next !== null) show(next); }

// --------------------------------------------------------------------------- //
// 事件绑定
// --------------------------------------------------------------------------- //
const fileInput = $('#file-input');
fileInput.addEventListener('click', () => { fileInput.value = ''; });
fileInput.addEventListener('change', e => { if (e.target.files?.length) pick(e.target.files); });
$('#detect-button').onclick = run;
$('#export-button').onclick = () => { try { downloadCsv(results.filter(r => !r.error)); } catch (e) { alert(e.message); } };
$('#live-button').onclick = () => {
  const panel = $('#live-panel');
  const opening = panel.classList.contains('hidden');
  panel.classList.toggle('hidden');
  if (opening) startCamera(); else stopCamera();
};
$('#batch-list').onclick = e => { const b = e.target.closest('[data-index]'); if (b) show(+b.dataset.index); };
$('#prev-image').onclick = () => move(-1);
$('#next-image').onclick = () => move(1);
document.addEventListener('keydown', e => { if (e.key === 'ArrowLeft') move(-1); if (e.key === 'ArrowRight') move(1); });
$('#drop-zone').ondragover = e => { e.preventDefault(); e.currentTarget.classList.add('drag'); };
$('#drop-zone').ondragleave = e => e.currentTarget.classList.remove('drag');
$('#drop-zone').ondrop = e => { e.preventDefault(); e.currentTarget.classList.remove('drag'); if (e.dataTransfer.files?.length) pick(e.dataTransfer.files); };
$('#save-image').onclick = () => { const a = document.createElement('a'); a.href = annotatedPng(); a.download = `${results[current].image_id.replace(/\.[^.]+$/, '')}_标注图.png`; a.click(); };

// 团队名称（导出文件名用，遵循「团队名称_检测结果.csv」规范）
// 用户填写的名称存 localStorage 优先；未填写时使用后端 config.classes 的 TEAM_NAME。
const teamInput = $('#team-name');
teamInput.value = teamName();
teamInput.addEventListener('change', () => localStorage.setItem('team_name', teamInput.value.trim()));
async function initTeamName() {
  try {
    const cfg = await fetchConfig();
    if (!(localStorage.getItem('team_name') || '').trim()) {
      teamInput.value = cfg.team_name || '';
      localStorage.setItem('team_name', (cfg.team_name || '').trim());
    }
  } catch (e) { /* 服务未就绪时保持占位，待服务启动后刷新页面即可 */ }
}
initTeamName();
