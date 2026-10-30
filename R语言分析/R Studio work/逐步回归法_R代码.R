# 逐步回归法：读取 Word 数据表并进行双向逐步回归
# 使用方法：将本文件与“逐步回归法作业_非年份数据加4.docx”放在同一文件夹，
# 在 RStudio 打开本文件后点击 Source（或先把工作目录设为该文件夹）。

needed <- c("officer", "docxtractr", "MASS")
missing <- needed[!vapply(needed, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing) > 0) {
  install.packages(missing, repos = "https://cloud.r-project.org")
}
library(officer)
library(docxtractr)
library(MASS)

# 优先读取当前工作目录中的副本；找不到时弹出文件选择框。
# 如果 RStudio 的工作目录不是本文件所在文件夹，弹窗中选择：
# 逐步回归法作业_非年份数据加4.docx
file_path <- file.path(getwd(), "逐步回归法作业_非年份数据加4.docx")
if (!file.exists(file_path)) {
  message("当前工作目录：", getwd())
  message("未找到默认 Word 文件，请在弹窗中选择“逐步回归法作业_非年份数据加4.docx”。")
  file_path <- file.choose()
}

# 提取第一个表格
doc <- read_docx(file_path)
tables <- docx_extract_all_tbls(doc, guess_header = TRUE)
if (length(tables) < 1) stop("Word 文档中没有找到表格。")
dat <- as.data.frame(tables[[1]], stringsAsFactors = FALSE, check.names = FALSE)
if (ncol(dat) < 8) stop("表格列数少于 8 列，请检查 Word 表格格式。")

# 按表格的实际列顺序命名，避免中文编码导致变量名不可用
# 年份 + 因变量 CS + 6 个候选自变量 NZ、GZ、JZZ、TPOP、CUM、SZM
# 如果 Word 表头文字乱码，也不会影响本脚本运行
dat <- dat[, 1:8]
names(dat) <- c("YEAR", "CS", "NZ", "GZ", "JZZ", "TPOP", "CUM", "SZM")

# 清理数字：去掉千位分隔符、空格和非数字字符（保留负号和小数点）
for (j in seq_len(ncol(dat))) {
  x <- as.character(dat[[j]])
  x <- gsub(",", "", x, fixed = TRUE)
  # 连字符放在字符类最后，避免 R 的正则表达式把它误读为范围符号
  x <- gsub("[^0-9eE+.-]", "", x)
  dat[[j]] <- suppressWarnings(as.numeric(x))
}
dat <- dat[complete.cases(dat), ]
if (nrow(dat) < 10) stop("有效数据行太少，无法进行回归。")

# 所有结果都保存到所选 Word 文件所在的文件夹，
# 不受 RStudio 当前工作目录（例如 Home）的影响
output_dir <- dirname(normalizePath(file_path, winslash = "/", mustWork = TRUE))
output_file <- function(filename) file.path(output_dir, filename)

# 保存清理后的数据，便于复核
write.csv(dat, output_file("逐步回归_清理后数据.csv"), row.names = FALSE, fileEncoding = "UTF-8")

# 全模型与空模型：CS 为因变量，其余 6 列为候选自变量
full_model <- lm(CS ~ NZ + GZ + JZZ + TPOP + CUM + SZM, data = dat)
null_model <- lm(CS ~ 1, data = dat)

# 双向逐步回归，以 AIC 为准则；trace=TRUE 会在控制台显示每一步
step_model <- stepAIC(
  null_model,
  scope = list(lower = formula(null_model), upper = formula(full_model)),
  direction = "both",
  trace = TRUE
)

# 输出主要结果
cat("\\n========== 双向逐步回归结果 ==========\\n")
cat("数据文件：", normalizePath(file_path), "\\n")
cat("样本量：", nrow(dat), "\\n")
cat("最终模型：", deparse(formula(step_model)), "\\n\\n")
print(summary(step_model))
cat("\\n========== 方差分析表 ==========\\n")
print(anova(step_model))
cat("\\n========== VIF（最终模型含两个及以上自变量时） ==========\\n")
if (length(coef(step_model)) > 2) {
  if (!requireNamespace("car", quietly = TRUE)) {
    message("如需 VIF，请运行 install.packages('car') 后重新运行本段。")
  } else {
    print(car::vif(step_model))
  }
} else {
  cat("最终模型自变量少于两个，不计算 VIF。\\n")
}

# 将完整结果写入文本文件
sink(output_file("逐步回归_结果.txt"))
cat("双向逐步回归结果\\n")
cat("数据文件：", normalizePath(file_path), "\\n")
cat("最终模型：", deparse(formula(step_model)), "\\n\\n")
print(summary(step_model))
cat("\\n方差分析表：\\n")
print(anova(step_model))
sink()

# 基本诊断图
png(output_file("逐步回归_诊断图.png"), width = 1600, height = 1200, res = 180)
par(mfrow = c(2, 2))
plot(step_model)
dev.off()

message("完成：结果已保存到：", output_dir)
message("文件包括：逐步回归_清理后数据.csv、逐步回归_结果.txt、逐步回归_诊断图.png")

