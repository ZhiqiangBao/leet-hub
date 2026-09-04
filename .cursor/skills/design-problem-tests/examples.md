# 示例：两数之和的提交测例

约束（摘自题面）：`2 <= n <= 10000`，`±1e9`，恰好一对、不可复用同一元素，下标顺序任意。

公开 3 条对应题面示例即可（`hidden: false`）。下面 **22 条均为 `hidden: true`**，每条一个意图。`expected` 须用参考解生成后写入；此处给出的下标是示意。

```json
{"args":[[1,2],3],"expected":[0,1],"hidden":true}
{"args":[[-1,1],0],"expected":[0,1],"hidden":true}
{"args":[[0,0],0],"expected":[0,1],"hidden":true}
{"args":[[-5,-5],-10],"expected":[0,1],"hidden":true}
{"args":[[5,5],10],"expected":[0,1],"hidden":true}
{"args":[[-1000000000,1000000000],0],"expected":[0,1],"hidden":true}
{"args":[[-1000000000,-1],-1000000001],"expected":[0,1],"hidden":true}
{"args":[[1000000000,1],1000000001],"expected":[0,1],"hidden":true}
{"args":[[9,1,2,3],10],"expected":[0,1],"hidden":true}
{"args":[[1,2,3,9],10],"expected":[2,3],"hidden":true}
{"args":[[1,9,2,8,3,7],10],"expected":[0,5],"hidden":true}
{"args":[[4,4,3],8],"expected":[0,1],"hidden":true}
{"args":[[3,2,3],6],"expected":[0,2],"hidden":true}
{"args":[[1,5,5,2],10],"expected":[1,2],"hidden":true}
{"args":[[-3,4,3,90],0],"expected":[0,2],"hidden":true}
{"args":[[-10,-1,-18,-19],-19],"expected":[1,2],"hidden":true}
{"args":[[0,4,3,0],0],"expected":[0,3],"hidden":true}
{"args":[[2,1,3],4],"expected":[0,2],"hidden":true}
{"args":[[8,7,11,2,15],9],"expected":[1,3],"hidden":true}
{"args":[[1,3,4,2],6],"expected":[1,2],"hidden":true}
```

再加 2 条规模（构造时保证唯一解，例如前 `n-2` 个是互不相同且无法配对的数，最后两个才配对）：

```json
{"args":[<n=10000，解在下标 0 与 1>],"expected":[0,1],"hidden":true}
{"args":[<n=10000，解在下标 9998 与 9999>],"expected":[9998,9999],"hidden":true}
```

大数组不要手写在聊天里；用脚本生成后写入 `tests.jsonl`。公开示例 `[2,7,11,15]` 等不要再出现在隐藏行。
