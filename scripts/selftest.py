from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("LOCAL_LEET_ROOT", str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.judge.engine import judge_source  # noqa: E402
from app.judge.languages import language_status  # noqa: E402
from app.services.problems import bank  # noqa: E402

AC_TWO_SUM = '''
class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        seen = {}
        for i, n in enumerate(nums):
            need = target - n
            if need in seen:
                return [seen[need], i]
            seen[n] = i
        return []
'''

WA_TWO_SUM = '''
class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        return [0, 0]
'''

CE_TWO_SUM = "class Solution:\n    def twoSum(self\n"

AC_CPP = r'''
class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        unordered_map<int,int> seen;
        for (int i = 0; i < (int)nums.size(); ++i) {
            int need = target - nums[i];
            if (seen.count(need)) return {seen[need], i};
            seen[nums[i]] = i;
        }
        return {};
    }
};
'''

AC_C = r'''
int* twoSum(int* nums, int numsSize, int target, int* returnSize) {
    for (int i = 0; i < numsSize; i++) {
        for (int j = i + 1; j < numsSize; j++) {
            if (nums[i] + nums[j] == target) {
                int* out = (int*)malloc(sizeof(int) * 2);
                out[0] = i;
                out[1] = j;
                *returnSize = 2;
                return out;
            }
        }
    }
    *returnSize = 0;
    return NULL;
}
'''

WA_C = r'''
int* twoSum(int* nums, int numsSize, int target, int* returnSize) {
    int* out = (int*)malloc(sizeof(int) * 2);
    out[0] = 0;
    out[1] = 0;
    *returnSize = 2;
    return out;
}
'''


def expect(name: str, result: dict, verdict: str) -> None:
    got = result.get("verdict")
    if got != verdict:
        raise SystemExit(f"[FAIL] {name}: expected {verdict}, got {got} details={result}")
    print(f"[OK] {name}: {verdict}")


def main() -> None:
    print("problems:", [p.slug for p in bank.list()])
    print("languages:", language_status())
    if not bank.list():
        raise SystemExit("no problems loaded")

    py_ok = any(x["id"] == "python3" and x["available"] for x in language_status())
    if not py_ok:
        raise SystemExit("python3 adapter not available on this machine (needed for selftest)")

    expect("python AC", judge_source("two-sum", "python3", AC_TWO_SUM), "AC")
    expect("python WA", judge_source("two-sum", "python3", WA_TWO_SUM), "WA")
    expect("python CE", judge_source("two-sum", "python3", CE_TWO_SUM), "CE")
    public_ac = judge_source("two-sum", "python3", AC_TWO_SUM, True)
    expect("python public-only AC", public_ac, "AC")
    if (public_ac.get("details") or {}).get("total") != 3:
        raise SystemExit(f"[FAIL] public-only should run 3 examples, got {public_ac}")
    na = judge_source("two-sum", "javascript", "class Solution {}")
    expect("javascript stub NA", na, "NA")

    cpp = next(x for x in language_status() if x["id"] == "cpp17")
    if cpp["available"]:
        expect("cpp AC", judge_source("two-sum", "cpp17", AC_CPP), "AC")
    else:
        print("[SKIP] cpp17 not available here; Ubuntu host with g++ will run C++ judging")

    clang = next(x for x in language_status() if x["id"] == "c")
    if clang["available"]:
        expect("c AC", judge_source("two-sum", "c", AC_C), "AC")
        expect("c WA", judge_source("two-sum", "c", WA_C), "WA")
        expect("c CE", judge_source("two-sum", "c", "int* twoSum("), "CE")
    else:
        print("[SKIP] c not available here; Ubuntu host with gcc will run C judging")

    print("selftest passed")


if __name__ == "__main__":
    main()
