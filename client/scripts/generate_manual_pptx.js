const fs = require('fs');
const path = require('path');
const PptxGenJS = require('pptxgenjs');

const ROOT = path.resolve(__dirname, '..', '..');
const OUTLINE_PATH = path.join(ROOT, 'client', 'docs', 'CLIENT_USER_MANUAL_SLIDE_OUTLINE.md');
const ASSET_DIR = path.join(ROOT, 'client', 'docs', 'manual-assets');
const OUTPUT_PATH = path.join(ROOT, 'client', 'docs', 'CLIENT_USER_MANUAL.pptx');

const pptx = new PptxGenJS();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'OpenAI Codex';
pptx.company = 'OpenAI';
pptx.subject = '土壌雨量指数監視システム クライアント操作マニュアル';
pptx.title = '土壌雨量指数監視システム 操作マニュアル';
pptx.lang = 'ja-JP';
pptx.theme = {
  headFontFace: 'Meiryo',
  bodyFontFace: 'Meiryo',
  lang: 'ja-JP',
};

const outline = fs.readFileSync(OUTLINE_PATH, 'utf8');

function parseSections(text) {
  const matches = [...text.matchAll(/^##\s+(\d+)\.\s+(.+)$/gm)];
  return matches.map((match, index) => {
    const start = match.index + match[0].length;
    const end = index + 1 < matches.length ? matches[index + 1].index : text.length;
    return {
      number: Number(match[1]),
      title: match[2].trim(),
      body: text.slice(start, end).trim(),
    };
  });
}

function sectionTextLines(body) {
  return body
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .map((line) => {
        if (line.startsWith('- ')) return `• ${line.slice(2)}`;
        if (/^\d+\.\s/.test(line)) return line;
        return line;
    });
}

function addPageFrame(slide, section, accentColor = 'A64E36') {
  slide.background = { color: 'F6F1E8' };
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: 13.333,
    h: 0.34,
    line: { color: accentColor, transparency: 100 },
    fill: { color: accentColor },
  });
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 7.16,
    w: 13.333,
    h: 0.34,
    line: { color: 'D8CCB8', transparency: 100 },
    fill: { color: 'D8CCB8' },
  });
  slide.addText(`${section.number}`, {
    x: 12.45,
    y: 0.47,
    w: 0.42,
    h: 0.3,
    fontFace: 'Meiryo',
    fontSize: 17,
    bold: true,
    color: accentColor,
    align: 'right',
    margin: 0,
  });
  slide.addText(section.title, {
    x: 0.55,
    y: 0.45,
    w: 10.8,
    h: 0.38,
    fontFace: 'Meiryo',
    fontSize: 24,
    bold: true,
    color: '2F2B28',
    margin: 0,
  });
}

function addFooter(slide) {
  slide.addText('土壌雨量指数監視システム クライアント操作マニュアル', {
    x: 0.55,
    y: 7.03,
    w: 5.8,
    h: 0.16,
    fontFace: 'Meiryo',
    fontSize: 9,
    color: '655F5A',
    margin: 0,
  });
}

function addTitleSlide() {
  const slide = pptx.addSlide();
  slide.background = { color: 'EEE4D5' };
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: 13.333,
    h: 7.5,
    line: { color: 'EEE4D5', transparency: 100 },
    fill: { color: 'EEE4D5' },
  });
  slide.addShape(pptx.ShapeType.rect, {
    x: 0.72,
    y: 0.82,
    w: 0.22,
    h: 5.85,
    line: { color: 'A64E36', transparency: 100 },
    fill: { color: 'A64E36' },
  });
  slide.addText('土壌雨量指数監視システム', {
    x: 1.25,
    y: 1.22,
    w: 8.8,
    h: 0.6,
    fontFace: 'Meiryo',
    fontSize: 28,
    bold: true,
    color: '2D2926',
    margin: 0,
  });
  slide.addText('クライアント操作マニュアル', {
    x: 1.25,
    y: 1.92,
    w: 6.6,
    h: 0.58,
    fontFace: 'Meiryo',
    fontSize: 24,
    bold: true,
    color: 'A64E36',
    margin: 0,
  });
  slide.addText('画面の基本操作、表示内容の見方、雨量調整機能の利用方法を説明します。', {
    x: 1.28,
    y: 2.78,
    w: 5.8,
    h: 0.55,
    fontFace: 'Meiryo',
    fontSize: 16,
    color: '4C4844',
    margin: 0,
  });

  const titleImagePath = path.join(ASSET_DIR, '02-loaded-screen.png');
  if (fs.existsSync(titleImagePath)) {
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 7.15,
      y: 1.0,
      w: 5.45,
      h: 4.55,
      rectRadius: 0.08,
      line: { color: 'D2C3AF', pt: 1.2 },
      fill: { color: 'FFFDFC' },
      shadow: { type: 'outer', color: 'B4A28D', angle: 45, blur: 2, distance: 1, opacity: 0.15 },
    });
    slide.addImage({
      path: titleImagePath,
      x: 7.35,
      y: 1.2,
      w: 5.05,
      h: 4.15,
      sizing: { type: 'contain', x: 7.35, y: 1.2, w: 5.05, h: 4.15 },
    });
  }

  slide.addText('対象: エンドユーザー', {
    x: 1.28,
    y: 5.15,
    w: 2.1,
    h: 0.25,
    fontFace: 'Meiryo',
    fontSize: 12,
    bold: true,
    color: '6B635A',
    margin: 0,
  });
  slide.addText('作成物: 操作説明用 PowerPoint', {
    x: 1.28,
    y: 5.48,
    w: 3.4,
    h: 0.25,
    fontFace: 'Meiryo',
    fontSize: 12,
    color: '6B635A',
    margin: 0,
  });
}

const imageMap = new Map([
  [3, '01-initial-screen.png'],
  [7, '02-loaded-screen.png'],
  [10, '02-loaded-screen.png'],
  [12, '03-rainfall-modal-3hour.png'],
  [13, '03-rainfall-modal-3hour.png'],
  [14, '03-rainfall-modal-3hour.png'],
  [16, '04-rainfall-modal-24hour.png'],
  [21, '05-adjusted-result.png'],
]);

addTitleSlide();

for (const section of parseSections(outline)) {
  const slide = pptx.addSlide();
  addPageFrame(slide, section);

  const imageName = imageMap.get(section.number);
  const imagePath = imageName ? path.join(ASSET_DIR, imageName) : null;
  const hasImage = imagePath && fs.existsSync(imagePath);

  const lines = sectionTextLines(section.body);
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 0.48,
    y: 1.0,
    w: hasImage ? 5.2 : 12.25,
    h: hasImage ? 5.82 : 5.95,
    rectRadius: 0.05,
    line: { color: 'D8CCB8', pt: 1 },
    fill: { color: 'FFFCF8' },
  });
  slide.addText(lines.join('\n'), {
    x: 0.72,
    y: 1.22,
    w: hasImage ? 4.72 : 11.75,
    h: hasImage ? 5.3 : 5.45,
    fontFace: 'Meiryo',
    fontSize: hasImage ? 15 : 18,
    color: '2F3437',
    breakLine: false,
    margin: 0,
    valign: 'top',
    fit: 'shrink',
    paraSpaceAfterPt: 11,
    bullet: { indent: 14 },
  });

  if (hasImage) {
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 5.82,
      y: 1.0,
      w: 6.9,
      h: 5.82,
      rectRadius: 0.05,
      line: { color: 'D8CCB8', pt: 1 },
      fill: { color: 'FFFCF8' },
    });
    slide.addImage({
      path: imagePath,
      x: 6.02,
      y: 1.2,
      w: 6.48,
      h: 5.05,
      sizing: { type: 'contain', x: 6.02, y: 1.2, w: 6.48, h: 5.05 },
    });
    slide.addText('画面例', {
      x: 6.05,
      y: 6.35,
      w: 1.0,
      h: 0.18,
      fontFace: 'Meiryo',
      fontSize: 10,
      bold: true,
      color: '7B6F64',
      margin: 0,
    });
  }

  addFooter(slide);
}

pptx.writeFile({ fileName: OUTPUT_PATH }).catch((error) => {
  console.error(error);
  process.exit(1);
});
