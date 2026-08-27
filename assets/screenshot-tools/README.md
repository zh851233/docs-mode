# screenshot-tools — 界面截图自动化

用于《系统使用说明书》第四章「系统功能界面设计」的真实界面截图。

## 文件

| 文件 | 作用 |
|------|------|
| `screenshots.mjs` | 通用 Playwright 截图脚本：配置 URL + 截图清单（等待/点击/填充/ready 条件），自动截图并留 OCR 验证占位 |

## 用法

```powershell
# 1. 编辑 screenshots.mjs 顶部的 CONFIG：baseUrl、shots 清单
# 2. 运行（可选自动起 dev server）：
node screenshots.mjs --server-command "npm run dev" --server-dir "D:\path\to\front"
# 3. 对每张截图执行 OCR 验证（模型在会话中调用 mcp__qwen-mm-plugins-api__ocr）：
#    确认不是 loading/空白/错误画面，把 OCR 文本写入 <name>.ocr.txt
# 4. 只有 OCR 验证通过的截图才能写进文档
```

## shots 清单字段

| 字段 | 说明 |
|------|------|
| `name` | 输出文件名（不含扩展名） |
| `wait` | 打开页面后等待 ms（默认 6000） |
| `ready` | JS 表达式，为 true 才截图（如 `!document.body.innerText.includes('正在装载')`）——**必须用**，防止 loading 图 |
| `click` | CSS 选择器数组，逐个点击（evaluate 方式，绕开 actionability 检查） |
| `fill` | `[selector, text]` 填充输入框 |
| `key` | 键盘按键 |
| `shot` | `'element:<sel>'` 只截某元素 |
| `waitAfterClick` | 每次点击后等待 ms（默认 2000） |

## 实战经验（从踩坑中总结）

1. **ready 条件必须用**：大体积应用（50MB+ 数据资产）加载慢，固定等待常截到「正在装载」画面。
2. **面板默认收起**：右侧报告面板/左侧参数面板常默认收起，截图前先 click 打开（`.insight-trigger`、`.controls-trigger` 之类）。
3. **点击地图触发分析后要等 10s+**：等分数组件出现（用 ready 条件），别固定时间。
4. **evaluate 点击比 Playwright actionability 稳定**：`outside of the viewport` 报错时用 `document.querySelector(sel).click()`。
5. **截图后必须 OCR 验证**：模型不能直接读图时，用 qwen OCR 确认内容；确认过才入文档。
