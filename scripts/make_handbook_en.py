"""Generate the English handbook (detailed, zero-background edition)."""
import os
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = r"E:\DeepseekHarness_Workspace\DSC-6004-project"
FIG = os.path.join(ROOT, "figures", "en")
RES = os.path.join(ROOT, "results")
OUT = os.path.join(ROOT, "report")
os.makedirs(OUT, exist_ok=True)

doc = Document()
sec = doc.sections[0]
sec.page_width = Inches(8.27); sec.page_height = Inches(11.69)
sec.left_margin = sec.right_margin = Inches(0.85)
sec.top_margin = Inches(0.75); sec.bottom_margin = Inches(0.75)
sec.different_first_page_header_footer = True

normal = doc.styles["Normal"]
normal.font.name = "Calibri"
normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
normal.font.size = Pt(10.5)
normal.paragraph_format.space_after = Pt(4)
normal.paragraph_format.line_spacing = 1.3

for lvl, size in [(1, 17), (2, 13.5), (3, 11.5)]:
    st = doc.styles[f"Heading {lvl}"]
    st.font.name = "Calibri"
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    st.font.size = Pt(size)
    st.font.bold = True
    st.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    st.paragraph_format.space_before = Pt(12)
    st.paragraph_format.space_after = Pt(4)


def _font(run, size=10.5, bold=False, italic=False, color=None):
    run.font.name = "Calibri"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)


def _rich(par, text, size=10.5, bold=False, color=None, italic=False):
    for i, seg in enumerate(str(text).split("**")):
        if not seg:
            continue
        _font(par.add_run(seg), size, bold=(bold or i % 2 == 1), color=color, italic=italic)


def h(text, level=1):
    doc.add_heading(text, level=level)


def p(text, size=10.5, bold=False, align=None, after=4):
    par = doc.add_paragraph()
    _rich(par, text, size, bold)
    if align == "center":
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.space_after = Pt(after)
    return par


def bullet(text, size=10.5):
    par = doc.add_paragraph(style="List Bullet")
    _rich(par, text, size)
    par.paragraph_format.space_after = Pt(2)


def numbered(text, size=10.5):
    par = doc.add_paragraph(style="List Number")
    _rich(par, text, size)
    par.paragraph_format.space_after = Pt(2)


def caption(text):
    par = doc.add_paragraph()
    _font(par.add_run(text), 8.8, italic=True, color=(0x55, 0x55, 0x55))
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.space_after = Pt(10)


def figure(path, cap, width=6.3):
    doc.add_picture(path, width=Inches(width))
    par = doc.paragraphs[-1]
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.keep_with_next = True
    caption(cap)


def _shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def callout(title, text, color="EAF2FB"):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = t.cell(0, 0); cell.text = ""
    _shade(cell, color)
    par = cell.paragraphs[0]
    _font(par.add_run(title), 10, bold=True, color=(0x1F, 0x3A, 0x5F))
    par2 = cell.add_paragraph()
    _rich(par2, text, 9.5)
    par2.paragraph_format.space_after = Pt(2)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def table(headers, rows, widths=None, font=9, caption_text=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    trPr = t.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
    trPr.append(OxmlElement("w:cantSplit"))
    for i, name in enumerate(headers):
        cell = t.rows[0].cells[i]; cell.text = ""
        _font(cell.paragraphs[0].add_run(name), font, bold=True)
    for row in rows:
        cells = t.add_row().cells
        t.rows[-1]._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for i, val in enumerate(row):
            cells[i].text = ""
            _rich(cells[i].paragraphs[0], str(val), font)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    if caption_text:
        caption(caption_text)
    return t


def page_number(section):
    par = section.footer.paragraphs[0]
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


page_number(sec)

# ===================== cover =====================
for _ in range(5):
    doc.add_paragraph()
p("EV Charging Demand Forecasting Project", size=24, bold=True, align="center", after=4)
p("Operations Handbook and Full Experiment Record", size=18, bold=True, align="center", after=18)
p("From zero background to data, methods and conclusions — ready for posters, papers and talks",
  size=11, align="center", after=60)
p("Data: CHARGED (Scientific Data, 2025)", size=10, align="center", after=4)
p("Cities modelled: Los Angeles (LOA) and Melbourne (MEL)", size=10, align="center", after=4)
p("November 2026", size=10, align="center", after=40)
p("This handbook assumes no machine-learning background: every term is explained and every figure "
  "comes with a 'how to read it' note.", size=10, align="center")
doc.add_page_break()

# ===================== 0 reading guide =====================
h("0 How to Use This Handbook", 1)
p("This is not a results memo but an operations handbook that can be handed to other team members. It assumes "
  "no machine-learning background, and it is written so that any reader can explain what the project does, "
  "read every figure, quote the numbers correctly in discussion, and use the material to build a poster, "
  "write a paper or prepare a talk.")
p("Suggested reading order:")
numbered("Chapters 1–2: understand what we are predicting and what the data look like. No background needed.")
numbered("Chapters 3–5: methods and models. Every technical term appears in a shaded box.")
numbered("Chapters 6–8: results, errors and interpretability. Every figure has a 'how to read it' note.")
numbered("Chapters 9–12: conclusions, limitations, reproducibility, and ready-to-use poster/paper/talk material.")
p("If you have only one hour: read Chapters 1, 2, 6 and the 'three-sentence summary' in Chapter 11. "
  "That is enough for most non-technical questions.")

figure(os.path.join(FIG, "hb_pipeline_en.png"),
       "Figure 0-1. The eight steps of the project. The handbook follows this order, and every step has a script and figures.")
callout("Term box: what is a 'model'?",
        "In this project a model is a mathematical function that maps inputs (the last 24 hours of volume, the day of "
        "the week, site attributes) to an output (next-hour volume, or the probability of a peak). Training fits the "
        "function to historical data; prediction feeds it new inputs. We compared several function forms (linear, tree, "
        "neural network) to see which generalises best to unseen data.")

# ===================== 1 research questions =====================
h("1 Research Questions", 1)
p("The project starts from a practical setting: a city has many public chargers, and the operator wants to know "
  "how much charging is likely in the next hour, and when congestion (a peak) may occur. If both can be anticipated, "
  "the operator can adjust pricing, redirect vehicles to idle sites, or schedule maintenance.")
p("Translated into testable questions:")
table(["ID", "Question", "Task type", "What counts as an answer"],
      [["Q1", "Can historical charging data predict next-hour demand and peak events?", "Feasibility",
        "The model beats a naive baseline such as 'same hour yesterday' consistently"],
       ["Q2", "How accurately can next-hour demand be predicted?", "Regression",
        "WAPE, MAE and the relative improvement over the baseline"],
       ["Q3", "Can machine learning identify potential peak charging periods?", "Classification",
        "PR-AUC, F1 and calibration"]],
      widths=[0.5, 2.5, 1.2, 2.3],
      caption_text="Table 1-1. The three research questions and their task types.")

# ===================== 2 dataset =====================
h("2 Dataset", 1)
h("2.1 What the dataset is", 2)
p("CHARGED is a public, city-scale EV charging dataset published in Scientific Data (2025). It harmonises public "
  "charging records from six cities (Amsterdam, Johannesburg, Los Angeles, Melbourne, São Paulo, Shenzhen) into a "
  "single format, covering 1 April – 30 September 2023 at hourly resolution (4,392 timestamps).")
p("Each city has ten tables. Think of it as an Excel workbook: some sheets are hourly matrices, some are site lists, "
  "some are weather logs.")
table(["File", "Content", "Role in this project"],
      [["volume.csv", "Charging volume (kWh) per site per hour; rows are time, columns are sites", "**Prediction target**"],
       ["duration.csv", "Charging duration (hours) per site per hour", "Supporting variable, not modelled"],
       ["e_price.csv", "Electricity price (local currency/kWh)", "Not used (too many missing values)"],
       ["s_price.csv", "Service fee (often zero)", "Not used"],
       ["sites.csv", "Site list: coordinates, charger count, area, average power", "Site static features"],
       ["chargers.csv", "Charger list with parent site", "Counting and validation"],
       ["distance.csv", "Pairwise geodesic distance between sites (km)", "Spatial analysis (not in the models)"],
       ["weather.csv", "Hourly weather: temperature, precipitation, humidity, wind, radiation, 19 columns", "Dropped (time-zone issue, Section 3.3)"],
       ["poi.csv", "Points of interest from OpenStreetMap", "Site-level POI density feature"],
       ["info.csv", "City-level summary: site counts, total volume, DBSCAN radius", "Metadata"]],
      widths=[1.1, 3.6, 2.3],
      caption_text="Table 2-1. The ten tables. The bold entry is the core target.")
p("Scale: 4,280 sites and 6,402 charger records. The site-level hourly matrices contain about 18.8 million "
  "observations. Of the sites, 3,127 produced non-zero volume at some point (active sites) and 1,153 are zero "
  "throughout (27%).")

h("2.2 Data quality: the short version", 2)
p("We inspected all sixty files completely (not by sampling). The conclusion is that **structural quality is good "
  "but informational content differs enormously across cities**.")
bullet("Structure: the four time-series matrices have no missing values, no duplicated timestamps and no gaps; the only "
       "missing column in the weather table is preciptype (empty when there is no precipitation, which is expected); "
       "the distance matrices are symmetric.")
bullet("Content: the hourly information content differs by an order of magnitude between cities; some are almost flat "
       "within a day.")
figure(os.path.join(FIG, "fig1_overview_en.png"),
       "Figure 2-1. Site composition (left) and charger counts (right). Red numbers are the share of zero-volume sites.")
p("How to read it: blue bars are sites that produced volume, grey are sites that stayed at zero. In Amsterdam 43% of "
  "sites are grey, so a large nominal site count does not imply demand. Los Angeles and Melbourne have only 1%–2%.")
figure(os.path.join(FIG, "fig3_hour_heatmap_en.png"),
       "Figure 2-2. Hour-of-day profile relative to each city's mean. AMS is essentially flat; LOA and MEL show clear structure.")
p("How to read it: a uniformly pale row (close to 1.00) means the city uses roughly the same amount of power at every "
  "hour; strong red/blue patterns mean morning/evening peaks. Amsterdam is flat, Melbourne peaks at noon (1.33) and "
  "troughs at dawn (0.64), Los Angeles peaks in the early morning (1.26–1.35) and dips in the afternoon (0.71).")
p("This figure decides which cities can be modelled hourly. Only cities with intraday structure make hourly "
  "forecasting meaningful.")
figure(os.path.join(FIG, "fig2_daily_en.png"),
       "Figure 2-3. Daily total volume per city (log scale).")
p("How to read it: the vertical axis is logarithmic, so a step means a multiplicative change. Amsterdam steps up twice "
  "(in May and June): that is data coverage being connected in stages, not demand growth. Such discontinuities must be "
  "avoided or modelled explicitly, otherwise the model mistakes 'more data' for 'more demand'.")
figure(os.path.join(FIG, "fig4_cv_en.png"),
       "Figure 2-4. Per-site intraday variability (log scale). Red numbers: share of sites with CV < 0.05.")
p("How to read it: each point is a site; we compute the within-day standard deviation divided by the mean. The red "
  "dashed line marks 0.05. In Amsterdam 94% of sites fall below it, versus 11% in Melbourne. This is the most direct "
  "evidence that Amsterdam should not be modelled hourly.")
figure(os.path.join(FIG, "fig5_size_en.png"),
       "Figure 2-5. Site-size distribution (left) and volume concentration (right).")
p("How to read it: the left panel spans three orders of magnitude; the steeper the right-hand curve, the more volume "
  "is concentrated in a few large sites. Shenzhen is the most concentrated: the top 5% of sites contribute about 60% "
  "of volume. This is why aggregate metrics must not be read as 'average site behaviour'.")
figure(os.path.join(FIG, "fig6_price_en.png"),
       "Figure 2-6. Electricity price and service fee. Left: median non-zero price (log scale); the share of zeros is printed below.")
p("How to read it: 98% of Los Angeles price cells are zero (not collected, not free), so price cannot be used as a "
  "feature. São Paulo's values are around 160, an order of magnitude above the others, suggesting a different unit.")
figure(os.path.join(FIG, "fig7_weather_en.png"),
       "Figure 2-7. Correlation between daily demand and weather variables.")
p("How to read it: darker colours mean stronger correlation. Amsterdam's 0.79 with temperature is spurious: both "
  "series rise together because of the coverage steps. Genuine correlations are generally weak, which is one reason "
  "weather was dropped.")
figure(os.path.join(FIG, "fig8_poi_en.png"),
       "Figure 2-8. POI composition by city.")
p("How to read it: more than 80% of POIs fall into the OpenStreetMap 'other' category in most cities, so POI "
  "usability varies by city. We used only a single 'POI density around the site' feature, and the interpretability "
  "analysis later shows its contribution is close to zero.")
figure(os.path.join(FIG, "fig9_distance_en.png"),
       "Figure 2-9. Amsterdam inter-site distance matrix (sorted by longitude).")
p("How to read it: brighter cells mean the two sites are farther apart; the diagonal is zero. The block structure "
  "shows that sites cluster spatially, which is exactly what DBSCAN produced when chargers were merged into virtual sites.")

h("2.3 Why only two cities are modelled", 2)
p("The dataset has six cities, but the main analysis uses only Los Angeles and Melbourne. This is a data-driven choice:")
table(["City", "Sites", "Active", "Flat sites", "Peak rate", "Role"],
      [["AMS", "2,449", "1,388", "94.2%", "—", "Counter-example, not modelled"],
       ["JHB", "47", "35", "57.1%", "5.0%", "Pooling ablation only"],
       ["LOA", "229", "224", "7.6%", "4.4%", "**Primary city**"],
       ["MEL", "63", "62", "11.3%", "5.0%", "**Primary city**"],
       ["SPO", "47", "41", "51.2%", "5.8%", "Pooling ablation only"],
       ["SZH", "1,445", "1,377", "49.5%", "2.7%", "Pooling ablation (large-scale control)"]],
      widths=[0.7, 0.8, 0.8, 1.0, 0.8, 2.4],
      caption_text="Table 2-2. Overview of the six cities; 'flat sites' = share with intraday CV < 0.05.")
callout("Why can't Amsterdam be modelled?",
        "Three reasons. (1) 94% of its active sites show almost no intraday variation, so the hourly series is closer to "
        "a daily value spread over 24 hours. (2) Its daily total moves in three steps, which reflects data coverage, not "
        "demand. (3) The same-hour-yesterday baseline already achieves a WAPE of 0.6%, so any model can 'win' and the "
        "conclusion carries no information. It is kept as a counter-example: not every published hourly dataset is "
        "worth modelling hourly.")

# ===================== 3 methods =====================
h("3 Methods", 1)
h("3.1 From wide tables to a panel", 2)
p("The raw volume.csv is a wide table (rows = time, columns = sites). It is convenient to look at but unsuitable for "
  "modelling, because each column is a different site with a very different scale. We reshape it into a long "
  "site-hour panel: each row is one observation with city, site, timestamp, volume and the constructed features. "
  "This is called panel data in statistics.")
p("The panel for LOA + MEL contains about 1.28 million rows and 286 sites. All sites then share one model, with city "
  "and site attributes entering as columns.")

h("3.2 Feature engineering", 2)
p("A feature is an input column. The raw data only contain 'volume at this moment', but predicting the next hour "
  "clearly requires history, so we construct three families of features:")
table(["Category", "Features", "Why it is needed"],
      [["Lags", "t-1, t-24 (yesterday), t-168 (last week)", "Charging has strong inertia and daily/weekly cycles"],
       ["Rolling statistics", "Mean/std over the past 24 h; mean over the past 7 days", "Captures the recent level and recent volatility"],
       ["Calendar", "Hour of day, day of week, day of year", "Separates weekdays/weekends and day/night"],
       ["Site statics", "Charger count, cluster area, POI density, coordinates", "Tells the model whether a site is large or small, central or remote"]],
      widths=[1.0, 3.2, 2.8],
      caption_text="Table 3-1. Feature set. Every lag and rolling statistic uses only information before time t.")
callout("Term box: what is a 'lag'?",
        "A lag copies a value from a past moment into the current row. For example, lag24 is 'the volume 24 hours ago'. "
        "When predicting 15:00 today, lag24 is yesterday at 15:00. It is the most direct historical signal available.")
callout("Term box: why shift(1)?",
        "If we include the current hour when computing a rolling mean and then use that mean to predict the current hour, "
        "we are effectively telling the model the answer. This is data leakage and inflates the scores. shift(1) moves "
        "the window back by one step so that only past data is used.")
p("We deliberately do **not** use the following, all for leakage or availability reasons:")
bullet("total_volume, total_duration and avg_power in sites.csv: they are period aggregates that contain future information.")
bullet("month as a feature: the test set contains a single month, so month would effectively reveal the answer.")
bullet("Price: 71%–98% of the entries are zero and units differ across cities.")
bullet("Weather: the timestamps are not on a consistent clock (Section 3.3).")

h("3.3 A check that must be done: time zone", 2)
p("Weather is recorded at local hours, but whether the charging timestamps are also local must be verified. We compared "
  "the intraday peak of charging volume with that of solar radiation, which always peaks near local noon.")
p("Result: both peak at 12:00 in Melbourne (offset 0 h), so Melbourne is local time. In Los Angeles the charging peak "
  "is at 02:00 while solar radiation peaks at 13:00, a 13-hour difference that is inconsistent with any local-time "
  "interpretation, suggesting that the Los Angeles timestamps are not local time.")
callout("Why does this check matter?",
        "If the two clocks are not aligned, joining weather to charging 'misaligns' the covariates: afternoon temperature "
        "would be used to explain midnight charging. Since alignment cannot be established, we drop weather for both "
        "cities. Better to lose one feature than to introduce a misaligned variable.")

h("3.4 Splits: why not shuffle", 2)
p("Machine learning usually splits data randomly into training and test sets. Time series cannot do that: if shuffled, "
  "the model may already have 'seen' data close to the test moments, and the evaluation becomes optimistic. The correct "
  "approach is to train on the past and test on the future.")
p("We use rolling-origin validation: the training set starts in April and expands month by month, predicting June, July, "
  "August and September in turn, with a one-day gap between training and test. Every test month therefore has a model "
  "trained only on earlier data, which is closer to real deployment.")
figure(os.path.join(FIG, "hb_timeline_en.png"),
       "Figure 3-1. Rolling-origin validation: blue is training, red is the test month, with a one-day gap.")

h("3.5 Evaluation metrics", 2)
p("Metrics answer 'how accurate is the forecast'. We use four regression metrics and four classification metrics; "
  "plain-language explanations follow.")
table(["Metric", "In one sentence", "Range", "How to read it"],
      [["MAE", "Average absolute error in kWh", "≥0, lower better", "Same unit as data; intuitive but not comparable across cities"],
       ["RMSE", "Like MAE but punishes large errors more", "≥0, lower better", "Dominated by outliers; report with MAE"],
       ["WAPE", "Total error ÷ total actual", "≥0, lower better", "**Primary metric**: scale-free, comparable across cities"],
       ["R²", "Share of variance explained", "≤1, closer to 1 better", "Computed within sites, avoids 'guessing size'"],
       ["Brier", "Mean squared difference between probability and outcome", "0–1, lower better", "Combines accuracy and calibration"],
       ["PR-AUC", "Ranking quality when positives are rare", "0–1, higher better", "Prefer it to accuracy when the base rate is low"],
       ["F1", "Harmonic mean of precision and recall", "0–1, higher better", "Requires a threshold chosen on validation"]],
      widths=[0.9, 2.6, 1.2, 2.6],
      caption_text="Table 3-2. Metric cheat sheet.")
callout("Term box: why WAPE?",
        "Site volumes differ by a factor of 400. Plain MAE would let large sites dominate and hide errors at small sites. "
        "WAPE normalises by total volume, effectively weighting each site by its volume, so it can compare cities and "
        "models. WAPE = 0.15 means 'the total error equals 15% of total volume'.")

# ===================== 4 peak events =====================
h("4 Peak Events: a Concept That Must Be Defined", 1)
p("The data contain no 'peak' column. It is a label we construct from the business meaning; how we define it determines "
  "whether the classification task is meaningful at all.")
h("4.1 The intuitive definition: above your own history", 2)
p("For each site and each hour, we take the volume of the same hour over the previous 28 days, compute its mean and "
  "standard deviation, and label the current hour as a peak if its volume exceeds mean + 2 standard deviations.")
figure(os.path.join(FIG, "hb_peak_definition_en.png"),
       "Figure 4-1. How a peak event is defined. Blue is the actual volume, the red dashed line is the dynamic threshold, and red dots are events.")
p("How to read it: the threshold is not a flat line; it follows the daily rhythm because it is computed for the same "
  "hour. Only when a given day is clearly above its own four-week level for that hour is it marked red. This lets sites "
  "of different sizes share one rule without 'large sites always win'.")
callout("Why not define peaks by capacity utilisation?",
        "The natural idea is 'volume / installed capacity > 80%'. But avg_power in this dataset is the mean power of a "
        "single charging session, not installed capacity. Estimating capacity as charger_num × avg_power shows that "
        "62%–73% of sites already exceed it in their *average* state, which is physically impossible. Capacity-based "
        "definitions are therefore unusable, and we fall back on a relative-to-history definition.")

h("4.2 The peak rate drifts by month", 2)
figure(os.path.join(FIG, "hb_peak_month_en.png"),
       "Figure 4-2. Share of peak events by month.")
p("How to read it: the same definition labels 2.1% of hours in August but 8.3% in September (Los Angeles). Peaks are "
  "not a stationary phenomenon: they vary with season, weather and travel patterns. This is why the classifier performs "
  "poorly in August and recovers in September — the model is not broken, the base rate of the label has changed.")

# ===================== 5 models =====================
h("5 Models", 1)
p("We group models into three tiers: baselines (no learning, only simple inference), classical models (linear regression, "
  "trees) and neural networks (LSTM). The purpose is to answer a key question: **is a complex model actually better than "
  "a simple one?**")
table(["Model", "Type", "In one sentence", "Role"],
      [["t-24 / t-168", "Baseline", "Copy yesterday's / last week's value", "Pass mark: every model must beat it"],
       ["Ridge", "Linear", "Weighted sum of features with regularisation", "Interpretable reference"],
       ["HGB", "Tree ensemble", "Many decision trees that correct each other's errors", "Non-linear reference"],
       ["LSTM", "Neural network", "Reads the past 24 hours in order and remembers long dependencies", "Sequence-model representative"]],
      widths=[1.2, 1.0, 3.1, 2.0],
      caption_text="Table 5-1. Regression models; classification uses the same idea (base rate, logistic regression, HGB).")
figure(os.path.join(FIG, "hb_lstm_arch_en.png"),
       "Figure 5-1. LSTM architecture: the sequence branch reads the last 24 hours, then concatenates calendar and site features before the output layer.")
p("How to read it: the left block is the sequence input, the middle is the LSTM (which 'remembers' trends), the green "
  "blocks are extra information, and the right block produces the next-hour output. This structure suits time series "
  "but overfits more easily, which is exactly why it is unstable on the small city.")
callout("Term box: what is 'overfitting'?",
        "Overfitting means the model memorises noise in the training data: accurate on training data, poor on new data. "
        "A typical symptom is a model that behaves normally in August and collapses in September. Small samples (such as "
        "Melbourne's 62 sites) overfit easily, which is why trees did worse than a simple linear model there.")

# ===================== 6 results =====================
h("6 Results: how accurate are the models?", 1)
h("6.1 Demand regression: every model beats the baseline", 2)
figure(os.path.join(FIG, "fig_cv_wape_en.png"),
       "Figure 6-1. WAPE over the rolling folds. Grey is the baseline; red and blue are models.")
p("How to read it: lower is better. The grey line (same hour yesterday) is clearly above the coloured lines in both "
  "cities, so the models do learn something. Los Angeles is best with HGB; Melbourne's blue line turns up in September, "
  "showing that the tree model overfits there.")
table(["City", "Model", "Jun", "Jul", "Aug", "Sep"],
      [["LOA", "t-24", ".479", ".500", ".422", ".290"],
       ["LOA", "Ridge", ".293", ".276", ".265", ".200"],
       ["LOA", "HGB", ".229", ".225", ".231", ".195"],
       ["MEL", "t-24", ".493", ".576", ".534", ".442"],
       ["MEL", "Ridge", ".368", ".387", ".374", ".314"],
       ["MEL", "HGB", ".463", ".378", ".389", ".470"]],
      widths=[0.8, 1.2, 0.9, 0.9, 0.9, 0.9],
      caption_text="Table 6-1. WAPE over the rolling folds (lower is better).")

h("6.2 Does pooling help?", 2)
figure(os.path.join(FIG, "fig_ablation_pooling_en.png"),
       "Figure 6-2. WAPE for single-city training, pooled LOA+MEL, and pooled plus Shenzhen.")
p("How to read it: the three bar groups are the three training schemes. Los Angeles is best under single-city training "
  "(it has enough data of its own); Melbourne's tree model improves when Shenzhen is added, but still does not beat the "
  "linear model. More data is not automatically more information — half of Shenzhen's sites are flat.")

h("6.3 Peak identification: ranking works, probability does not", 2)
figure(os.path.join(FIG, "fig_cv_class_en.png"),
       "Figure 6-3. Peak classification over the rolling folds.")
table(["Test month", "City", "Event rate", "Brier", "PR-AUC", "F1"],
      [["Jun", "LOA", "4.5%", ".035", ".373", ".416"],
       ["Jul", "LOA", "4.5%", ".037", ".379", ".420"],
       ["Aug", "LOA", "2.0%", ".020", ".067", ".130"],
       ["Sep", "LOA", "8.5%", ".064", ".386", ".425"],
       ["Jun", "MEL", "7.8%", ".049", ".566", ".563"],
       ["Jul", "MEL", "4.8%", ".040", ".366", ".417"],
       ["Aug", "MEL", "5.9%", ".050", ".367", ".443"],
       ["Sep", "MEL", "4.6%", ".048", ".173", ".287"]],
      widths=[0.8, 0.8, 0.9, 0.9, 0.9, 0.9],
      caption_text="Table 6-2. Peak-classification results over the rolling folds.")
figure(os.path.join(FIG, "hb_confusion_LOA_en.png"),
       "Figure 6-4. Los Angeles confusion matrix for September: of 14,534 hours flagged as peaks, 5,500 are real (precision 37.8%).", width=3.4)
figure(os.path.join(FIG, "hb_confusion_MEL_en.png"),
       "Figure 6-5. Melbourne confusion matrix: precision 24.6%, recall 31.5%.", width=3.4)
p("How to read a confusion matrix: the top-left cell is 'no peak, correctly not flagged', bottom-right is 'peak, "
  "correctly flagged', top-right is a false alarm, bottom-left is a miss. For operations, false alarms waste dispatch "
  "resources while misses lose the warning — the trade-off must be chosen by the business, not by a single F1 value.")

h("6.4 The peak definition decides the conclusion", 2)
figure(os.path.join(FIG, "fig_peak_defs_en.png"),
       "Figure 6-6. Sensitivity to three peak definitions.")
table(["Definition", "Train rate", "Test rate", "Brier", "PR-AUC", "F1"],
      [["Rolling mean + 2σ", "3.9%", "8.3%", ".064", ".385", ".412"],
       ["Rolling median × 4", "7.9%", "12.7%", ".080", ".517", ".550"],
       ["Training-period P95", "2.2%", "2.4%", ".019", ".389", ".400"]],
      widths=[1.7, 0.9, 0.9, 0.8, 0.9, 0.8],
      caption_text="Table 6-3. Three definitions on Los Angeles in September.")
p("This is the easiest page to overlook and the most important: **the same word 'peak' produces a five-fold difference "
  "in event rate and changes the conclusion**. The 'adaptive' rolling threshold drifts with the overall level, so the "
  "test event rate doubles and calibration breaks. The static P95 keeps the rate almost unchanged (2.2% vs 2.4%) and "
  "has the best Brier score.")

h("6.5 Model comparison on identical test rows", 2)
figure(os.path.join(FIG, "fig_lstm_compare_en.png"),
       "Figure 6-7. Four models on the same test rows.")
table(["City", "t-24", "Ridge", "HGB", "LSTM", "LSTM 95% bootstrap CI"],
      [["LOA", ".281", ".167", ".203", ".153", "[0.13, 0.18]"],
       ["MEL", ".442", ".324", ".540", ".306", "[0.16, 0.44]"]],
      widths=[0.8, 0.9, 0.9, 0.9, 0.9, 2.0],
      caption_text="Table 6-4. WAPE and bootstrap intervals on identical test rows.")
p("Note the last column: although the LSTM has the lowest point estimate, its interval overlaps Ridge substantially. "
  "The statistically robust statement is therefore 'LSTM and Ridge both clearly beat the tree model', not 'LSTM is best'.")
figure(os.path.join(FIG, "fig_pred_vs_actual_en.png"),
       "Figure 6-8. Predicted versus actual volume (HGB, test set). Closer to the diagonal is better.")
p("How to read it: points near the red dashed line are accurate. The visible vertical stripes mean many sites sit at "
  "fixed levels for long periods — the 'flat site' phenomenon described earlier.")
figure(os.path.join(FIG, "fig_wape_hour_en.png"),
       "Figure 6-9. WAPE by hour. HGB beats t-24 at every hour of the day.")

# ===================== 7 error analysis =====================
h("7 Error Analysis: where and why the model fails", 1)
p("A single aggregate score is not enough. We need to know which observations carry the error before judging whether "
  "the model can be used in practice.")
figure(os.path.join(FIG, "fig_err_decile_en.png"),
       "Figure 7-1. Error by actual demand level (log scale).")
p("How to read it: test rows are grouped into ten bins by actual volume. The lowest bin (near-zero demand) is one to "
  "two orders of magnitude worse than the rest. Concretely, the lowest decile has WAPE 2.4–3.3 on Los Angeles (the model "
  "over-predicts by a factor of 2–3) and 87–354 on Melbourne. The model turns 'no charging' into a positive number, "
  "which is the classic zero-inflation problem.")
figure(os.path.join(FIG, "fig_err_bootstrap_en.png"),
       "Figure 7-2. WAPE with 95% intervals from 200 site-level bootstrap resamples.")
p("How to read it: each point is one resample and the vertical line is the 95% interval. Narrow intervals mean stable "
  "estimates. On Los Angeles the three models are almost non-overlapping (the differences are credible); on Melbourne "
  "the LSTM and Ridge intervals overlap heavily (the difference is not credible).")
figure(os.path.join(FIG, "fig_err_acf_en.png"),
       "Figure 7-3. Autocorrelation of the LSTM residuals.")
p("How to read it: if residuals were white noise, all bars would be near zero. The clear negative spike at lag 1 (−0.35) "
  "and positive spike at lag 24 (+0.29) mean the model over-corrects the previous hour and does not fully capture the "
  "daily cycle. This points to the next improvements: a two-part model, residual modelling, or stronger seasonal features.")
figure(os.path.join(FIG, "fig_error_size_en.png"),
       "Figure 7-4. Error by site size.")
p("How to read it: on Los Angeles larger sites are more accurate; on Melbourne larger sites are less accurate. The same "
  "model shows opposite patterns in the two cities, indicating different demand structures (large sites are steadier in "
  "Los Angeles and more volatile in Melbourne).")

# ===================== 8 interpretability =====================
h("8 Interpretability: what the model relies on", 1)
figure(os.path.join(FIG, "fig_importance_en.png"),
       "Figure 8-1. Permutation importance: how much the error rises when a column is shuffled.")
p("How to read it: the longer the bar, the more important the feature. The previous hour (t-1) dominates, followed by "
  "last week's value and the 24-hour rolling mean; POI density, area, longitude and latitude are almost invisible, so the "
  "model has not learned anything from spatial information.")
figure(os.path.join(FIG, "fig_pdp_en.png"),
       "Figure 8-2. Partial dependence: how the prediction changes when one feature is varied while others are held fixed.")
p("How to read it: a monotonically rising curve means 'the larger the feature, the larger the prediction', which matches "
  "intuition (more charging yesterday implies more today). The hour curve is U-shaped, meaning the model learns a "
  "'high at night, low at noon' pattern.")
callout("What does this mean for the project?",
        "Since the model relies almost entirely on autoregressive features, adding more site attributes, POIs or weather "
        "will not substantially improve accuracy. To go further, the direction is better temporal structure (two-part "
        "models, residual modelling) or longer history, rather than more static features.")

# ===================== 9 conclusions =====================
h("9 Conclusions and Answers to the Research Questions", 1)
p("Q1: Can historical data predict next-hour demand and peak events?", bold=True)
p("Yes, conditionally. In cities with genuine intraday dynamics (LOA, MEL), historical series support next-hour "
  "forecasting and all models beat the baseline. Peaks can be ranked, but probability reliability is limited by label "
  "drift. Cities such as Amsterdam, where the hourly data are degenerate, are unsuitable: the baseline WAPE is 0.6% and "
  "modelling is pointless.")
p("Q2: How accurate is next-hour demand prediction?", bold=True)
p("On the same test set, WAPE is 0.153 for Los Angeles (MAE about 1.10 kWh per site-hour) and 0.306 for Melbourne "
  "(MAE about 15.5 kWh), improving on the baseline by about 46% and 31%. Accuracy is highly uneven: WAPE is 0.11–0.40 in "
  "high-demand hours but 2.4–354 in near-zero hours.")
p("Q3: Can machine learning identify potential peak periods?", bold=True)
p("Yes for ranking, but not directly for probability. PR-AUC is 3–8 times the base rate and F1 is 0.42–0.43 on LOA. "
  "Because the peak rate varies between 2% and 8.5% across months, cross-month calibration degrades and August nearly "
  "fails. The conclusion also depends on the definition: +2σ drifts, P95 is most stable, and ×4 has the highest recall.")

# ===================== 10 limitations =====================
h("10 Limitations", 1)
bullet("The span is six months (April–September), so winter and seasonal extrapolation are not covered.")
bullet("The cities span both hemispheres: Melbourne is in autumn/winter during the same months, so seasons are not aligned.")
bullet("Weather was dropped because of time-zone ambiguity, so the models contain no meteorological input.")
bullet("Only LOA and MEL are modelled; AMS is excluded for data degradation and the rest are used only in ablations.")
bullet("The peak label is constructed by a threshold rule, not annotated in the data; different definitions give different conclusions.")
bullet("The LSTM was trained on a single fold (September) for 30 epochs, without early stopping or hyper-parameter search.")
bullet("Melbourne has only 62 sites, so city-level conclusions have wide confidence intervals.")

# ===================== 11 downstream =====================
h("11 Downstream Use: Poster, Paper and Talk", 1)
p("This chapter is for members who did not build the models but will use the results. All material is in figures/ and results/.")
h("11.1 Three-sentence summary (usable anywhere)", 2)
p("(1) In cities whose data quality allows it, historical charging data reduce next-hour demand error from 28%–44% to "
  "15%–31% relative to a naive baseline; (2) peak events can be ranked — the model puts more likely peak hours near the "
  "top — but the probabilities cannot be used across months without recalibration; (3) the binding constraints are data "
  "and definitions, not model capacity: hourly data quality differs by an order of magnitude across cities, and the "
  "choice of peak definition changes the conclusion.")
h("11.2 Poster plan", 2)
p("Use a three-block layout: data and question top-left, method top-right, results below. Three figures, three sentences:")
table(["Position", "Figure", "Caption"],
      [["Top-left", "Figure 2-2 (hour heatmap)", "Hourly data quality differs sharply: Amsterdam is flat, Melbourne has a clear noon peak."],
       ["Top-right", "Figure 3-1 (rolling validation) or 0-1 (pipeline)", "Rolling 4-fold with causal features avoids time leakage."],
       ["Bottom", "Figure 6-7 (model comparison)", "LSTM/Ridge cut WAPE from 0.28–0.44 to 0.15–0.31; trees overfit in the small city."],
       ["Bottom-right", "One-sentence conclusion", "Peaks can be ranked, not reported as probabilities; errors concentrate near zero demand."]],
      widths=[0.9, 2.5, 3.4],
      caption_text="Table 11-1. Poster material checklist.")
p("Layout advice: make the title a conclusion (not 'A study based on CHARGED'); write figure captions as conclusions, "
  "not labels; keep two decimals and put the data source and period in a corner.")
h("11.3 Paper structure", 2)
table(["Section", "What to write", "Figures and tables"],
      [["Introduction", "Why urban charging demand matters; gaps in existing datasets; the questions", "—"],
       ["Data", "CHARGED overview; six-city quality differences; why two cities", "Table 2-2, Figures 2-2, 2-4"],
       ["Methods", "Panel construction; feature engineering; peak definition; rolling split; models", "Table 3-1, Figures 3-1, 5-1"],
       ["Results – regression", "Baseline vs models; monthly variation; ablation", "Figures 6-1, Table 6-1, Figure 6-2"],
       ["Results – classification", "Ranking ability; confusion matrices; definition sensitivity", "Figures 6-3, 6-4/6-5, Table 6-3"],
       ["Error analysis", "Low-demand over-prediction; bootstrap; residual ACF", "Figures 7-1 to 7-4"],
       ["Discussion", "Interpretability; operational implications; limitations", "Figures 8-1, 8-2"],
       ["Conclusion", "Three answers plus one limitation", "—"]],
      widths=[1.2, 3.4, 2.2],
      caption_text="Table 11-2. Mapping from paper sections to project figures.")
p("Three points reviewers are likely to challenge; address them in the text: (1) why Amsterdam is excluded (with the "
  "quantitative evidence); (2) why peaks are not capacity-based (the capacity field is unusable, with a counter-example); "
  "(3) why the LSTM only marginally beats Ridge (overlapping bootstrap intervals, hence weak evidence).")
h("11.4 A 10-minute talk script", 2)
table(["Slide", "Content", "What to say", "Time"],
      [["1", "Title + one-sentence conclusion", "'We ask whether historical charging data can predict next-hour demand and peaks.'", "30 s"],
       ["2", "Dataset overview", "Six cities, 4,392 hours, 4,280 sites; but quality differs sharply.", "1 min"],
       ["3", "Evidence of quality differences", "Amsterdam: 94% of sites flat; the yesterday baseline already achieves 0.6%.", "1.5 min"],
       ["4", "Method pipeline", "Panel → features → rolling split → models → evaluation; emphasise causality and leakage control.", "1.5 min"],
       ["5", "Peak definition", "Rolling mean + 2σ; why capacity cannot be used.", "1 min"],
       ["6", "Regression results", "WAPE falls from .28–.44 to .15–.31; LSTM and Ridge are close, trees overfit in the small city.", "2 min"],
       ["7", "Classification results", "PR-AUC is 3–8× the base rate; August fails because the peak rate drifts.", "1.5 min"],
       ["8", "Errors and conclusions", "Errors concentrate near zero demand; three answers plus one limitation.", "1 min"]],
      widths=[0.5, 1.6, 3.9, 0.7],
      caption_text="Table 11-3. Talk script (compress to 5 minutes by dropping slides 4–5).")
h("11.5 Frequently asked questions", 2)
table(["Question", "Suggested answer"],
      [["Why only two cities?", "The other four either have almost no hourly variation (Amsterdam, 94%) or too few sites (Johannesburg, 35), so hourly modelling is not meaningful."],
       ["Why not random forest?", "It was tried and overfits more in the small city; HGB already represents the tree family and trains faster."],
       ["Why is the LSTM only slightly better than linear regression?", "The signal is mostly autoregressive (t-1 dominates), which a linear model already captures; the LSTM advantage is not statistically robust."],
       ["Why no weather?", "The timestamps are on different clocks: Los Angeles' charging peak is 13 hours from the solar peak, so alignment cannot be guaranteed."],
       ["Can the peak probability be used for alerts?", "Ranking yes, probability no: the peak rate moves from 2% to 8.5% across months, so calibration does not transfer. Online recalibration is required."],
       ["Is six months enough?", "Enough for short-term forecasting, not for seasonality or cross-city generalisation; it is listed as a limitation."],
       ["Where is the largest error?", "In near-zero hours, where the model turns 0 into a positive value; the error is 2–3× the true value on Los Angeles and much larger on Melbourne."],
       ["Can the results be reproduced?", "Yes: scripts, seeds and splits are fixed under scripts/; follow Appendix C."]],
      widths=[2.0, 4.8],
      caption_text="Table 11-4. FAQ and suggested answers.")

# ===================== 12 reproducibility =====================
h("12 Reproducibility", 1)
p("All processing and modelling steps are saved as scripts; data and results are separated and random seeds are fixed.")
table(["Script", "Purpose"],
      [["scripts/build_panel.py", "Build the site-hour panel (features and peak labels)"],
       ["scripts/rolling_cv.py", "Rolling 4-fold regression and classification"],
       ["scripts/ablation.py", "Single-city / pooled / +SZH ablation"],
       ["scripts/interpret.py", "Feature importance, partial dependence, error decomposition"],
       ["scripts/peak_defs.py", "Sensitivity to three peak definitions"],
       ["scripts/lstm_model.py", "LSTM training on GPU"],
       ["scripts/compare_lstm.py", "Aligned comparison on identical test rows"],
       ["scripts/error_analysis.py", "Decile errors, ACF, bootstrap intervals"],
       ["scripts/make_figures.py", "Data-characterisation figures"],
       ["scripts/make_handbook_figs.py", "Concept diagrams (Chinese edition)"],
       ["scripts/make_figures_en.py", "English versions of the report figures"],
       ["scripts/make_handbook_figs_en.py", "English versions of the handbook figures"]],
      widths=[2.5, 3.7],
      caption_text="Table 12-1. Scripts and execution order.")
table(["Item", "Version"],
      [["Python", "3.12.14"],
       ["pandas / numpy", "3.0.1 / 2.3.5"],
       ["scikit-learn", "1.9.1"],
       ["PyTorch", "2.14.1 + cu126 (RTX 3060 Laptop 6 GB)"],
       ["matplotlib", "3.11.2"]],
      widths=[1.8, 4.4],
      caption_text="Table 12-2. Runtime environment.")

# ===================== appendices =====================
h("Appendix A Glossary", 1)
table(["Term", "Explanation"],
      [["Panel data", "The same objects observed repeatedly over time (here: sites × hours)."],
       ["Lag", "A value from a past moment copied into the current row, e.g. lag24 = 24 hours ago."],
       ["Rolling window", "A fixed-length window ending at the current moment, used for means and standard deviations."],
       ["Data leakage", "Using information that would not be available at prediction time, inflating the evaluation."],
       ["Overfitting", "Memorising noise in the training data, leading to poor performance on new data."],
       ["WAPE", "Total absolute error divided by total actual value; scale-free."],
       ["Brier score", "Mean squared error of a probability forecast."],
       ["PR-AUC", "Ranking quality when positives are rare."],
       ["Calibration", "Making '30% predicted' events happen about 30% of the time."],
       ["Bootstrap", "Resampling with replacement to estimate confidence intervals."],
       ["ACF", "Autocorrelation function: correlation of a series with its lagged self."],
       ["z-score", "Subtract the mean and divide by the standard deviation."]],
      widths=[1.6, 5.2],
      caption_text="Table A-1. Glossary.")

h("Appendix B Data Dictionary", 1)
table(["Table", "Field", "Meaning"],
      [["volume.csv", "index = time, columns = site_id", "Hourly charging volume (kWh) per site"],
       ["duration.csv", "same", "Hourly charging duration (hours)"],
       ["e_price.csv / s_price.csv", "same", "Electricity / service price (local currency per kWh)"],
       ["sites.csv", "site_id, longitude, latitude, charger_num, total_duration, total_volume, avg_power, perimeter, area", "Site list. **total_* and avg_power are period aggregates and must not be used as features**"],
       ["chargers.csv", "charger_id, longitude, latitude, site_id, total_duration, total_volume, avg_power", "Charger list"],
       ["distance.csv", "rows and columns are site_id", "Geodesic distance (km), symmetric"],
       ["weather.csv", "time, temp, feelslike, humidity, dew, precip, snow, snowdepth, preciptype, windgust, windspeed, winddir, pressure, visibility, cloudcover, solarradiation, solarenergy, uvindex, conditions", "Hourly weather"],
       ["poi.csv", "(index), type, longitude, latitude", "OpenStreetMap points of interest"],
       ["info.csv", "city, country, abbreviation, total_chargers, total_sites, DBSCAN_eps, total_duration, total_volume, avg_power", "City-level metadata"]],
      widths=[1.4, 2.8, 2.8],
      caption_text="Table B-1. Data dictionary.")

h("Appendix C Figure Index", 1)
table(["Figure", "File", "Best used in"],
      [["Pipeline", "en/hb_pipeline_en.png", "Methods overview, poster"],
       ["Timeline", "en/hb_timeline_en.png", "Methods"],
       ["Peak definition", "en/hb_peak_definition_en.png", "Peak-definition section"],
       ["LSTM architecture", "en/hb_lstm_arch_en.png", "Model section"],
       ["Hour heatmap", "en/fig3_hour_heatmap_en.png", "Data section, poster"],
       ["Rolling WAPE", "en/fig_cv_wape_en.png", "Results, poster"],
       ["Model comparison", "en/fig_lstm_compare_en.png", "Results, poster"],
       ["Peak definition sensitivity", "en/fig_peak_defs_en.png", "Results"],
       ["Decile error", "en/fig_err_decile_en.png", "Error analysis"],
       ["Bootstrap", "en/fig_err_bootstrap_en.png", "Error analysis"],
       ["Residual ACF", "en/fig_err_acf_en.png", "Error analysis"],
       ["Importance", "en/fig_importance_en.png", "Interpretability"],
       ["Confusion matrices", "en/hb_confusion_LOA_en.png / MEL", "Results"]],
      widths=[1.8, 3.0, 2.0],
      caption_text="Table C-1. Figure index. All files live under figures/en/.")

doc.save(os.path.join(OUT, "EV_Charging_Project_Handbook_EN.docx"))
print("saved")
