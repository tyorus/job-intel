export function parseDescription(raw) {
  if (!raw || !String(raw).trim()) return [];
  const lines = String(raw).replaceAll("\r\n", "\n").split("\n");
  const blocks = [];
  let paragraph = [];
  let list = [];

  function flushParagraph() {
    const text = paragraph.join(" ").trim();
    if (text) blocks.push({ type: "p", text });
    paragraph = [];
  }

  function flushList() {
    if (list.length) blocks.push({ type: "ul", items: [...list] });
    list = [];
  }

  for (const line of lines) {
    const text = line.trim();
    if (!text) {
      flushList();
      flushParagraph();
      continue;
    }
    if (text.startsWith("## ")) {
      flushList();
      flushParagraph();
      blocks.push({ type: "h2", text: text.slice(3).trim() });
      continue;
    }
    if (text.startsWith("### ")) {
      flushList();
      flushParagraph();
      blocks.push({ type: "h3", text: text.slice(4).trim() });
      continue;
    }
    const bullet = text.match(/^(?:[-*•]|\d+[.)])\s+(.*)$/);
    if (bullet) {
      flushParagraph();
      list.push(bullet[1].trim());
      continue;
    }
    flushList();
    paragraph.push(text);
  }
  flushList();
  flushParagraph();
  return blocks;
}
