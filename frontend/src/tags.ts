export const TAG_LABELS: Record<string, string> = {
  array: "数组",
  hash: "哈希表",
  string: "字符串",
  stack: "栈",
  "two-pointers": "双指针",
  "sliding-window": "滑动窗口",
  "binary-search": "二分",
  "linked-list": "链表",
  tree: "树",
  greedy: "贪心",
  dp: "动态规划",
  math: "数学",
  sorting: "排序",
};

export function tagLabel(id: string): string {
  return TAG_LABELS[id] || id;
}
