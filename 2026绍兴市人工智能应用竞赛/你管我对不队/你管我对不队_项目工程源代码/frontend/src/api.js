// api.js — 后端接口封装。

export async function predict(file) {
  const form = new FormData(); form.append('image', file, file.name);
  const response = await fetch('/api/predict', { method: 'POST', body: form });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || '推理服务不可用，请确认服务已启动');
  return body;
}

/**
 * 实时摄像头帧推理。blob 为 JPEG 帧；gray=true 时后端先转单通道灰度，
 * 与「灰度内容存成三通道」的训练分布对齐。
 */
export async function predictFrame(blob, { gray = true } = {}) {
  const form = new FormData();
  form.append('image', blob, 'camera_frame.jpg');
  if (gray) form.append('gray', '1');
  const response = await fetch('/api/predict', { method: 'POST', body: form });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || '推理服务不可用，请确认服务已启动');
  return body;
}

/** 读取服务端配置（默认团队名等）。 */
export async function fetchConfig() {
  const response = await fetch('/api/config');
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || '读取配置失败');
  return body;
}
