// exporter.js — 前端 CSV 导出（字段与校验同后端 csv_export.py，保持同步）。
const HEADERS = ['image_id','class_name','confidence','x_min','y_min','x_max','y_max','inference_time_ms'];

/** 团队名称：用户输入存 localStorage；未填写时用 config.classes 的 TEAM_NAME 占位。 */
export function teamName() {
  return (localStorage.getItem('team_name') || '').trim() || 'TEAM_NAME';
}

function recordsFor(result) {
  if (!result.detections.length) return [[result.image_id, 'Ok', -1, -1, -1, -1, -1, result.inference_time_ms]];
  return result.detections.map(d => [result.image_id, d.class_name, d.confidence.toFixed(2), d.x_min, d.y_min, d.x_max, d.y_max, result.inference_time_ms]);
}
// 导出前按竞赛字段与像素框规则进行阻断式校验（附件1 要求）。
export function buildCsv(results) {
  const rows = results.flatMap(recordsFor); const ids = new Set(rows.map(r => r[0]));
  if (HEADERS.length !== 8 || results.some(r => !ids.has(r.image_id))) throw new Error('CSV 校验失败：存在缺失图片记录');
  for (const row of rows) {
    const [,, confidence, x1,y1,x2,y2] = row;
    if (row[1] === 'Ok') { if (![confidence,x1,y1,x2,y2].every(v => Number(v) === -1)) throw new Error('CSV 校验失败：Ok 占位行不规范'); }
    else if (!(Number(confidence) >= 0 && Number(confidence) <= 1 && Number(x2) > Number(x1) && Number(y2) > Number(y1))) throw new Error('CSV 校验失败：置信度或像素坐标不合法');
  }
  return [HEADERS.join(','), ...rows.map(row => row.join(','))].join('\n');
}
// 导出文件名遵循竞赛规范：团队名称_检测结果.csv
export function downloadCsv(results) { const blob = new Blob([buildCsv(results)], {type:'text/csv;charset=utf-8'}); const a = Object.assign(document.createElement('a'), {href:URL.createObjectURL(blob), download:`${teamName()}_检测结果.csv`}); a.click(); URL.revokeObjectURL(a.href); }
