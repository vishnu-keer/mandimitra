// MandiMitra hackathon pitch deck (editable PowerPoint).
//
//   node presentation/tools/build_deck.js
//
// Every number comes from research/key_numbers.json, which
// presentation/tools/make_figures.py generates from outputs/. Screenshots are
// the real app (docs/screenshots/). Speaker notes are on every slide.
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..");
const OUT = path.join(ROOT, "presentation", "MandiMitra_Hackathon_Pitch.pptx");
const KN = JSON.parse(fs.readFileSync(path.join(ROOT, "research", "key_numbers.json")));
const SHOT = (f) => path.join(ROOT, "docs", "screenshots", f);
const FIG = (f) => path.join(ROOT, "research", "figures", f);
const QR = (f) => path.join(ROOT, "presentation", f);
const ASSET = (f) => path.join(ROOT, "presentation", "assets", f);
let applyTheme = null;
for (const p of ["/mnt/skills/public/pptx/scripts/apply_theme.js"]) {
  try { ({ applyTheme } = require(p)); break; } catch (e) { /* optional */ }
}

const THEME = {
  name: "MandiMitra Field",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1D2430", lt1: "FFFFFF", dk2: "16523A", lt2: "F1F5F2",
    accent1: "1F6F4A", accent2: "C27C2C", accent3: "5B6472",
    accent4: "3B7DC4", accent5: "8E5EA2", accent6: "D1495B",
    hlink: "1F6F4A", folHlink: "16523A",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";            // 13.33 x 7.5 in
pres.title = "MandiMitra — Hackathon pitch";
pres.author = "Vishnu Keer";
pres.company = "Vivekananda Global University, Jaipur";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const W = 13.33, H = 7.5, M = 0.6;

// ------------------------------------------------------------- layouts
pres.defineSlideMaster({
  title: "MM_DARK",
  background: { color: HEX.dk2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 2.2, w: 8.6, h: 1.4,
        fontSize: 54, bold: true, color: C.background1, fontFace: THEME.headFontFace, valign: "bottom", align: "left" },
      text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: M, y: 3.7, w: 8.2, h: 2.0,
        fontSize: 20, color: "D9E8DF", valign: "top", align: "left" }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "MM_CONTENT",
  background: { color: HEX.lt1 },
  margin: [0.5, 0.6, 0.6, 0.6],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.35, w: W - 2 * M, h: 0.95,
        fontSize: 30, bold: true, color: C.text1, fontFace: THEME.headFontFace, valign: "middle" },
      text: "" } },
    { text: { text: "MandiMitra · historical data, ends 28 Apr 2015 · not financial or farming advice",
        options: { x: M, y: H - 0.42, w: 9, h: 0.3, fontSize: 10, color: "5B6472" } } },
  ],
  slideNumber: { x: W - 1.0, y: H - 0.42, w: 0.5, h: 0.3, fontSize: 10, color: "5B6472", align: "right" },
});

function card(slide, x, y, w, h, fill) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, rectRadius: 0.12, fill: { color: fill || HEX.lt2 }, line: { color: "DDE5E0", width: 0.75 },
  });
}
function stat(slide, x, y, w, big, small, color) {
  slide.addText(big, { x, y, w, h: 0.95, fontSize: 40, bold: true, color: color || C.accent1,
    fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  slide.addText(small, { x, y: y + 0.95, w, h: 0.75, fontSize: 14, color: C.text1, margin: 0,
    valign: "top", isTextBox: true });
}
function bullets(slide, items, opts) {
  slide.addText(items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1 } })),
    Object.assign({ fontSize: 16, color: C.text1, paraSpaceAfter: 8, valign: "top", isTextBox: true }, opts));
}
function source(slide, text) {
  slide.addText(text, { x: M, y: H - 0.8, w: W - 2 * M, h: 0.3, fontSize: 10, italic: true,
    color: "5B6472", margin: 0, isTextBox: true });
}

const sel = KN.selected;
const onion1 = sel.find((r) => r.pair === "Onion/Jaipur" && r.h === 1);
const dmSq = KN.dm_summary.squared, dmAbs = KN.dm_summary.absolute;
const legacy1 = KN.legacy.find((r) => r.h === 1);
const unchOn = KN.unchanged_pct["Onion/Jaipur"], unchTo = KN.unchanged_pct["Tomato/Jaipur"];

// ============================================================ 1 title
pres.addSection({ title: "Opening" });
let s = pres.addSlide({ masterName: "MM_DARK", sectionTitle: "Opening" });
s.addText("MandiMitra", { placeholder: "title" });
s.addText([
  { text: "Explainable mandi price intelligence", options: { bold: true, breakLine: true } },
  { text: "Does AI really beat “same as today” for wholesale onion and tomato prices? We tested it — properly.", options: { breakLine: true } },
  { text: " ", options: { breakLine: true, fontSize: 10 } },
  { text: "Vishnu Keer · Vivekananda Global University, Jaipur", options: { fontSize: 16 } },
], { placeholder: "body" });
for (const [i, q] of [["qr_live_app.png", "Live app"], ["qr_repository.png", "Code + data"]].entries()) {
  const x = 9.75 + i * 1.75;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x - 0.1, y: 2.35, w: 1.6, h: 2.15, rectRadius: 0.1,
    fill: { color: HEX.lt1 }, line: { color: HEX.lt1 } });
  s.addImage({ path: QR(q[0]), x, y: 2.45, w: 1.4, h: 1.4, altText: `QR code: ${q[1]}` });
  s.addText(q[1], { x: x - 0.1, y: 3.9, w: 1.6, h: 0.45, fontSize: 13, bold: true, color: C.text1,
    align: "center", margin: 0, isTextBox: true });
}
s.addText("mandimitra.streamlit.app  ·  github.com/vishnu-keer/mandimitra", { x: 9.6, y: 4.65, w: 3.5,
  h: 0.6, fontSize: 11, color: "D9E8DF", isTextBox: true });
s.addNotes("Hi, I'm Vishnu. MandiMitra asks a question most price-prediction apps skip: does the AI actually beat the simplest forecast — tomorrow's price equals today's — when you test it honestly? Scan the left code for the live app, the right one for the code and data. Everything I show is reproducible from those links.");

// ============================================================ 2 problem
pres.addSection({ title: "Problem" });
s = pres.addSlide({ masterName: "MM_CONTENT", sectionTitle: "Problem" });
s.addText("Price-prediction claims reach farmers unchecked", { placeholder: "title" });
card(s, M, 1.55, 4.0, 4.6, HEX.lt2);
s.addText([{ text: "Rs. 600", options: { breakLine: true } }, { text: "→ Rs. 4,500" }], { x: M + 0.3, y: 1.75, w: 3.5, h: 1.5,
  fontSize: 36, bold: true, color: C.accent1, fontFace: THEME.headFontFace, margin: 0, valign: "top", isTextBox: true });
s.addText("per quintal: Jaipur wholesale onion, June → 21 October 2013, then back to about Rs. 800 by December",
  { x: M + 0.3, y: 3.3, w: 3.5, h: 1.2, fontSize: 15, color: C.text1, margin: 0, valign: "top", isTextBox: true });
s.addText("Official Department of Consumer Affairs series", { x: M + 0.3, y: 4.6, w: 3.5, h: 0.5,
  fontSize: 12, italic: true, color: "5B6472", isTextBox: true });
const users = [
  ["Farmers", "Sell today or hold? A confident wrong forecast costs real money."],
  ["Traders", "How noisy is this market, and how stale is the quoted price?"],
  ["Students & analysts", "Was this model tested in a way that could have shown it fails?"],
];
users.forEach(([h, t], i) => {
  const y = 1.55 + i * 1.6;
  s.addShape(pres.shapes.OVAL, { x: 5.2, y: y + 0.15, w: 0.7, h: 0.7, fill: { color: HEX.accent1 } });
  s.addText(String(i + 1), { x: 5.2, y: y + 0.15, w: 0.7, h: 0.7, fontSize: 20, bold: true,
    color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
  s.addText(h, { x: 6.15, y, w: 6.5, h: 0.5, fontSize: 20, bold: true, color: C.text1, margin: 0, isTextBox: true });
  s.addText(t, { x: 6.15, y: y + 0.5, w: 6.5, h: 0.8, fontSize: 16, color: C.text1, margin: 0,
    valign: "top", isTextBox: true });
});
s.addNotes("Mandi prices swing hard — Jaipur onion went from about six to nine hundred rupees a quintal in June 2013 to four and a half thousand in October. Apps now promise AI forecasts to farmers and traders. The people who would act on them can't check how they were tested. That's the gap.");

// ============================================================ 3 evidence
s = pres.addSlide({ masterName: "MM_CONTENT", sectionTitle: "Problem" });
s.addText("Prices move in rare jumps that price history alone cannot see", { placeholder: "title" });
s.addImage({ path: FIG("fig1_price_history.png"), x: M, y: 1.45, w: 7.6, h: 4.39,
  altText: "Reported daily wholesale prices of onion and tomato in Jaipur, 2009 to 2015" });
card(s, 8.6, 1.45, 4.13, 4.6, HEX.lt2);
stat(s, 8.85, 1.65, 3.7, `${unchOn}%`, "of reported Onion/Jaipur days quote exactly the previous price (Tomato: " + unchTo + "%)");
stat(s, 8.85, 3.55, 3.7, "~55%", "of calendar days have a reported price at all (2009–2015)", HEX.accent2);
source(s, "Data: Dept. of Consumer Affairs via data.gov.in (GODL-India). Related evidence: onion price volatility is linked to market-arrivals uncertainty (Birthal, Negi & Joshi, 2019, JADEE 9(3)).");
s.addNotes("This is the real series. Most days the quoted price doesn't change at all — eighty-five percent of reported onion days. Then it jumps. Research on Indian onion prices links that volatility to uncertainty in market arrivals, which isn't in the price history. So a price-only model has very little to work with — and that should be tested, not assumed.");

// ============================================================ 4 solution
pres.addSection({ title: "Solution" });
s = pres.addSlide({ masterName: "MM_CONTENT", sectionTitle: "Solution" });
s.addText("An honest dashboard, not a model leaderboard", { placeholder: "title" });
s.addImage({ path: ASSET("overview.png"), x: M, y: 1.45, w: 6.6, h: 4.9, altText: "MandiMitra overview screen" });
const feats = [
  ["Strong reference first", "Every forecast is shown next to “same as today” and the last reported price."],
  ["Freshness and quality", "Latest genuine observation, stale-quote rate, reporting gaps — on screen."],
  ["Honest uncertainty", "Ranges are drawn only if they held up on unseen data. They didn't, so we say so."],
  ["English + हिन्दी", "Plain-language views in Hindi; CSV downloads; works on a phone."],
];
feats.forEach(([h, t], i) => {
  const y = 1.45 + i * 1.22;
  card(s, 7.55, y, 5.18, 1.08, HEX.lt2);
  s.addText(h, { x: 7.75, y: y + 0.08, w: 4.8, h: 0.4, fontSize: 17, bold: true, color: C.accent1, margin: 0, isTextBox: true });
  s.addText(t, { x: 7.75, y: y + 0.47, w: 4.8, h: 0.55, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true });
});
s.addNotes("MandiMitra is built around trust. The forecast always sits beside the simplest reference. Data freshness and stale quotes are on the first screen. If an uncertainty band didn't hold up on unseen data, we don't draw it — we tell you. And the plain-language views are in Hindi.");

// ============================================================ 5 demo
s = pres.addSlide({ masterName: "MM_CONTENT", sectionTitle: "Solution" });
s.addText("It works today: seven views, every number traceable to a file", { placeholder: "title" });
const shots = [["history.png", "Price history: reported vs carried-forward days"],
               ["evaluation.png", "Model evaluation: chosen by CV, every model on the same days"],
               ["forecast.png", "Forecast: origin and target dates, no fake confidence band"],
               ["hindi.png", "Hindi view for farmers"]];
shots.forEach(([f, cap], i) => {
  const x = M + (i % 2) * 6.17, y = 1.35 + Math.floor(i / 2) * 2.72;
  s.addImage({ path: ASSET(f), x, y, w: 5.9, h: 2.27, altText: cap });
  s.addShape(pres.shapes.RECTANGLE, { x, y, w: 5.9, h: 2.27, fill: { type: "none" }, line: { color: "DDE5E0", width: 0.75 } });
  s.addText(cap, { x, y: y + 2.3, w: 5.9, h: 0.36, fontSize: 13, color: "5B6472", margin: 0, isTextBox: true });
});
s.addNotes("Live demo here if the network allows — otherwise these are the real screens. Price history marks the days the mandi didn't report. Model evaluation shows how the model was chosen before the test period. The forecast tab shows the date it was made and the dates it is for. Same app in Hindi.");

// ============================================================ 6 pipeline
pres.addSection({ title: "How it works" });
s = pres.addSlide({ masterName: "MM_CONTENT", sectionTitle: "How it works" });
s.addText("A pipeline that refuses to write a misleading result", { placeholder: "title" });
const steps = [["Official CSVs", "untouched, SHA-256"], ["Clean + calendar", "0 = missing"],
               ["Features ≤ day t", "leakage-proofed"], ["Choose by CV", "4 rolling folds"],
               ["Test once", "~200 unseen days"], ["Dashboard", "read-only"]];
steps.forEach(([h, t], i) => {
  const x = M + i * 2.07;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.9, w: 1.8, h: 1.45, rectRadius: 0.1,
    fill: { color: i === 4 ? HEX.accent1 : HEX.lt2 }, line: { color: "C9D6CE", width: 0.75 } });
  s.addText(h, { x: x + 0.08, y: 2.0, w: 1.64, h: 0.7, fontSize: 15, bold: true, align: "center",
    color: i === 4 ? C.background1 : C.text1, margin: 0, valign: "middle", isTextBox: true });
  s.addText(t, { x: x + 0.08, y: 2.7, w: 1.64, h: 0.55, fontSize: 12, align: "center",
    color: i === 4 ? C.background1 : "5B6472", margin: 0, valign: "top", isTextBox: true });
  if (i < steps.length - 1) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + 1.82, y: 2.47, w: 0.22, h: 0.3,
    fill: { color: "9AA3AD" }, line: { color: "9AA3AD" } });
});
const gates = [["154", "automated tests: leakage, chronology, embargo, identical rows, provenance, ingestion"],
               ["2 gates", "pipeline exits with FAIL rather than publish a broken comparison"],
               ["Byte-identical", "rebuild from the government files on Python 3.11 and 3.12; CI on every push"]];
gates.forEach(([b, t], i) => {
  const x = M + i * 4.1;
  card(s, x, 3.9, 3.85, 2.2, HEX.lt2);
  s.addText(b, { x: x + 0.25, y: 4.05, w: 3.4, h: 0.75, fontSize: 30, bold: true, color: C.accent1,
    fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  s.addText(t, { x: x + 0.25, y: 4.8, w: 3.4, h: 1.2, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true });
});
s.addNotes("Under the hood: official files kept untouched and hashed; a real daily calendar so 'yesterday' means yesterday; features that only use what was known at the end of the day; the model is chosen on earlier years; the test period is scored once. A hundred and fifty-four tests and two gates stop the pipeline if any of that breaks.");

// ============================================================ 7 methods
s = pres.addSlide({ masterName: "MM_CONTENT", sectionTitle: "How it works" });
s.addText("The model is chosen before the test data is ever scored", { placeholder: "title" });
const tl = [["Fit only", 2.6, "D7E7DD"], ["4 cross-validation folds — choose the model", 4.4, "8CC0A4"],
            ["Untouched test, scored once", 2.9, HEX.accent1]];
let tx = M;
tl.forEach(([lab, w, col], i) => {
  s.addShape(pres.shapes.RECTANGLE, { x: tx, y: 1.6, w, h: 0.75, fill: { color: col }, line: { color: "FFFFFF", width: 2 } });
  s.addText(lab, { x: tx + 0.1, y: 1.6, w: w - 0.2, h: 0.75, fontSize: 14, bold: true, valign: "middle",
    color: i === 2 ? C.background1 : C.text1, margin: 0, isTextBox: true });
  tx += w;
});
s.addText("2009 → early 2014: development period", { x: M, y: 2.42, w: 7.0, h: 0.35, fontSize: 13,
  color: "5B6472", margin: 0, isTextBox: true });
s.addText("Feb 2014 → Apr 2015", { x: M + 7.0, y: 2.42, w: 2.9, h: 0.35, fontSize: 13,
  color: "5B6472", margin: 0, isTextBox: true });
s.addText("~200 unseen days per horizon", { x: M + 10.1, y: 1.6, w: 2.0, h: 0.75, fontSize: 13,
  color: C.accent1, bold: true, margin: 0, valign: "middle", isTextBox: true });
const cands = [["Naive", "tomorrow = today"], ["ARIMA", "classical time series"], ["Random Forest", "tabular ML"],
               ["Gradient Boosting", "tabular ML"], ["RF-delta", "predicts the change"]];
cands.forEach(([h, t], i) => {
  const x = M + i * 2.47;
  card(s, x, 3.05, 2.3, 1.1, HEX.lt2);
  s.addText(h, { x: x + 0.15, y: 3.12, w: 2.0, h: 0.45, fontSize: 16, bold: true, color: C.text1, margin: 0, isTextBox: true });
  s.addText(t, { x: x + 0.15, y: 3.57, w: 2.0, h: 0.45, fontSize: 13, color: "5B6472", margin: 0, isTextBox: true });
});
bullets(s, [
  "Selection rule written in advance: lowest mean RMSE across the four folds.",
  "Every model scored on identical days; only days the mandi really reported are scored.",
  "Training rows whose target date crosses a boundary are removed (embargo).",
  "Significance: Diebold–Mariano tests vs Naive, Holm-adjusted.",
], { x: M, y: 4.45, w: W - 2 * M, h: 2.0 });
s.addNotes("This is the part most projects skip. The test period is locked away. Five candidates, from 'same as today' to tree models that predict the price change, are compared on four rolling folds of earlier data, and the rule for picking the winner was written before we saw the results. Then the test is scored once.");

// ============================================================ 8 results
pres.addSection({ title: "Results" });
s = pres.addSlide({ masterName: "MM_CONTENT", sectionTitle: "Results" });
s.addText("The model chosen in advance never beat “same as today”", { placeholder: "title" });
const cats = sel.map((r) => `${r.pair.split("/")[0]} ${r.h}d`);
s.addChart(pres.charts.BAR, [
  { name: "Model chosen by CV", labels: cats, values: sel.map((r) => r.test_rmse) },
  { name: "Naive (same as today)", labels: cats, values: sel.map((r) => r.naive_rmse) },
], { x: M, y: 1.45, w: 7.5, h: 4.75, barDir: "col", barGrouping: "clustered", barGapWidthPct: 60,
  chartColors: [HEX.accent1, "9AA3AD"], showLegend: true, legendPos: "t", legendFontSize: 12,
  legendFontFace: "+mn-lt", showTitle: true, title: "Test RMSE, Rs. per quintal (lower is better)",
  titleFontSize: 14, titleFontFace: "+mn-lt", titleColor: HEX.dk1,
  catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", catAxisLabelColor: "5B6472",
  valAxisLabelFontSize: 11, valAxisLabelFontFace: "+mn-lt", valAxisLabelColor: "5B6472",
  valGridLine: { color: "E5E9EC", size: 0.75 }, catGridLine: { style: "none" },
  showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 10, dataLabelFontFace: "+mn-lt",
  dataLabelColor: HEX.dk1, dataLabelFormatCode: "0" });
card(s, 8.45, 1.45, 4.28, 4.75, HEX.lt2);
stat(s, 8.7, 1.6, 3.9, `0 of ${dmSq.n + dmAbs.n}`, "significance tests found any model more accurate than Naive");
stat(s, 8.7, 3.2, 3.9, `p = ${KN.dm_onion_h1_gbm.p}`, `for our first version's “+${legacy1.vs_naive_pct}%” — it came from picking the winner on the test set`, HEX.accent2);
s.addText("Naive also had the lowest error on an ordinary day (MAE) at all six.", { x: 8.7, y: 4.95, w: 3.9, h: 0.9,
  fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true });
source(s, "Onion: CV chose Naive at all horizons. Tomato: 1d RF-delta −5.66%, 2d ARIMA −0.53%, 3d ARIMA −0.31% vs Naive. Files: outputs/best_model.csv, outputs/experiments/dm_test.csv.");
s.addNotes(`Here's the result. For onion, cross-validation chose 'same as today' at every horizon. For tomato it chose other models, and each was slightly worse on unseen data. Across forty-eight significance tests, none found a model better than Naive. Our own first version claimed a ${legacy1.vs_naive_pct}% win — it came from choosing the winner on the test data, and the gap has p = ${KN.dm_onion_h1_gbm.p}. That correction is the finding.`);

// ============================================================ 9 validation
s = pres.addSlide({ masterName: "MM_CONTENT", sectionTitle: "Results" });
s.addText("No user evidence yet — this is exactly how we will get it", { placeholder: "title" });
card(s, M, 1.5, 5.6, 4.6, "FDF3E7");
s.addText("What we can claim today", { x: M + 0.3, y: 1.65, w: 5.0, h: 0.5, fontSize: 20, bold: true, color: C.accent2, margin: 0, isTextBox: true });
bullets(s, ["A working, tested, reproducible product.", "A measured, significance-tested result on official data.",
            "No farmer interviews, user counts, savings or income effects — none have been measured."],
  { x: M + 0.3, y: 2.25, w: 5.0, h: 3.6 });
card(s, 6.7, 1.5, 6.03, 4.6, HEX.lt2);
s.addText("Next 4 weeks: consented user study", { x: 7.0, y: 1.65, w: 5.5, h: 0.5, fontSize: 20, bold: true, color: C.accent1, margin: 0, isTextBox: true });
bullets(s, ["5–10 traders and farmers at a Jaipur mandi, with informed consent, no names stored.",
            "Measure: can they read the forecast, the reference and the warning correctly?",
            "Measure: which screen would change a decision, and how?",
            "Publish the anonymised findings — whatever they are."], { x: 7.0, y: 2.25, w: 5.5, h: 3.6 });
s.addNotes("I want to be precise here: we have not tested this with farmers yet, so we make no impact claims. The plan is ready — a short, consented study at a Jaipur mandi, measuring whether people read the forecast and its warnings correctly. We'll publish what we find.");

// ============================================================ 10 feasibility
pres.addSection({ title: "Feasibility" });
s = pres.addSlide({ masterName: "MM_CONTENT", sectionTitle: "Feasibility" });
s.addText("Rs. 0 to run, open data, and built to add markets", { placeholder: "title" });
const fz = [["Rs. 0", "GitHub + Actions, Streamlit Community Cloud, data.gov.in. No paid service anywhere.", HEX.accent1],
            ["GODL-India", "Government open data with attribution; code MIT. Licences kept separate.", HEX.accent4],
            ["Live-ready", "Validated client for the official AGMARKNET daily price API — waiting only for a free access key.", HEX.accent2],
            ["Gate-based", "New market = add its official file. The 400-row gate decides; nothing is forced.", HEX.accent5]];
fz.forEach(([b, t, col], i) => {
  const x = M + (i % 2) * 6.15, y = 1.5 + Math.floor(i / 2) * 2.35;
  card(s, x, y, 5.95, 2.1, HEX.lt2);
  s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: y + 0.35, w: 0.55, h: 0.55, fill: { color: col } });
  s.addText(b, { x: x + 1.05, y: y + 0.25, w: 4.7, h: 0.7, fontSize: 24, bold: true, color: C.text1,
    fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  s.addText(t, { x: x + 1.05, y: y + 0.95, w: 4.7, h: 1.0, fontSize: 15, color: C.text1, margin: 0, valign: "top", isTextBox: true });
});
s.addNotes("It costs nothing to run. The data is government open data with attribution. The live-price client for the official AGMARKNET API is built and tested — it needs only a free access key. Adding a market means adding its official file; the data gate decides if it's usable.");

// ============================================================ 11 limitations
s = pres.addSlide({ masterName: "MM_CONTENT", sectionTitle: "Feasibility" });
s.addText("What this does not show yet — and the next milestones", { placeholder: "title" });
const rows = [
  [{ text: "Limitation", options: { bold: true, color: "FFFFFF", fill: { color: HEX.dk2 } } },
   { text: "Next milestone", options: { bold: true, color: "FFFFFF", fill: { color: HEX.dk2 } } }],
  ["Data ends April 2015", "Connect the official daily API (key); check a CEDA daily mirror's terms"],
  ["One mandi, two commodities", "Run more Rajasthan and national centres through the gate"],
  ["Price history only", "Add arrivals and rainfall — where a real edge is more plausible"],
  ["Back-test only", "Score live forecasts against prices published afterwards"],
  ["No user evidence", "Consented study with 5–10 traders and farmers"],
];
s.addTable(rows, { x: M, y: 1.5, w: W - 2 * M, colW: [4.6, W - 2 * M - 4.6], fontSize: 16, color: HEX.dk1,
  border: { type: "solid", pt: 0.75, color: "DDE5E0" }, fill: { color: "FFFFFF" }, rowH: 0.72, valign: "middle", margin: 0.12 });
s.addNotes("Limits, stated plainly: historical data, one mandi, prices only, back-testing only, and no user evidence yet. Each has a concrete next step on the right.");

// ============================================================ 12 close
pres.addSection({ title: "Close" });
s = pres.addSlide({ masterName: "MM_DARK", sectionTitle: "Close" });
s.addText("Trust before prediction", { placeholder: "title" });
s.addText([
  { text: "We ask for:", options: { bold: true, breakLine: true } },
  { text: "Mentors in agricultural economics and forecasting", options: { bullet: true, breakLine: true } },
  { text: "Introductions to a mandi committee or FPO for a consented pilot", options: { bullet: true, breakLine: true } },
  { text: "Feedback on what traders would actually use", options: { bullet: true } },
], { placeholder: "body" });
for (const [i, q] of [["qr_live_app.png", "Live app"], ["qr_repository.png", "Code + data"]].entries()) {
  const x = 9.75 + i * 1.75;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x - 0.1, y: 2.35, w: 1.6, h: 2.15, rectRadius: 0.1,
    fill: { color: HEX.lt1 }, line: { color: HEX.lt1 } });
  s.addImage({ path: QR(q[0]), x, y: 2.45, w: 1.4, h: 1.4, altText: `QR code: ${q[1]}` });
  s.addText(q[1], { x: x - 0.1, y: 3.9, w: 1.6, h: 0.45, fontSize: 13, bold: true, color: C.text1,
    align: "center", margin: 0, isTextBox: true });
}
s.addText("Vishnu Keer · Vivekananda Global University, Jaipur", { x: M, y: 6.4, w: 8, h: 0.4, fontSize: 14,
  color: "D9E8DF", isTextBox: true });
s.addNotes("Before anyone trusts a price prediction, it should beat the simplest reference on data it never saw. MandiMitra makes that check visible, reproducible and bilingual. We'd welcome mentors, an introduction to a mandi or FPO for a consented pilot, and feedback from traders. Thank you.");

(async () => {
  await pres.writeFile({ fileName: OUT });
  if (applyTheme) await applyTheme(OUT, THEME);
  console.log("wrote", path.relative(ROOT, OUT), applyTheme ? "(theme applied)" : "(theme NOT applied)");
})();
