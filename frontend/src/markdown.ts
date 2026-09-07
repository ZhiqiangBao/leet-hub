import { marked } from "marked";
import markedKatex from "marked-katex-extension";

marked.use(
  markedKatex({
    throwOnError: false,
    nonStandard: true,
  }),
);

const FENCE = /```[^\n]*\n([\s\S]*?)```/g;
const EX_NUM = /^### 示例 (\d+)\s*$/;
const EX_HEAD = /^(?:#{2,3}\s*|\*\*)示例\s+(\d+)\s*[：:．.]?\s*\*{0,2}\s*$/;
const LABEL = /^(?:\*\*)?(输入|输出|解释)[:：](?:\*\*)?\s*(.*?)\s*$/;
const LABEL_START = /^(?:\*\*)?(输入|输出|解释)[:：]/;

function unwrapExampleFences(text: string): string {
  return text.replace(FENCE, (full, body: string) => {
    if (/输入[:：]/.test(body) && /输出[:：]/.test(body)) {
      return `${body.replace(/^\n+/, "").replace(/\n+$/, "")}\n`;
    }
    return full;
  });
}

const IO_LINE = /^(\*\*)?(输入|输出)[:：](\*\*)?\s*(.*?)\s*$/;
const FENCE_LANG_TOKEN =
  /^(?:json|javascript|js|python|py|text|txt|html|xml|c|cpp|java)$/i;

function compactValue(text: string): string {
  return text.trim().replace(/\s+/g, " ");
}

function innerFromInlineFence(rest: string): string | null {
  if (!rest.startsWith("```")) return null;
  const body = rest.slice(3);
  const close = body.lastIndexOf("```");
  if (close < 0) return null;
  let inner = body.slice(0, close).trim();
  const lang = inner.match(/^([A-Za-z][\w+-]*)(?:\s+([\s\S]+))?$/);
  const rest = (lang?.[2] || "").trim();
  if (rest && lang && FENCE_LANG_TOKEN.test(lang[1])) inner = rest;
  return compactValue(inner);
}

function unwrapValueFences(text: string): string {
  const lines = text.split("\n");
  const out: string[] = [];
  let i = 0;

  const consumeFence = (start: number, openRest: string): [string, number] => {
    const parts: string[] = [];
    const extra = openRest.trim();
    if (extra && !FENCE_LANG_TOKEN.test(extra)) parts.push(extra);
    let j = start;
    while (j < lines.length) {
      if (lines[j].trim().startsWith("```")) {
        return [compactValue(parts.join("\n")), j + 1];
      }
      parts.push(lines[j]);
      j += 1;
    }
    return [compactValue(parts.join("\n")), j];
  };

  while (i < lines.length) {
    const m = lines[i].trim().match(IO_LINE);
    if (!m) {
      out.push(lines[i]);
      i += 1;
      continue;
    }
    const kind = m[2];
    const rest = (m[4] || "").trim();
    const inline = innerFromInlineFence(rest);
    if (inline !== null) {
      out.push(inline ? `${kind}：${inline}` : `${kind}：`);
      i += 1;
      continue;
    }
    if (rest.startsWith("```")) {
      const [inner, nxt] = consumeFence(i + 1, rest.slice(3));
      out.push(inner ? `${kind}：${inner}` : `${kind}：`);
      i = nxt;
      continue;
    }
    if (rest === "") {
      let j = i + 1;
      while (j < lines.length && lines[j].trim() === "") j += 1;
      if (j < lines.length && lines[j].trim().startsWith("```")) {
        const [inner, nxt] = consumeFence(j + 1, lines[j].trim().slice(3));
        out.push(inner ? `${kind}：${inner}` : `${kind}：`);
        i = nxt;
        continue;
      }
    }
    out.push(lines[i]);
    i += 1;
  }
  return out.join("\n");
}

function fullwidthLabelColons(text: string): string {
  return text.replace(/^(\*\*)?(输入|输出|解释)[:：]/gm, "$1$2：");
}

function splitJoinedLabels(text: string): string {
  return text
    .replace(/(输入：[^\n]*?)\s+(输出：)/g, "$1\n$2")
    .replace(/(输出：[^\n]*?)\s+(解释：)/g, "$1\n$2");
}

function aliasHeadings(text: string): string {
  return text
    .replace(/^##\s*(题目描述|题意)\s*\n+/gm, "")
    .replace(
      /^##\s*(?:输入格式|输出格式|参数与返回值|参数|返回值)\s*\n(?:(?!^## ).*\n)*/gm,
      "",
    )
    .replace(/^#{2,3}\s*约束(?:条件)?\s*$/gm, "## 约束");
}

function convertLineHeading(line: string): string {
  const stripped = line.trim();
  if (stripped === "---" || stripped === "***" || stripped === "___") return "";
  const m = stripped.match(EX_HEAD);
  if (m) return `### 示例 ${m[1]}`;
  return line;
}

function insertExampleNumbers(lines: string[]): string[] {
  const out: string[] = [];
  let n = 0;
  for (const line of lines) {
    const num = line.trim().match(EX_NUM);
    if (num) {
      n = Number(num[1]);
      out.push(`### 示例 ${n}`);
      continue;
    }
    const lab = line.trim().match(LABEL_START);
    if (lab?.[1] === "输入") {
      let j = out.length - 1;
      while (j >= 0 && out[j].trim() === "") j -= 1;
      if (j < 0 || !EX_NUM.test(out[j].trim())) {
        n += 1;
        if (out.length && out[out.length - 1].trim() !== "") out.push("");
        out.push(`### 示例 ${n}`, "");
      }
      out.push(line);
      continue;
    }
    out.push(line);
  }
  return out;
}

function insertExampleSection(lines: string[]): string[] {
  if (lines.some((ln) => /^##\s*示例\s*$/.test(ln.trim()))) return lines;
  const i = lines.findIndex((ln) => EX_NUM.test(ln.trim()));
  if (i < 0) return lines;
  return [...lines.slice(0, i), "## 示例", "", ...lines.slice(i)];
}

function formatLabelLine(line: string): string {
  const m = line.trim().match(LABEL);
  if (!m) return line;
  let rest = m[2].trim();
  if (m[1] === "输入" || m[1] === "输出") {
    rest = rest.replace(/`([^`]+)`/g, "$1");
  } else {
    const wrapped = rest.match(/^`([^`]+)`$/);
    if (wrapped) rest = wrapped[1];
  }
  const body = rest ? `${m[1]}：${rest}` : `${m[1]}：`;
  return `${body}  `;
}

function padHeadingSpacing(text: string): string {
  return text
    .replace(/(?<!\n)\n(#{2,3} )/g, "\n\n$1")
    .replace(/^(#{2,3} .+)\n(?!\n)/gm, "$1\n\n");
}

function squeezeLabelBlanks(text: string): string {
  return text.replace(
    /(^(?:输入|输出|解释)：[^\n]*\n)\n+(?=^(?:输入|输出|解释)：)/gm,
    "$1",
  );
}

/** Match `normalize_examples.normalize_layout`, then drop the R2 title (page already has it). */
export function normalizeStatement(md: string): string {
  let body = (md || "").replace(/^\uFEFF/, "").replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  body = body.replace(/^#\s+[^\n]+\n+/, "");
  body = unwrapExampleFences(body);
  body = unwrapValueFences(body);
  body = fullwidthLabelColons(body);
  body = splitJoinedLabels(body);
  body = aliasHeadings(body);
  let lines = body.split("\n").map(convertLineHeading);
  lines = insertExampleNumbers(lines);
  lines = insertExampleSection(lines);
  lines = lines.map(formatLabelLine);
  body = squeezeLabelBlanks(lines.join("\n"));
  body = padHeadingSpacing(body).replace(/\n{3,}/g, "\n\n");
  return wrapExampleQuotes(body.trim());
}

function isSectionBreak(line: string): boolean {
  const t = line.trim();
  return EX_NUM.test(t) || /^##\s+\S/.test(t);
}

function quoteExampleLine(line: string): string {
  const m = line.trim().match(LABEL);
  if (!m) return line.trim() === "" ? ">" : `> ${line}`;
  let rest = m[2].trim();
  if (m[1] === "输入" || m[1] === "输出") {
    rest = rest.replace(/`([^`]+)`/g, "$1");
  }
  const body = rest ? `**${m[1]}：** ${rest}` : `**${m[1]}：**`;
  return `> ${body}`;
}

function wrapExampleQuotes(text: string): string {
  const lines = text.split("\n");
  const out: string[] = [];
  let i = 0;
  while (i < lines.length) {
    const label = lines[i].trim().match(LABEL);
    if (label?.[1] !== "输入") {
      out.push(lines[i]);
      i += 1;
      continue;
    }
    const buf: string[] = [];
    while (i < lines.length) {
      const t = lines[i].trim();
      if (buf.length && isSectionBreak(lines[i])) break;
      if (buf.length && LABEL.test(t) && LABEL.exec(t)?.[1] === "输入") break;
      buf.push(lines[i]);
      i += 1;
    }
    while (buf.length && buf[buf.length - 1].trim() === "") buf.pop();
    const quoted: string[] = [];
    for (let k = 0; k < buf.length; k++) {
      const currLabel = buf[k].trim().match(LABEL);
      if (k > 0 && currLabel) quoted.push(">");
      else if (k > 0 && LABEL.test(buf[k - 1].trim()) && buf[k].trim() !== "" && !currLabel) {
        quoted.push(">");
      }
      quoted.push(quoteExampleLine(buf[k]));
    }
    out.push(quoted.join("\n"));
  }
  return out.join("\n");
}

export function renderStatement(md: string): string {
  return marked.parse(normalizeStatement(md), { async: false, gfm: true }) as string;
}
