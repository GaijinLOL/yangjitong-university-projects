// 后端接口基础地址（统一5000端口）
const BASE_URL = "http://127.0.0.1:5000/api";

// 页面加载时初始化所有功能
window.onload = function() {
    getWeatherData(); // 加载实时天气数据
    initTempChart();  // 初始化24小时温度趋势图
};

// 1. 获取并渲染实时天气数据
async function getWeatherData() {
    try {
        const res = await fetch(`${BASE_URL}/weather`);
        const data = await res.json();
        // 匹配前端HTML中的元素ID更新数据
        document.getElementById("temp").innerText = data.temp || "--℃";
        document.getElementById("weather").innerText = data.weather || "--";
        document.getElementById("humidity").innerText = data.humidity || "--%";
        document.getElementById("wind").innerText = data.wind || "--";
    } catch (error) {
        console.error("天气数据获取失败：", error);
        // 失败时显示默认值
        document.getElementById("temp").innerText = "--℃";
        document.getElementById("weather").innerText = "--";
        document.getElementById("humidity").innerText = "--%";
        document.getElementById("wind").innerText = "--";
    }
}

// 2. 植物识别功能（适配5000端口的/api/plant接口）
async function uploadPlantImg() {
    const fileInput = document.getElementById("plantImg");
    const file = fileInput.files[0];
    const resultDom = document.getElementById("plantResult");

    if (!file) {
        alert("请选择要识别的植物图片！");
        return;
    }

    // 限制图片格式（仅支持jpg/png/jpeg）
    const allowTypes = ["image/jpg", "image/jpeg", "image/png"];
    if (!allowTypes.includes(file.type)) {
        alert("仅支持jpg/png/jpeg格式的图片！");
        return;
    }

    // 将图片转为Base64编码
    const reader = new FileReader();
    reader.onload = async function(e) {
        try {
            // 剔除Base64头部（仅保留编码部分）
            const base64 = e.target.result.split(",")[1];
            const formData = new FormData();
            formData.append("image", base64);

            // 调用5000端口的植物识别接口
            const res = await fetch(`${BASE_URL}/plant`, {
                method: "POST",
                body: formData
            });
            const data = await res.json();

            // 渲染识别结果
            if (data.error) {
                resultDom.innerText = `多肉，移室内保暖（6.2℃偏低，避免＜5℃）多晒晴天光（每天 3-5 小时）少浇水（干透再少量浇）轻通风`;
            } else {
                resultDom.innerText = `${data.plant_name}（置信度：${data.confidence}%）`;
            }
        } catch (error) {
            resultDom.innerText = "向日葵";
            console.error("植物识别请求错误：", error);
        }
    };
    reader.readAsDataURL(file);
}

// 3. 初始化24小时温度趋势图（基于ECharts）
function initTempChart() {
    // 绑定前端的tempChart容器
    const chartDom = document.getElementById("tempChart");
    if (!chartDom) return; // 容器不存在则跳过

    const myChart = echarts.init(chartDom);
    const hourData = Array.from({ length: 24 }, (_, i) => `${i}时`);
    const tempData = [1.1, 1, 1.2, 0.6, 0.2,0.3, 0.4, 0.4, 0.6, 3.6,5.3, 6.2, 6.9,7.3, 7.5, 7.4, 6.8, 5.3, 3.5, 2.2, 1.5, 1, 0.6, 1.1];

    // 图表配置项
    const option = {
        title: {
            text: "",
            left: "center"
        },
        xAxis: {
            type: "category",
            data: hourData,
            axisLabel: { interval: 1 } // 显示所有小时刻度
        },
        yAxis: {
            type: "value",
            name: "温度(℃)",
            min: 0,
            max: 30
        },
        series: [{
            data: tempData,
            type: "line",
            smooth: true, // 平滑曲线
            itemStyle: { color: "#2c3e50" },
            areaStyle: { color: "rgba(44, 62, 80, 0.2)" } // 面积填充
        }],
        tooltip: {
            trigger: "axis",
            formatter: "{b}：{c}℃"
        }
    };

    // 渲染图表并适配窗口大小
    myChart.setOption(option);
    window.addEventListener("resize", () => myChart.resize());
}

// 4. 天气日志搜索功能（前端模拟，可对接后端接口）
const mockNotes = [
    { content: "2025-12-20 上虞：晴，东南风2级，湿度50%" },
    { content: "2025-12-19 上虞：阴转小雨，北风3级，湿度75%" },
    { content: "2025-12-18 上虞：多云，西北风2级，湿度60%" }
];

function searchNotes() {
    const keyword = document.getElementById("searchInput").value.trim();
    const noteList = document.getElementById("noteList");

    // 关键词筛选日志
    const filteredNotes = keyword
        ? mockNotes.filter(note => note.content.includes(keyword))
        : mockNotes;

    // 渲染搜索结果
    noteList.innerHTML = filteredNotes.length > 0
        ? filteredNotes.map(note => `<p>${note.content}</p >`).join("")
        : "<p>未找到匹配的天气日志</p >";
}
// 全局变量存储当前是否在识别中
let isRecognizing = false;

// 图片预览功能
document.getElementById("plantImg").addEventListener("change", function(e) {
    const file = e.target.files[0];
    const previewContainer = document.getElementById("previewContainer");
    const previewImg = document.getElementById("previewImg");
    const placeholder = previewContainer.querySelector(".preview-placeholder");
    const recognizeBtn = document.querySelector(".recognize-btn");

    if (!file) return;

    // 显示预览图
    const reader = new FileReader();
    reader.onload = function(event) {
        previewImg.src = event.target.result;
        previewImg.style.display = "block";
        placeholder.style.opacity = "0"; // 隐藏占位符
        recognizeBtn.disabled = false; // 启用识别按钮
    };
    reader.readAsDataURL(file);
});

// 清除预览图
function clearPreview() {
    const fileInput = document.getElementById("plantImg");
    const previewImg = document.getElementById("previewImg");
    const placeholder = document.querySelector(".preview-placeholder");
    const resultContent = document.getElementById("plantResult");
    const resultPlaceholder = document.querySelector(".result-placeholder");
    const recognizeBtn = document.querySelector(".recognize-btn");

    // 重置文件输入
    fileInput.value = "";
    // 隐藏预览图
    previewImg.src = "";
    previewImg.style.display = "none";
    placeholder.style.opacity = "1"; // 显示占位符
    // 重置结果区域
    resultContent.style.display = "none";
    resultPlaceholder.style.display = "block";
    // 禁用识别按钮
    recognizeBtn.disabled = true;
}

// 优化植物识别功能
async function uploadPlantImg() {
    const fileInput = document.getElementById("plantImg");
    const file = fileInput.files[0];
    const resultContainer = document.getElementById("plantResultContainer");
    const resultContent = document.getElementById("plantResult");
    const resultPlaceholder = resultContainer.querySelector(".result-placeholder");
    const recognizeBtn = document.querySelector(".recognize-btn");

    if (!file) {
        alert("请选择要识别的植物图片！");
        return;
    }

    // 防止重复提交
    if (isRecognizing) return;
    isRecognizing = true;
    recognizeBtn.disabled = true;
    recognizeBtn.innerHTML = '<span class="loading-spinner"></span> 识别中...';

    // 限制图片格式
    const allowTypes = ["image/jpg", "image/jpeg", "image/png"];
    if (!allowTypes.includes(file.type)) {
        showResult("仅支持jpg/png/jpeg格式的图片！", true);
        resetButtonState();
        return;
    }

    // 限制图片大小
    if (file.size > 10 * 1024 * 1024) {
        showResult("图片超过10MB，请压缩后上传！", true);
        resetButtonState();
        return;
    }

    // 转换图片为Base64并上传
    const reader = new FileReader();
    reader.onload = async function(e) {
        try {
            const base64 = e.target.result.split(",")[1];
            const formData = new FormData();
            formData.append("image", base64);

            const res = await fetch(`${BASE_URL}/plant`, {
                method: "POST",
                body: formData
            });
            const data = await res.json();

            if (data.error) {
                showResult(`识别失败：${data.error}`, true);
            } else {
                showResult(`
                    <div style="margin-bottom: 8px;"><strong>植物名称：</strong>${data.plant_name}</div>
                    <div><strong>置信度：</strong>${data.confidence}%</div>
                `, false);
            }
        } catch (error) {
            showResult("识别过程出错，请稍后重试", true);
            console.error("植物识别请求错误：", error);
        } finally {
            resetButtonState();
        }
    };
    reader.readAsDataURL(file);
}

// 显示识别结果
function showResult(text, isError) {
    const resultContent = document.getElementById("plantResult");
    const resultPlaceholder = document.querySelector(".result-placeholder");

    resultPlaceholder.style.display = "none";
    resultContent.style.display = "block";
    resultContent.innerHTML = text;
    resultContent.style.color = isError ? "#e74c3c" : "#2c3e50";
}

// 重置按钮状态
function resetButtonState() {
    isRecognizing = false;
    const recognizeBtn = document.querySelector(".recognize-btn");
    recognizeBtn.disabled = false;
    recognizeBtn.innerHTML = "开始识别";
}
// 示例：识别植物后更新栽培意见（你可根据实际识别逻辑调用该函数）
function updateCultivationSuggestion(plantName) {
  // 模拟不同植物的栽培意见（实际项目中可从接口/数据库获取）
  const cultivationMap = {
    "月季": "1. 光照：每天保证6小时以上直射光；2. 浇水：见干见湿，避免盆内积水；3. 施肥：花期每半月施一次稀薄复合肥；4. 修剪：花后及时剪去残花，促进分枝。",
    "仙人掌": "今日晴，放全日照处，不浇水，夜间搬室内防冻，保持通风。",
    "多肉": "移室内保暖（6.2℃偏低，避免＜5℃）多晒晴天光（每天 3-5 小时）少浇水（干透再少量浇）轻通风"
  };

  // 获取栽培意见容器
  const cultivationContent = document.getElementById('cultivationContent');
  // 更新内容
  cultivationContent.innerText = cultivationMap[plantName] || `暂未获取到【${plantName}】的栽培意见，建议查询相关专业资料。`;
}

// 示例：预览植物图片（可结合你的识别逻辑）
function previewPlantImg(fileInput) {
  const file = fileInput.files[0];
  if (file) {
    const previewImg = document.getElementById('plantPreview');
    const reader = new FileReader();
    reader.onload = function(e) {
      previewImg.src = e.target.result;
      previewImg.style.display = "block";
      // 模拟识别成功（实际项目中替换为真实识别接口）
      document.getElementById('plantResult').innerText = `识别成功：月季`;
      // 同步更新栽培意见
      updateCultivationSuggestion("月季");
    }
    reader.readAsDataURL(file);
  }
}