# SenseType TODO

## Overlay 前端优化

- [ ] **音量柱 scale 不够**：正常说话只显示 10%-20% 高度，需要加大映射系数或换更激进的曲线
- [ ] **DPI 修复后框太小、位置偏**：`SetProcessDpiAwareness` 之后 tkinter 用物理像素了，WIDTH/HEIGHT/BOTTOM_MARGIN 需要根据实际 DPI 缩放调整
- [ ] **柱形图改为时间线滚动**：当前 28 根 bar 用 sin 生成，几乎同步跳动。应改为左边=历史音量，右边=最新音量，整体向左滚动（用 deque 存历史值）
- [ ] **考虑用 pywebview 重写前端**：tkinter 视觉上限有限，pywebview 可用 HTML+CSS 实现真毛玻璃（backdrop-filter: blur）、阴影、动画，效果对标 Spokenly。优先级最低，等功能稳定后再做
