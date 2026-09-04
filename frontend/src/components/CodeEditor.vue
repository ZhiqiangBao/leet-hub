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
  cpp17: "cpp",
  javascript: "javascript",
  go: "go",
  rust: "rust",
  zig: "plaintext",
};

onMounted(() => {
  if (!root.value) return;
  editor = monaco.editor.create(root.value, {
    value: props.modelValue,
    language: monacoLang[props.language] || "plaintext",
    theme: "vs-dark",
    automaticLayout: true,
    minimap: { enabled: false },
    fontSize: 14,
    scrollBeyondLastLine: false,
    tabSize: 4,
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
