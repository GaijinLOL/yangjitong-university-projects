function renderPriceChart(prices) {
  const el = document.getElementById('priceChart');
  if (!el) return;
  const chart = echarts.init(el);
  const x = (prices || []).map(p => p.trade_date);
  const y = (prices || []).map(p => p.close);
  chart.setOption({
    tooltip: {trigger: 'axis'},
    xAxis: {type: 'category', data: x},
    yAxis: {type: 'value'},
    grid: {left: 45, right: 20, top: 20, bottom: 35},
    series: [{type: 'line', data: y, smooth: true, name: '收盘价'}],
  });
}

function renderValuationChart(basics) {
  const el = document.getElementById('valuationChart');
  if (!el) return;
  const chart = echarts.init(el);
  const x = (basics || []).map(p => p.trade_date);
  const pe = (basics || []).map(p => p.pe_ttm);
  const pb = (basics || []).map(p => p.pb);
  const mv = (basics || []).map(p => p.total_mv);
  chart.setOption({
    tooltip: {trigger: 'axis'},
    legend: {data: ['PE(TTM)', 'PB', '总市值']},
    xAxis: {type: 'category', data: x},
    yAxis: [
      {type: 'value', name: 'PE/PB'},
      {type: 'value', name: '市值', position: 'right'}
    ],
    grid: {left: 45, right: 55, top: 30, bottom: 35},
    series: [
      {type: 'line', data: pe, smooth: true, name: 'PE(TTM)'},
      {type: 'line', data: pb, smooth: true, name: 'PB'},
      {type: 'bar', data: mv, yAxisIndex: 1, name: '总市值', opacity: 0.7},
    ],
  });
}

function renderFinaChart(fina) {
  const el = document.getElementById('finaChart');
  if (!el) return;
  const chart = echarts.init(el);
  const x = (fina || []).map(p => p.end_date);
  const roe = (fina || []).map(p => p.roe);
  const npm = (fina || []).map(p => p.netprofit_margin);
  const dta = (fina || []).map(p => p.debt_to_assets);
  const oiy = (fina || []).map(p => p.op_income_yoy);
  const npy = (fina || []).map(p => p.netprofit_yoy);
  chart.setOption({
    tooltip: {trigger: 'axis'},
    legend: {data: ['ROE', '净利率', '资产负债率', '营收同比', '净利同比']},
    xAxis: {type: 'category', data: x},
    yAxis: {type: 'value'},
    grid: {left: 45, right: 20, top: 30, bottom: 35},
    series: [
      {type: 'line', data: roe, name: 'ROE', smooth: true},
      {type: 'line', data: npm, name: '净利率', smooth: true},
      {type: 'line', data: dta, name: '资产负债率', smooth: true},
      {type: 'line', data: oiy, name: '营收同比', smooth: true},
      {type: 'line', data: npy, name: '净利同比', smooth: true},
    ],
  });
}

