// camera.js — 实时摄像头检测：浏览器摄像头 + 后端逐帧推理。
//
// 流程：getUserMedia 打开摄像头 → 循环抓帧（canvas.toBlob JPEG）→
// POST /api/predict（gray=1 对齐训练分布）→ 在 canvas 上叠加检测框 →
// 等本轮结果返回后再抓下一帧（串行，避免请求堆积）。
import { predictFrame } from './api.js';

const $ = s => document.querySelector(s);
const panel = $('#live-panel'), video = $('#live-video'), canvas = $('#live-canvas');
const hint = $('#live-hint'), ctx = canvas.getContext('2d');

let stream = null, running = false, timerId = 0;
let counts = {}, totalDefects = 0, lastTime = 0, fps = 0;

const MIN_INTERVAL_MS = 40; // 两次抓帧最小间隔，防止 GPU 推理过快时打满后端

function setButtons({ start, stop }) {
  $('#live-start').disabled = !start;
  $('#live-stop').disabled = !stop;
}

function resetStats() {
  counts = {}; totalDefects = 0; lastTime = 0; fps = 0;
  $('#live-fps').textContent = '-'; $('#live-ms').textContent = '-';
  $('#live-defects').textContent = '-'; $('#live-total').textContent = '0';
  $('#live-counts').innerHTML = '<p class="muted">检测中…</p>';
}

async function start() {
  if (running || stream) return;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showHint('当前浏览器不支持摄像头。请用 Chrome / Edge 打开 http://127.0.0.1:8080 重试。');
    return;
  }
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    });
  } catch (e) {
    const why = e.name === 'NotAllowedError' ? '摄像头权限被拒绝，请在地址栏允许摄像头权限后重试。'
      : e.name === 'NotFoundError' ? '未检测到摄像头设备。'
      : e.message || String(e);
    showHint(`无法访问摄像头：${why}`);
    return;
  }
  video.srcObject = stream;
  try { await video.play(); } catch (e) { /* 个别浏览器需要用户手势，忽略 */ }
  canvas.width = video.videoWidth || 1280;
  canvas.height = video.videoHeight || 720;
  hint.classList.add('hidden');
  running = true;
  setButtons({ start: false, stop: true });
  $('#live-verdict').textContent = '运行中';
  $('#live-verdict').className = 'verdict neutral';
  resetStats();
  loop();
}

async function loop() {
  if (!running) return;
  const t0 = performance.now();
  if (lastTime) fps = fps * 0.7 + (1000 / Math.max(1, t0 - lastTime)) * 0.3;
  lastTime = t0;
  $('#live-fps').textContent = fps.toFixed(1);

  // 抓当前帧：画到 canvas 再导出 JPEG
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise(res => canvas.toBlob(res, 'image/jpeg', 0.75));
  if (!running || !blob) return;

  try {
    const data = await predictFrame(blob, { gray: true });
    if (!running) return;
    drawBoxes(data);
    updateStats(data);
  } catch (e) {
    if (!running) return;
    $('#live-verdict').textContent = '服务异常';
    $('#live-verdict').className = 'verdict ng';
    $('#live-ms').textContent = String(e.message).slice(0, 40);
  }

  const elapsed = performance.now() - t0;
  if (running) timerId = setTimeout(loop, Math.max(0, MIN_INTERVAL_MS - elapsed));
}

function updateStats(data) {
  $('#live-ms').textContent = `${data.inference_time_ms} ms`;
  $('#live-defects').textContent = data.defect_count;
  const status = data.status || (data.defect_count ? 'NG' : 'OK');
  $('#live-verdict').textContent = status;
  $('#live-verdict').className = `verdict ${status.toLowerCase()}`;
  data.detections.forEach(d => {
    counts[d.class_name_zh] = (counts[d.class_name_zh] || 0) + 1;
    totalDefects += 1;
  });
  $('#live-total').textContent = totalDefects;
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  $('#live-counts').innerHTML = entries.length
    ? entries.map(([name, n]) => `<div class="count-row"><span>${name}</span><b>${n}</b></div>`).join('')
    : '<p class="muted">暂未检出缺陷</p>';
}

function confidenceColor(confidence) {
  return confidence < 0.4 ? '#ff667d' : confidence < 0.7 ? '#ffd166' : '#70e0a3';
}

function drawBoxes(data) {
  const line = Math.max(2, Math.round(canvas.width / 400));
  ctx.font = `${Math.max(14, Math.round(canvas.width / 45))}px sans-serif`;
  data.detections.forEach(d => {
    const color = confidenceColor(d.confidence);
    ctx.strokeStyle = color;
    ctx.lineWidth = line;
    ctx.strokeRect(d.x_min, d.y_min, d.x_max - d.x_min, d.y_max - d.y_min);
    const label = `${d.class_name_zh} ${d.confidence.toFixed(2)}`;
    const width = ctx.measureText(label).width + 12;
    ctx.fillStyle = color;
    ctx.fillRect(d.x_min, Math.max(0, d.y_min - 28), width, 28);
    ctx.fillStyle = '#07101c';
    ctx.fillText(label, d.x_min + 6, Math.max(20, d.y_min - 8));
  });
}

function stop() {
  running = false;
  clearTimeout(timerId);
  if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
  video.srcObject = null;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  $('#live-verdict').textContent = '已停止';
  $('#live-verdict').className = 'verdict neutral';
  $('#live-fps').textContent = '-';
  setButtons({ start: true, stop: false });
  showHint('已停止。点击「开始检测」重新开启。');
}

function showHint(text) {
  hint.textContent = text;
  hint.classList.remove('hidden');
}

export function startCamera() { start(); }
export function stopCamera() { stop(); }
export function isCameraRunning() { return running; }

// 面板内部按钮
$('#live-start').onclick = () => start();
$('#live-stop').onclick = () => stop();
$('#live-close').onclick = () => { stop(); panel.classList.add('hidden'); };
