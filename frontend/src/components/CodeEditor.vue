<template>
  <div ref="root" class="editor-wrap"></div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as monaco from "monaco-editor";
import editorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";
import jsonWorker from "monaco-editor/esm/vs/language/json/json.worker?worker";
import tsWorker from "monaco-editor/esm/vs/language/typescript/ts.worker?worker";

self.MonacoEnvironment = {
  getWorker(_workerId: string, label: string) {
    if (label === "json") return new jsonWorker();
    if (label === "javascript" || label === "typescript") return new tsWorker();
    return new editorWorker();
  },
};

const props = defineProps<{ modelValue: string; language: string }>();
const emit = defineEmits<{ "update:modelValue": [string] }>();
const root = ref<HTMLDivElement | null>(null);
let editor: monaco.editor.IStandaloneCodeEditor | null = null;

const monacoLang: Record<string, string> = {
  python3: "python",
  c: "c",
  cpp17: "cpp",
  javascript: "javascript",
  go: "go",
  rust: "rust",
  zig: "plaintext",
};

function configurePythonIndent() {
  monaco.languages.setLanguageConfiguration("python", {
    comments: {
      lineComment: "#",
      blockComment: ["'''", "'''"],
    },
    brackets: [
      ["{", "}"],
      ["[", "]"],
      ["(", ")"],
    ],
    autoClosingPairs: [
      { open: "{", close: "}" },
      { open: "[", close: "]" },
      { open: "(", close: ")" },
      { open: '"', close: '"', notIn: ["string"] },
      { open: "'", close: "'", notIn: ["string", "comment"] },
    ],
    surroundingPairs: [
      { open: "{", close: "}" },
      { open: "[", close: "]" },
      { open: "(", close: ")" },
      { open: '"', close: '"' },
      { open: "'", close: "'" },
    ],
    onEnterRules: [
      {
        beforeText:
          /^\s*(?:def|class|for|if|elif|else|while|try|with|finally|except|async|match|case).*?:\s*(?:#.*)?$/,
        action: { indentAction: monaco.languages.IndentAction.Indent },
      },
      {
        beforeText: /^\s*(?:break|continue|raise|return|pass)\b.*$/,
        action: { indentAction: monaco.languages.IndentAction.Outdent },
      },
    ],
    indentationRules: {
      increaseIndentPattern:
        /^\s*(?:class|def|elif|else|except|finally|for|if|try|with|while|async\s+(?:def|for|with)|match|case)\b.*:\s*(?:#.*)?$/,
      decreaseIndentPattern: /^\s*(?:elif|else|except|finally)\b.*/,
    },
    folding: { offSide: true },
  });
}

onMounted(() => {
  if (!root.value) return;
  configurePythonIndent();
  editor = monaco.editor.create(root.value, {
    value: props.modelValue,
    language: monacoLang[props.language] || "plaintext",
    theme: "vs-dark",
    automaticLayout: true,
    minimap: { enabled: false },
    fontSize: 14,
    scrollBeyondLastLine: false,
    tabSize: 4,
    insertSpaces: true,
    detectIndentation: false,
    autoIndent: "full",
  });
  editor.onDidChangeModelContent(() => {
    emit("update:modelValue", editor?.getValue() || "");
  });
});

watch(
  () => props.modelValue,
  (value) => {
    if (editor && value !== editor.getValue()) editor.setValue(value);
  },
);

watch(
  () => props.language,
  (language) => {
    if (!editor) return;
    const model = editor.getModel();
    if (model) monaco.editor.setModelLanguage(model, monacoLang[language] || "plaintext");
  },
);

onBeforeUnmount(() => {
  editor?.dispose();
});
</script>
