# Chill with You 日记导出器

把游戏 **《Chill with You: Lo-Fi Story / 放松时光：与你共享 Lo-Fi 故事》** 日历（Calender）里的日记一键导出成 `.txt`，每天一份，还会额外生成一份全集。

不用进游戏、不用装 mod、不用 BepInEx，直接读存档就能把历史全部日记翻出来。

## 它能做什么

- 自动找到游戏存档位置（Windows，Steam 版）
- 扫描所有月度存档，把写过日记的每一天导出成 `YYYY-MM-DD.txt`
- 额外生成一份 `日记全集.txt`，按日期排好、带星期
- 自动处理游戏存档里的古怪格式：gzip 压缩、裸数字 key、非法转义、中文、换行

## 下载即用（推荐）

到 [Releases](../../releases) 下载，二选一：

- **`DiaryExporter.exe`** —— 单文件，双击就跑（推荐）
- **`DiaryExporter-win64.zip`** —— 文件夹版，解压后运行里面的 `DiaryExporterDir.exe`（单文件在个别系统上被杀软拦时用它）

导出结果会出现在 **exe 同目录** 的 `日记导出` 文件夹里：

```
日记导出/
├── 日记全集.txt          ← 全部日记汇总
└── daily/
    ├── 2025-12-04.txt    ← 每天一份
    ├── 2026-10-16.txt
    └── ...
```

> 建议导出前**先退出游戏**，否则当天刚写的日记可能还没存盘。

如果你的存档不在默认位置，可以在 exe 所在目录打开命令行：

```powershell
.\DiaryExporter.exe --save-dir "D:\游戏\SaveData\Release\v2"
```

按回车即可关闭窗口。

## 用源码运行

需要 Python 3.8+，无第三方依赖（纯标准库）。

```bash
git clone https://github.com/BRroll/lofi-diary-exporter.git
cd lofi-diary-exporter
python export_diaries.py
```

可选参数：

```bash
# 手动指定存档目录（可重复指定多个）
python export_diaries.py --save-dir "C:\Users\你\AppData\LocalLow\nestopi\Chill With You\SaveData\Release\v2"

# 手动指定输出目录
python export_diaries.py --out-dir "D:\我的日记"
```

## 存档在哪

游戏用 Easy Save 3 存盘，默认路径通常是：

```
C:\Users\<你的用户名>\AppData\LocalLow\nestopi\Chill With You\SaveData\Release\v2\<SteamID>\
```

里面带 `_YYYYMM` 后缀的 `.es3` 文件（如 `1597634371_202610.es3`）就是按月存的日记数据。脚本默认会自动探测，找不到时用它提示的路径配合 `--save-dir` 手动指定即可。

## 原理（给好奇的人）

`.es3` 文件头是 `1f 8b`，其实是 **gzip 压缩的 JSON 变体**。解压后结构大致是：

```json
{
  "1597634371": {
    "__type": "Bulbul.CalenderMonthlyData,Assembly-CSharp",
    "value": {
      "Year": 2026,
      "Month": 10,
      "DiaryList": {
        "1": { "DiaryText": "今天……" }
      }
    }
  }
}
```

坑点有两个，脚本都处理了：

1. `DiaryList` 的日期 key 是裸数字没加引号（`{1:{...}}`），不是合法 JSON；
2. 日记正文里游戏自己塞了 `\“` 这类非法转义符。

所以脚本先把 ES3 变体规范化成标准 JSON，再解析并清理文本。

## 自己打包 exe（可选）

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --name DiaryExporter export_diaries.py
```

`--noconsole` 会隐藏控制台，但脚本末尾的"按回车退出"就没意义了，可自行取舍；想要看日志就用不带 `--noconsole` 的版本。

## 许可证

MIT —— 随便用，记得别拿它干坏事。

---

Made with ♥ for 考研党 and all the late-night Lo-Fi listeners.
