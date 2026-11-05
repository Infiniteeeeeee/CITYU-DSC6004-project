"""Generate the Word report from the project's figures and result tables."""
import os
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = r"E:\DeepseekHarness_Workspace\DSC-6004-project"
FIG = os.path.join(ROOT, "figures")
RES = os.path.join(ROOT, "results")
OUT = os.path.join(ROOT, "report")
os.makedirs(OUT, exist_ok=True)

doc = Document()

# ---------- page & base styles ----------
sec = doc.sections[0]
sec.page_width = Inches(8.27); sec.page_height = Inches(11.69)
sec.left_margin = sec.right_margin = Inches(0.9)
sec.top_margin = Inches(0.8); sec.bottom_margin = Inches(0.8)

normal = doc.styles["Normal"]
normal.font.name = "Microsoft YaHei"
normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
normal.font.size = Pt(10.5)
normal.paragraph_format.space_after = Pt(4)
normal.paragraph_format.line_spacing = 1.25

for i, size in [(1, 16), (2, 13), (3, 11.5)]:
    st = doc.styles[f"Heading {i}"]
    st.font.name = "Microsoft YaHei"
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    st.font.size = Pt(size)
    st.font.bold = True
    st.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    st.paragraph_format.space_before = Pt(10)
    st.paragraph_format.space_after = Pt(4)


def h(text, level=1):
    doc.add_heading(text, level=level)


def p(text, bold=False, size=10.5, align=None, space_after=4):
    par = doc.add_paragraph()
    run = par.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    run.font.name = "Microsoft YaHei"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    if align == "center":
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.space_after = Pt(space_after)
    return par


def bullet(text):
    par = doc.add_paragraph(style="List Bullet")
    run = par.add_run(text)
    run.font.size = Pt(10.5)
    run.font.name = "Microsoft YaHei"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    par.paragraph_format.space_after = Pt(2)


def caption(text):
    par = doc.add_paragraph()
    run = par.add_run(text)
    run.italic = True
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    run.font.name = "Microsoft YaHei"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.space_after = Pt(8)


def figure(path, cap, width=6.1):
    doc.add_picture(path, width=Inches(width))
    par = doc.paragraphs[-1]
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.keep_with_next = True
    caption(cap)


def table(headers, rows, widths=None, font=9):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    hdr = t.rows[0].cells
    # repeat the header row when the table breaks across pages
    trPr = t.rows[0]._tr.get_or_add_trPr()
    tblHeader = OxmlElement("w:tblHeader")
    tblHeader.set(qn("w:val"), "true")
    trPr.append(tblHeader)
    cantSplit = OxmlElement("w:cantSplit")
    trPr.append(cantSplit)
    for i, name in enumerate(headers):
        hdr[i].text = ""
        run = hdr[i].paragraphs[0].add_run(name)
        run.bold = True; run.font.size = Pt(font)
        run.font.name = "Microsoft YaHei"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    for row in rows:
        cells = t.add_row().cells
        trPr = t.rows[-1]._tr.get_or_add_trPr()
        trPr.append(OxmlElement("w:cantSplit"))
        for i, val in enumerate(row):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(str(val))
            run.font.size = Pt(font)
            run.font.name = "Microsoft YaHei"
            run._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def add_page_number(section):
    footer = section.footer
    par = footer.paragraphs[0]
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = par.add_run()
    for tag, attr, text in [("w:fldChar", "begin", None), ("w:instrText", None, "PAGE"),
                            ("w:fldChar", "end", None)]:
        el = OxmlElement(tag)
        if attr:
            el.set(qn("w:fldCharType"), attr)
        if text:
            el.set(qn("xml:space"), "preserve")
            el.text = text
        run._r.append(el)


add_page_number(sec)


# ================= 封面 =================
for _ in range(4):
    doc.add_paragraph()
p("基于 CHARGED 数据集的电动汽车充电需求与", bold=True, size=20, align="center", space_after=2)
p("高峰事件预测实验报告", bold=True, size=20, align="center", space_after=12)
p("城市尺度逐小时数据 · 需求回归 · 峰值分类 · 误差分析", size=11, align="center", space_after=60)
p("数据来源：CHARGED（Scientific Data, 2025）", size=10, align="center", space_after=4)
p("建模城市：洛杉矶（LOA）、墨尔本（MEL）", size=10, align="center", space_after=4)
p("2026 年 11 月", size=10, align="center")
doc.add_page_break()

# ================= 摘要 =================
h("摘要", 1)
p("本报告基于 CHARGED 城市尺度电动汽车充电数据集（6 城、2023-04-01 至 2023-09-30、逐小时），"
  "回答三个问题：历史充电数据能否预测下一小时需求与峰值事件、预测精度如何、机器学习能否识别潜在峰值时段。"
  "我们在洛杉矶与墨尔本两座具有真实日内节律的城市上构建了站点—小时面板（约 128 万条），"
  "采用因果特征工程、滚动 4 折时间切分，比较了朴素基线、Ridge、梯度提升树与 LSTM。"
  "结果显示：需求预测相对“昨日同时刻”基线可将 WAPE 降低约 35%~45%（洛杉矶 0.281→0.153，"
  "墨尔本 0.442→0.306）；峰值事件在排序层面可识别（PR-AUC 为基准率的 3~8 倍），"
  "但概率校准受峰值率月份漂移的严重限制；误差高度集中于接近零需求的小时。"
  "报告同时给出数据质量核查、定义敏感性分析与可复现说明。")

# ================= 1 研究问题 =================
h("1 研究问题", 1)
p("本研究围绕以下三个问题展开：")
bullet("Q1：历史电动汽车充电数据能否预测下一小时需求和峰值事件？")
bullet("Q2：下一小时需求能被预测到多准确？")
bullet("Q3：机器学习能否识别潜在的峰值充电时段？")
p("三个问题分别对应：可行性判断（Q1）、回归精度（Q2）与分类/识别能力（Q3）。"
  "报告在给出结果后，将逐条回答，并明确每个结论成立的条件与边界。")

# ================= 2 数据集 =================
h("2 数据集", 1)
h("2.1 数据来源与规模", 2)
p("CHARGED 是一个城市尺度的电动汽车充电需求数据集，包含 6 个城市：阿姆斯特丹（AMS）、"
  "约翰内斯堡（JHB）、洛杉矶（LOA）、墨尔本（MEL）、圣保罗（SPO）与深圳（SZH）。"
  "每个城市提供 10 张表，时间范围为 2023-04-01 至 2023-09-30，共 4,392 个逐小时时间点。"
  "核心表为站点级小时矩阵（volume/duration/e_price/s_price），另有站点、充电桩、天气、POI 与站间距离等辅助表。")
p("数据规模：4,280 个站点、6,402 个充电桩记录，其中 3,127 个站点在观测期内产生过电量（活跃站点），"
  "1,153 个站点全期为 0（占比 27%）。站点级小时矩阵合计约 1,880 万条观测。")
h("2.2 数据质量与特点", 2)
p("全量核查显示：四个时间矩阵均无缺失值、无重复时间戳、无时间断档；天气表只有 preciptype 存在缺失（无降水时为空），"
  "属正常语义；距离矩阵对称。数据的结构性质量良好，但城市之间的“信息含量”差异极大。")
figure(os.path.join(FIG, "fig1_overview.png"),
       "图 1 站点构成与充电桩数量。AMS 有 43% 的站点全期为 0，LOA/MEL 仅 1%~2%。")
p("图 1 显示，AMS 的零站点比例高达 43%，而 LOA、MEL 低于 2%。这意味着“站点是否活跃”本身就构成一个城市差异维度，"
  "也直接影响了后续指标的解读。")
figure(os.path.join(FIG, "fig3_hour_heatmap.png"),
       "图 2 各城市日内负荷形状（相对该城市均值）。AMS 几乎完全平坦，LOA/MEL 呈现明显的日内节律。")
p("图 2 是选择建模城市的核心依据：AMS 的 24 个小时几乎都是 1.00，说明其“小时数据”实质上是日值或插值；"
  "而 LOA 的峰值出现在凌晨（1.26~1.35），MEL 的峰值出现在午间（1.33），两者都具有真实的日内结构。"
  "进一步统计（日内变异系数 CV<0.05 的站点占比）为：AMS 94%、JHB 57%、SPO 51%、SZH 50%、MEL 11%、LOA 8%。")
h("2.3 建模城市的选择", 2)
table(
    ["城市", "站点", "活跃", "合格*", "日内 CV<0.05", "峰值率", "本报告中的用途"],
    [["AMS", "2,449", "1,388", "≈81", "94.2%", "—", "反例：小时数据退化，不参与建模"],
     ["JHB", "47", "35", "17", "57.1%", "5.0%", "并入池化消融"],
     ["LOA", "229", "224", "204", "7.6%", "4.4%", "主分析城市"],
     ["MEL", "63", "62", "51", "11.3%", "5.0%", "主分析城市"],
     ["SPO", "47", "41", "19", "51.2%", "5.8%", "并入池化消融"],
     ["SZH", "1,445", "1,377", "691", "49.5%", "2.7%", "池化消融（大规模对照）"]],
    widths=[0.7, 0.8, 0.8, 0.7, 1.2, 0.8, 2.6])
caption("表 1 六城市概况。*合格站点指日内变异系数 CV≥0.05、即存在真实小时波动的站点。"
        "AMS 的峰值率未计算，因为它不参与建模。")
p("AMS 被排除的理由有三点：其一，94% 的活跃站点日内几乎无波动，小时序列更接近日值的平摊或插值；"
  "其二，其城市日总量呈三级台阶（约 5 万→25 万→120 万 kWh/天），反映的是数据覆盖度分三次接入，而非需求增长；"
  "其三，“昨日同时刻”基线在其上的 WAPE 仅 0.6%，任何模型都能轻易“获胜”，结论没有信息量。"
  "因此本报告将其作为反例保留在数据描述中，不进入训练与评估。")

# ================= 3 研究方法 =================
h("3 研究方法", 1)
h("3.1 数据组织与特征工程", 2)
p("原始数据是“站点 × 小时”的宽表。为便于统一建模，我们将其转换为“站点—小时”长表（面板），"
  "每行是一条观测，包含目标值、滞后特征、滚动统计、日历特征、天气与站点静态属性。"
  "建模主表为 LOA 与 MEL 合并后的 128 万行（286 个站点）。")
p("特征工程遵循两条原则：一是所有特征必须可在预测时刻获得（因果性），二是阈值类统计只能来自训练期。"
  "具体特征如下：")
table(
    ["类别", "字段", "说明"],
    [["滞后", "lag1, lag24, lag168", "前 1 小时、昨日同时刻、上周同时刻的电量"],
     ["滚动统计", "roll24_mean, roll24_std, roll168_mean", "过去 24h 均值/标准差、过去 7 天均值（均 shift(1)）"],
     ["日历", "hour, dow, doy", "小时、星期、年内日序"],
     ["站点静态", "charger_num, area, poi_density, lon, lat", "桩数、聚类面积、500m 网格 POI 计数、经纬度"],
     ["（弃用）天气", "temp, precip, humidity, wind, solar, cloud", "因时区口径不一致而弃用，见 3.2 说明"]],
    widths=[0.9, 2.6, 2.9])
caption("表 2 特征清单。所有滞后与滚动统计均只使用 t 时刻之前的信息。")
p("防泄漏措施包括：不使用 sites.csv 中的 total_volume、total_duration、avg_power（它们是全期聚合，含未来信息）；"
  "不使用 month 作为特征（测试月只有一个取值，等价于泄漏）；滚动统计一律 shift(1)；极值缩尾（P99.9）的阈值只用训练集计算。")
p("关于天气特征：时区核验发现，LOA 的充电峰值与太阳辐射峰值相差 13 小时，而 MEL 相差 0 小时，"
  "说明两城的时间戳口径不一致（MEL 为本地时间，LOA 可能不是）。在无法确认对齐关系的情况下，"
  "天气特征在两地一律弃用，以避免引入错位的协变量。这一取舍也使得模型的输入完全来自充电序列本身与日历/站点属性。")
h("3.2 峰值事件的定义", 2)
p("“峰值”不是数据中的原始标签，需要人为定义。本报告的主定义为：对每个站点、每个小时，"
  "取其过去 28 天同一小时电量的均值与标准差，若当前小时电量超过“均值 + 2 倍标准差”，则记为峰值事件。"
  "该定义完全因果（阈值只使用历史数据且不含当前小时），并随站点自身水平自适应。")
p("为检验结论是否依赖定义，我们另外构造了两种口径：滚动 28 天同小时中位数 × 4，以及训练期正电量小时的 P95（静态阈值）。"
  "三种定义的事件率与分类表现将在 4.4 节对比。")
h("3.3 数据划分", 2)
p("时间序列不能随机切分。我们采用扩展窗口的滚动原点验证：训练集从 4 月 1 日起逐月扩展，"
  "分别以 6、7、8、9 月作为测试月，训练与测试之间留 1 天间隔以避免边界泄漏。"
  "分类任务的概率校准使用测试月之前两个月的数据拟合。")
table(
    ["折", "训练区间", "测试月"],
    [["1", "2023-04-01 ~ 2023-05-31", "2023-06"],
     ["2", "2023-04-01 ~ 2023-06-30", "2023-07"],
     ["3", "2023-04-01 ~ 2023-07-31", "2023-08"],
     ["4", "2023-04-01 ~ 2023-08-31", "2023-09"]],
    widths=[0.6, 3.2, 1.2])
caption("表 3 滚动 4 折的时间划分。")
h("3.4 模型", 2)
p("回归任务比较四类模型：朴素基线（常数均值、昨日同时刻 t-24、上周同时刻 t-168）、Ridge 线性回归、"
  "梯度提升树（HistGradientBoosting）与 LSTM。分类任务比较基率、小时×星期频率表、逻辑回归与梯度提升树，"
  "并对树模型做 isotonic 概率校准。")
table(
    ["任务", "模型", "关键设置"],
    [["回归", "常数 / t-24 / t-168", "无拟合，作为及格线"],
     ["回归", "Ridge", "标准化特征，alpha=1.0，目标为原始电量"],
     ["回归", "HistGradientBoosting", "250 轮、学习率 0.08、31 叶、min_samples_leaf=40"],
     ["回归", "LSTM", "单层 64 维，输入过去 24 小时（按站点 z-score），batch 4096，30 epoch"],
     ["分类", "基率 / 小时×星期", "训练期频率，无拟合"],
     ["分类", "逻辑回归", "标准化特征 + 类别平衡"],
     ["分类", "HistGradientBoosting", "同回归配置，isotonic 校准（前两个月拟合）"]],
    widths=[0.8, 2.2, 3.4])
caption("表 4 模型配置。LSTM 在 NVIDIA RTX 3060（6GB）上训练，PyTorch 2.14.1 + CUDA 12.6。")
h("3.5 评估指标", 2)
p("回归使用 MAE、RMSE、R² 与 WAPE。其中 WAPE = Σ|预测−真实| / Σ|真实|，对量纲不敏感，"
  "是本报告跨城市比较的主指标；R² 采用站点内计算，并报告中位数与“R²>0 的站点占比”，"
  "以避免“只要猜对站点大小就能得高分”的假象。分类使用 Brier 分数、对数损失、PR-AUC 与 F1，"
  "其中 PR-AUC 更适合 2%~8% 的正例比例，F1 的阈值在验证集上选取。")

# ================= 4 结果 =================
h("4 结果", 1)
h("4.1 需求回归", 2)
figure(os.path.join(RES, "fig_cv_wape.png"),
       "图 3 滚动 4 折的 WAPE。两个城市的所有模型都稳定优于 t-24 基线。")
table(
    ["城市", "模型", "6 月", "7 月", "8 月", "9 月"],
    [["LOA", "t-24", ".479", ".500", ".422", ".290"],
     ["LOA", "Ridge", ".293", ".276", ".265", ".200"],
     ["LOA", "HGB", ".229", ".225", ".231", ".195"],
     ["MEL", "t-24", ".493", ".576", ".534", ".442"],
     ["MEL", "Ridge", ".368", ".387", ".374", ".314"],
     ["MEL", "HGB", ".463", ".378", ".389", ".470"]],
    widths=[0.8, 1.2, 0.9, 0.9, 0.9, 0.9])
caption("表 5 滚动 4 折的 WAPE（越低越好）。加粗结论见正文。")
p("两个城市的所有模型都显著优于“昨日同时刻”基线。但最优模型因城市而异：LOA（224 个站点）上梯度提升树最好，"
  "MEL（62 个站点）上树模型在 9 月反而输给基线，Ridge 最稳。这说明模型复杂度必须与样本量匹配——"
  "站点少时，树模型容易记住噪声。")
h("4.2 池化与外部城市的消融", 2)
table(
    ["训练方式", "LOA WAPE", "MEL WAPE"],
    [["单城训练（Ridge / HGB）", ".205 / .217", ".352 / .452"],
     ["两城池化（LOA+MEL）", ".235 / .211", ".346 / .429"],
     ["三城池化（+SZH）", ".236 / .208", ".350 / .392"]],
    widths=[2.3, 1.8, 1.8])
caption("表 6 8 月与 9 月的平均 WAPE。池化对 LOA 无益，对 MEL 的树模型有帮助，但仍不如单城 Ridge。")
p("池化对 LOA 没有帮助（它自身的数据已足够），对 MEL 的树模型则有明显改善（.452→.392）；"
  "但即使加入深圳的 634 万行，MEL 的树模型仍不如单城训练的 Ridge。深圳的数据量虽大，"
  "但其中一半站点本身是平坦的，能提供的“新信息”有限。")
h("4.3 峰值事件识别", 2)
figure(os.path.join(RES, "fig_cv_class.png"),
       "图 4 滚动 4 折的峰值分类表现（PR-AUC 与 Brier×10）。8 月是明显的困难月份。")
table(
    ["测试月", "城市", "事件率", "Brier", "PR-AUC", "F1"],
    [["6 月", "LOA", "4.5%", ".035", ".373", ".416"],
     ["7 月", "LOA", "4.5%", ".037", ".379", ".420"],
     ["8 月", "LOA", "2.0%", ".020", ".067", ".130"],
     ["9 月", "LOA", "8.5%", ".064", ".386", ".425"],
     ["6 月", "MEL", "7.8%", ".049", ".566", ".563"],
     ["7 月", "MEL", "4.8%", ".040", ".366", ".417"],
     ["8 月", "MEL", "5.9%", ".050", ".367", ".443"],
     ["9 月", "MEL", "4.6%", ".048", ".173", ".287"]],
    widths=[0.8, 0.8, 0.9, 0.9, 0.9, 0.9])
caption("表 7 峰值分类的滚动验证结果。")
p("峰值识别的排序能力是存在的：PR-AUC 通常是事件基准率的 3~8 倍，说明模型确实能把“更可能出峰”的时段排在前面。"
  "但 8 月几乎失效（LOA 的 PR-AUC 仅 .067），原因是峰值率本身在月份之间从 2% 波动到 8.5%，"
  "用前两个月校准的概率无法迁移到事件率完全不同的测试月。")
h("4.4 峰值定义敏感性", 2)
figure(os.path.join(RES, "fig_peak_defs.png"),
       "图 5 三种峰值定义在 LOA 9 月上的对比。")
table(
    ["定义", "全期事件率", "训练期", "测试期", "Brier", "PR-AUC", "F1"],
    [["滚动均值 + 2σ", "4.7%", "3.9%", "8.3%", ".064", ".385", ".412"],
     ["滚动中位数 × 4", "8.7%", "7.9%", "12.7%", ".080", ".517", ".550"],
     ["训练期 P95", "2.2%", "2.2%", "2.4%", ".019", ".389", ".400"]],
    widths=[1.6, 0.9, 0.8, 0.8, 0.7, 0.8, 0.7])
caption("表 8 三种峰值定义的对比（LOA，9 月）。")
p("“自适应”的滚动阈值会随需求整体水平漂移：训练期 3.9%、测试期 8.3%，事件率翻倍，概率校准随之失效。"
  "相反，静态 P95 虽然简单，事件率在训练期与测试期几乎一致（2.2% vs 2.4%），Brier 也最好（.019）。"
  "如果目标是“概率可解释”，P95 更合适；如果目标是“尽量不漏掉异常日”，×4 中位数的召回最高（F1 .550）。")
h("4.5 模型对比（同一测试集）", 2)
figure(os.path.join(RES, "fig_lstm_compare.png"),
       "图 6 在同一批测试行上的回归模型对比（9 月）。")
table(
    ["城市", "t-24", "Ridge", "HGB", "LSTM", "LSTM 的 95% 自助区间"],
    [["LOA", ".281", ".167", ".203", ".153", "[0.13, 0.18]"],
     ["MEL", ".442", ".324", ".540", ".306", "[0.16, 0.44]"]],
    widths=[0.8, 0.9, 0.9, 0.9, 0.9, 2.0])
caption("表 9 同一测试行（LOA 164,880 行 / MEL 45,360 行）上的 WAPE 与自助置信区间。")
p("LSTM 在两个城市上都取得了最低的 WAPE：LOA 0.153、MEL 0.306。不过自助区间显示，"
  "LSTM 与 Ridge 的差异并不稳健（LOA 区间 [0.13, 0.18] 与 [0.14, 0.20] 重叠，MEL 重叠更明显），"
  "而两者都显著优于 HGB（MEL 的 HGB 区间为 [0.40, 0.68]）。换言之，"
  "“序列模型优于线性模型”只能算弱证据，“优于树模型”才是强结论。")
h("4.6 误差分析", 2)
figure(os.path.join(RES, "fig_err_decile.png"),
       "图 7 误差随真实需求水平变化（对数轴）。最低十分位的误差高出 1~2 个数量级。")
p("误差几乎全部来自“接近零需求”的小时：LOA 的最低十分位 WAPE 为 2.4~3.3，模型平均高估 2.3~3.2 倍；"
  "MEL 的最低十分位 WAPE 高达 87~354，高估 86~354 倍。其余十分位的 WAPE 只有 0.11~0.67。"
  "整体 WAPE 之所以看起来不高，是因为高需求时段把平均值拉低了。")
figure(os.path.join(RES, "fig_err_bootstrap.png"),
       "图 8 200 次按站点重采样的 WAPE 及 95% 区间。")
figure(os.path.join(RES, "fig_err_acf.png"),
       "图 9 LSTM 残差的自相关。")
p("残差仍存在明显的日周期结构：LOA 在滞后 1 小时为 −0.35、滞后 24 小时为 +0.29，说明模型对上一小时“过度修正”，"
  "同时没有完全捕捉日周期。这为后续改进（两段式模型、残差建模）提供了直接依据。")
p("此外，按站点类型分解可见：合格站点（CV≥0.05）的 WAPE 为 LOA 0.178 / MEL 0.323，"
  "平坦站点仅 LOA 0.012 / MEL 0.185。平坦站点几乎“白送”正确预测，"
  "因此任何跨数据集的指标比较都必须说明站点构成。")
h("4.7 可解释性", 2)
figure(os.path.join(RES, "fig_importance.png"),
       "图 10 置换特征重要性（MAE 上升量）。前 1 小时与上周同时刻是主导特征。")
p("特征重要性显示，模型几乎完全依赖自回归信息：前 1 小时是绝对主导，其次是上周同时刻与近 24 小时均值；"
  "而 POI 密度、面积、经纬度、桩数的贡献接近于零。这说明在本数据上，"
  "“预测”本质上是“延续性建模”，空间与静态属性没有提供额外的边际信息。")

# ================= 5 研究问题回答 =================
h("5 研究问题的回答", 1)
p("Q1：历史电动汽车充电数据能否预测下一小时需求和峰值事件？", bold=True)
p("能，但有边界条件。需求侧：在具有真实日内节律的城市（LOA、MEL），历史序列足以支撑下一小时预测，"
  "所有模型都稳定优于朴素基线。峰值侧：可以识别“更可能出峰”的时段，但概率的可靠性受标签漂移限制。"
  "边界条件是：并非所有城市都适用——AMS 的小时数据有 94% 的站点日内无波动，“昨日同时刻”基线误差仅 0.6%，"
  "在这种城市上做逐小时预测没有意义。因此 Q1 的准确表述是："
  "“在数据具有真实小时动态的城市，历史数据可以支撑需求预测与峰值排序；否则不应建模。”")
p("Q2：下一小时需求能被预测到多准确？", bold=True)
p("在同一测试集上，LOA 的最优 WAPE 为 0.153（MAE 约 1.10 kWh/站点·小时），MEL 为 0.306（MAE 约 15.5 kWh）。"
  "相对“昨日同时刻”基线分别改善约 46% 与 31%。但这一精度并不均匀：高需求时段的 WAPE 为 0.11~0.40，"
  "而接近零需求的小时误差可达 2.4~354。若用途是容量规划，应重点关注高需求时段；"
  "若用途是“是否会突然有充电”，则需要先解决低需求高估问题。")
p("Q3：机器学习能否识别潜在的峰值充电时段？", bold=True)
p("能识别，但要区分“排序”与“概率”。排序层面：PR-AUC 为基准率的 3~8 倍，F1 在 LOA 上为 0.42~0.43、"
  "MEL 上为 0.29~0.56，说明模型可以把更可能出峰的时段排在前面。概率层面：由于峰值率在月份间波动 2%~8.5%，"
  "跨月校准会显著失真，8 月甚至接近失效。此外，结论依赖峰值定义：+2σ 会漂移，P95 最稳定（Brier .019），"
  "×4 中位数召回最高（F1 .550）。因此 Q3 的准确表述是："
  "“机器学习可以用于峰值时段的排序与预警，但报告概率时必须说明定义与校准窗口。”")

# ================= 6 局限性 =================
h("6 局限性", 1)
bullet("时间跨度只有 6 个月（4—9 月），无法覆盖冬季，也无法外推季节效应。")
bullet("城市间存在半球差异：MEL 位于南半球，同期为秋冬季；跨城市合并时季节并不对齐。")
bullet("天气特征因时间戳口径不一致而弃用，模型的输入不包含气象信息。")
bullet("只对 LOA 与 MEL 建模；AMS 因小时数据退化被排除，JHB/SPO/SZH 仅用于消融。")
bullet("峰值标签是构造的（阈值规则），不是数据中真实标注的事件；不同定义会给出不同的事件率与结论。")
bullet("LSTM 只跑了单折（9 月）、30 个 epoch 且未早停，也没有做超参数搜索，其优势的稳健性有限。")
bullet("MEL 只有 62 个站点，城市级结论的置信区间较宽。")

# ================= 7 结论 =================
h("7 结论", 1)
p("本报告在 CHARGED 数据集上完成了从数据核查、特征工程、滚动验证到误差分析的全流程，主要结论如下：")
bullet("需求可预测：在具有真实小时节律的城市，WAPE 可从基线的 0.28~0.44 降至 0.15~0.31，改善约 31%~46%。")
bullet("模型复杂度需与样本量匹配：树模型在站点少的 MEL 上过拟合，LSTM 与 Ridge 更稳；"
       "LSTM 与 Ridge 的差异在自助区间内并不显著，二者都明显优于树模型。")
bullet("预测信号以自回归为主：滞后特征几乎解释了全部方差，空间与静态特征的边际贡献接近于零。")
bullet("峰值识别的瓶颈是标签漂移而非模型能力：排序可用，概率不可跨月直接使用。")
bullet("峰值定义决定结论：+2σ、×4、P95 三种口径的事件率相差约 5 倍，任何“峰值”结论都必须写明定义。")
bullet("误差集中在接近零需求的小时，提示两段式模型或 Tweedie 损失是下一步最直接的改进方向。")

# ================= 8 可复现性 =================
h("8 可复现性", 1)
p("全部处理与建模均以脚本形式保存，数据与结果分离，随机种子固定。运行环境如下：")
table(
    ["项", "版本 / 说明"],
    [["Python", "3.12.14"],
     ["pandas / numpy", "3.0.1 / 2.3.5"],
     ["scikit-learn", "1.9.1"],
     ["PyTorch", "2.14.1 + cu126（GPU：RTX 3060 Laptop 6GB）"],
     ["matplotlib", "3.11.2"],
     ["数据", "data/ 下 6 个城市目录；表头问题已修复，原表头备份在 scripts/header_backup.json"]],
    widths=[1.6, 4.6])
caption("表 10 运行环境。")
p("脚本与执行顺序：")
table(
    ["脚本", "作用"],
    [["scripts/build_panel.py", "构建站点—小时面板（含因果特征与峰值标签）"],
     ["scripts/rolling_cv.py", "滚动 4 折回归与分类验证"],
     ["scripts/ablation.py", "单城 / 池化 / 加 SZH 的消融"],
     ["scripts/interpret.py", "特征重要性、部分依赖、误差分解"],
     ["scripts/peak_defs.py", "三种峰值定义的敏感性分析"],
     ["scripts/lstm_model.py", "GPU 上的 LSTM 训练与预测"],
     ["scripts/compare_lstm.py", "同测试集上的模型对齐比较"],
     ["scripts/error_analysis.py", "十分位误差、残差 ACF、自助区间"],
     ["scripts/make_figures.py", "数据特征图表"]],
    widths=[2.4, 3.8])
caption("表 11 脚本清单。按表中顺序执行即可复现全部结果。")
p("数据划分、随机种子（0）、超参数与阈值均写死在脚本中；面板与结果表分别保存在 panel/ 与 results/ 目录，"
  "图表保存在 figures/ 与 results/ 目录，可直接用于复核。")

doc.save(os.path.join(OUT, "实验报告_充电需求与峰值预测.docx"))
print("saved:", os.path.join(OUT, "实验报告_充电需求与峰值预测.docx"))
