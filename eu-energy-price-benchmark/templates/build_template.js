/**
 * Builds the report template that src/build_deck.py fills in.
 *
 * The template is deliberately a separate artefact: in a company it arrives from
 * the brand team as a read-only .pptx and the generator is not allowed to invent
 * layout. It defines the contract:
 *
 *   {{TOKEN}}        - text replaced with a value
 *   {{CHART:name}}   - placeholder box replaced with a rendered chart
 *
 * Run: node templates/build_template.js
 */

const pptxgen = require("pptxgenjs");
const path = require("path");

const NAVY = "12243A";
const INK = "1A1A1A";
const MUTED = "43525F";
const TINT = "F2F5F8";
const RULE = "DDE3E9";
const ACCENT = "2A78D6";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";           // 13.3 x 7.5in - must precede addSlide
pres.author = "Market analysis";
pres.title = "Industrial energy price benchmark";

const W = 13.3;
const M = 0.7;

function title(slide, token) {
  slide.addText(token, {
    x: M, y: 0.45, w: W - 2 * M, h: 0.8, fontFace: "Cambria", fontSize: 30,
    bold: true, color: NAVY, isTextBox: true, margin: 0,
  });
}

function lede(slide, token) {
  slide.addText(token, {
    x: M, y: 1.24, w: W - 2 * M, h: 0.4, fontFace: "Calibri", fontSize: 14,
    color: MUTED, isTextBox: true, margin: 0,
  });
}

function footer(slide, page) {
  slide.addText("Source: Eurostat  |  {{PERIOD}}  |  Non-household consumers, excluding VAT", {
    x: M, y: 7.0, w: 10, h: 0.3, fontFace: "Calibri", fontSize: 10.5,
    color: MUTED, isTextBox: true, margin: 0,
  });
  slide.addText(String(page), {
    x: W - M - 0.6, y: 7.0, w: 0.6, h: 0.3, fontFace: "Calibri", fontSize: 10.5,
    color: MUTED, align: "right", isTextBox: true, margin: 0,
  });
}

function chartSlide(name, page) {
  const s = pres.addSlide();
  title(s, `{{S${page}_TITLE}}`);
  lede(s, `{{S${page}_LEDE}}`);
  const box = { x: M, y: 1.8, w: 8.5, h: 4.75 };
  s.addShape(pres.ShapeType.rect, { ...box, fill: { color: TINT }, line: { color: RULE, width: 1 } });
  s.addText(`{{CHART:${name}}}`, {
    ...box, fontFace: "Calibri", fontSize: 13, color: MUTED, align: "center",
    valign: "middle", isTextBox: true, margin: 0,
  });
  s.addShape(pres.ShapeType.roundRect, {
    x: M + 8.85, y: 1.8, w: W - 2 * M - 8.85, h: 4.75, rectRadius: 0.08,
    fill: { color: TINT }, line: { color: RULE, width: 1 },
  });
  s.addText("WHAT THIS SHOWS", {
    x: M + 9.1, y: 2.05, w: 2.5, h: 0.3, fontFace: "Calibri", fontSize: 11.5,
    bold: true, color: MUTED, isTextBox: true, margin: 0,
  });
  s.addText(`{{S${page}_TAKEAWAY}}`, {
    x: M + 9.1, y: 2.45, w: 2.5, h: 3.85, fontFace: "Calibri", fontSize: 13,
    color: INK, valign: "top", isTextBox: true, margin: 0,
  });
  footer(s, page);
}

// ------------------------------------------------------------------ 1. title
const s1 = pres.addSlide();
s1.background = { color: NAVY };
s1.addText("{{DECK_TITLE}}", {
  x: M, y: 2.3, w: W - 2 * M - 1.5, h: 1.6, fontFace: "Cambria", fontSize: 40,
  bold: true, color: "FFFFFF", isTextBox: true, margin: 0,
});
s1.addText("{{SUBTITLE}}", {
  x: M, y: 3.95, w: 9.5, h: 0.9, fontFace: "Calibri", fontSize: 16,
  color: "9FB3C8", isTextBox: true, margin: 0,
});
s1.addText("{{SOURCE_LINE}}", {
  x: M, y: 6.5, w: 8.5, h: 0.4, fontFace: "Calibri", fontSize: 12,
  color: "9FB3C8", isTextBox: true, margin: 0,
});
s1.addText("{{GENERATED}}", {
  x: W - M - 4, y: 6.5, w: 4, h: 0.4, fontFace: "Calibri", fontSize: 12,
  color: "9FB3C8", align: "right", isTextBox: true, margin: 0,
});

// ---------------------------------------------------------------- 2. headline
const s2 = pres.addSlide();
title(s2, "{{S2_TITLE}}");
lede(s2, "{{S2_LEDE}}");
const tileW = 2.94, gapX = 0.28;
for (let i = 0; i < 4; i++) {
  const x = M + i * (tileW + gapX);
  s2.addShape(pres.ShapeType.roundRect, {
    x, y: 1.85, w: tileW, h: 1.75, rectRadius: 0.08,
    fill: { color: TINT }, line: { color: RULE, width: 1 },
  });
  s2.addText(`{{KPI${i + 1}_LABEL}}`, {
    x: x + 0.22, y: 2.02, w: tileW - 0.44, h: 0.5, fontFace: "Calibri",
    fontSize: 11.5, color: MUTED, isTextBox: true, margin: 0,
  });
  s2.addText(`{{KPI${i + 1}_VALUE}}`, {
    x: x + 0.22, y: 2.5, w: tileW - 0.44, h: 0.6, fontFace: "Cambria",
    fontSize: 26, bold: true, color: NAVY, isTextBox: true, margin: 0,
  });
  s2.addText(`{{KPI${i + 1}_NOTE}}`, {
    x: x + 0.22, y: 3.08, w: tileW - 0.44, h: 0.45, fontFace: "Calibri",
    fontSize: 11, color: MUTED, isTextBox: true, margin: 0,
  });
}
s2.addText("THE FINDING", {
  x: M, y: 3.95, w: 5, h: 0.3, fontFace: "Calibri", fontSize: 11.5, bold: true,
  color: MUTED, isTextBox: true, margin: 0,
});
s2.addText("{{S2_FINDING}}", {
  x: M, y: 4.3, w: W - 2 * M, h: 2.3, fontFace: "Calibri", fontSize: 15,
  color: INK, valign: "top", isTextBox: true, margin: 0,
});
footer(s2, 2);

// -------------------------------------------------------------- 3-6. charts
chartSlide("history", 3);
chartSlide("ranking", 4);
chartSlide("composition", 5);
chartSlide("bands", 6);

// ------------------------------------------------------------ 7. implications
const s7 = pres.addSlide();
title(s7, "{{S7_TITLE}}");
lede(s7, "{{S7_LEDE}}");
for (let i = 0; i < 3; i++) {
  const x = M + i * (3.9 + 0.3);
  s7.addShape(pres.ShapeType.roundRect, {
    x, y: 1.85, w: 3.9, h: 4.5, rectRadius: 0.08,
    fill: { color: TINT }, line: { color: RULE, width: 1 },
  });
  s7.addText(`{{COL${i + 1}_NUM}}`, {
    x: x + 0.28, y: 2.05, w: 3.34, h: 0.5, fontFace: "Cambria", fontSize: 22,
    bold: true, color: ACCENT, isTextBox: true, margin: 0,
  });
  s7.addText(`{{COL${i + 1}_HEAD}}`, {
    x: x + 0.28, y: 2.55, w: 3.34, h: 0.75, fontFace: "Calibri", fontSize: 15,
    bold: true, color: NAVY, isTextBox: true, margin: 0,
  });
  s7.addText(`{{COL${i + 1}_BODY}}`, {
    x: x + 0.28, y: 3.35, w: 3.34, h: 2.75, fontFace: "Calibri", fontSize: 13,
    color: INK, valign: "top", isTextBox: true, margin: 0,
  });
}
footer(s7, 7);

// ----------------------------------------------------------------- 8. method
const s8 = pres.addSlide();
title(s8, "{{S8_TITLE}}");
lede(s8, "{{S8_LEDE}}");
for (let i = 0; i < 3; i++) {
  const x = M + i * (3.9 + 0.3);
  s8.addShape(pres.ShapeType.roundRect, {
    x, y: 1.85, w: 3.9, h: 1.45, rectRadius: 0.08,
    fill: { color: TINT }, line: { color: RULE, width: 1 },
  });
  s8.addText(`{{DQ${i + 1}_LABEL}}`, {
    x: x + 0.25, y: 2.0, w: 3.4, h: 0.3, fontFace: "Calibri", fontSize: 11.5,
    color: MUTED, isTextBox: true, margin: 0,
  });
  s8.addText(`{{DQ${i + 1}_VALUE}}`, {
    x: x + 0.25, y: 2.32, w: 3.4, h: 0.55, fontFace: "Cambria", fontSize: 24,
    bold: true, color: ACCENT, isTextBox: true, margin: 0,
  });
  s8.addText(`{{DQ${i + 1}_NOTE}}`, {
    x: x + 0.25, y: 2.86, w: 3.4, h: 0.35, fontFace: "Calibri", fontSize: 11,
    color: MUTED, isTextBox: true, margin: 0,
  });
}
s8.addText("HOW THE NUMBERS WERE CHECKED", {
  x: M, y: 3.6, w: 5.6, h: 0.3, fontFace: "Calibri", fontSize: 11.5, bold: true,
  color: MUTED, isTextBox: true, margin: 0,
});
s8.addText("{{METHOD_LEFT}}", {
  x: M, y: 3.95, w: 5.6, h: 2.5, fontFace: "Calibri", fontSize: 13, color: INK,
  valign: "top", isTextBox: true, margin: 0,
});
s8.addText("WHAT THIS ANALYSIS CANNOT TELL YOU", {
  x: M + 5.9, y: 3.6, w: 5.6, h: 0.3, fontFace: "Calibri", fontSize: 11.5,
  bold: true, color: MUTED, isTextBox: true, margin: 0,
});
s8.addText("{{METHOD_RIGHT}}", {
  x: M + 5.9, y: 3.95, w: 5.6, h: 2.5, fontFace: "Calibri", fontSize: 13,
  color: INK, valign: "top", isTextBox: true, margin: 0,
});
footer(s8, 8);

const out = path.join(__dirname, "report_template.pptx");
pres.writeFile({ fileName: out }).then(() => console.log("Wrote", out));
