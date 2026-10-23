# -*- coding: utf-8 -*-
"""程序化生成示意图 make_diagrams.py —— 为实验报告/技术文档生成时序图与流程图。

为什么需要：实验报告与设计文档常要求"示意图"（如 TCP 三次握手时序图、实验流程图），
手工用 Pillow 画一次就丢掉了。本工具把常见图型配置化，重复可用。

支持图型：
- sequence：时序图（参与者竖线 + 消息箭头 + 序号 + 可选注释）
- flow：流程图（开始/处理/判断/结束节点 + 连线，垂直自动布局）

用法：
  # 用内置预设（如 TCP 三次握手）
  python make_diagrams.py --preset tcp-handshake --out tcp.png

  # 用 JSON 配置
  python make_diagrams.py --config my-diagram.json --out chart.png

  # 列出内置预设
  python make_diagrams.py --list

依赖：Pillow（pip install pillow）。中文字体自动查找系统字体（微软雅黑/黑体/宋体）。
输出：高分辨率 PNG（2x），适合直接插入 Word（建议宽度 ≤ 15cm）。
"""
import os, sys, json, argparse
from PIL import Image, ImageDraw, ImageFont

# ── 字体查找 ────────────────────────────────────────────────────────────────
FONT_CANDIDATES = [
    r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\msyhbd.ttc',
    r'C:\Windows\Fonts\simhei.ttf', r'C:\Windows\Fonts\simsun.ttc',
    '/System/Library/Fonts/PingFang.ttc',
    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
]

def find_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    print('⚠️ 未找到中文字体，使用默认字体（中文可能显示为方块）')
    return ImageFont.load_default()

# ── 内置预设 ────────────────────────────────────────────────────────────────
PRESETS = {
    'tcp-handshake': {
        'type': 'sequence',
        'title': 'TCP 三次握手时序图',
        'actors': ['客户端', '服务端'],
        'messages': [
            {'from': 0, 'to': 1, 'label': 'SYN (seq=x)', 'note': '客户端请求建立连接，进入 SYN_SENT'},
            {'from': 1, 'to': 0, 'label': 'SYN+ACK (seq=y, ack=x+1)', 'note': '服务端同意连接，进入 SYN_RCVD'},
            {'from': 0, 'to': 1, 'label': 'ACK (seq=x+1, ack=y+1)', 'note': '三次握手完成，双方进入 ESTABLISHED'},
        ],
    },
    'tcp-close': {
        'type': 'sequence',
        'title': 'TCP 四次挥手时序图',
        'actors': ['客户端', '服务端'],
        'messages': [
            {'from': 0, 'to': 1, 'label': 'FIN (seq=u)', 'note': '主动关闭方发送 FIN，进入 FIN_WAIT_1'},
            {'from': 1, 'to': 0, 'label': 'ACK (ack=u+1)', 'note': '被动关闭方确认，进入 CLOSE_WAIT'},
            {'from': 1, 'to': 0, 'label': 'FIN (seq=w)', 'note': '被动关闭方也关闭，发送 FIN'},
            {'from': 0, 'to': 1, 'label': 'ACK (ack=w+1)', 'note': '主动关闭方确认，进入 TIME_WAIT'},
        ],
    },
    'experiment-flow': {
        'type': 'flow',
        'title': '抓包实验流程图',
        'nodes': [
            {'id': 's', 'text': '开始实验', 'type': 'start'},
            {'id': 'a', 'text': '准备实验环境\\n（Wireshark + 客户端/服务端）', 'type': 'process'},
            {'id': 'b', 'text': '选择网卡并启动抓包', 'type': 'process'},
            {'id': 'c', 'text': '触发 TCP 连接', 'type': 'process'},
            {'id': 'd', 'text': '停止抓包并按 SYN 过滤', 'type': 'process'},
            {'id': 'e', 'text': '抓到三次握手？', 'type': 'decision'},
            {'id': 'f', 'text': '调整过滤器/重新抓包', 'type': 'process'},
            {'id': 'g', 'text': '分析 seq/ack 与标志位', 'type': 'process'},
            {'id': 'h', 'text': '撰写实验报告', 'type': 'end'},
        ],
        'edges': [
            {'from': 's', 'to': 'a'}, {'from': 'a', 'to': 'b'}, {'from': 'b', 'to': 'c'},
            {'from': 'c', 'to': 'd'}, {'from': 'd', 'to': 'e'},
            {'from': 'e', 'to': 'g', 'label': '是'}, {'from': 'e', 'to': 'f', 'label': '否'},
            {'from': 'f', 'to': 'b'}, {'from': 'g', 'to': 'h'},
        ],
    },
}

# ── 绘制：时序图 ────────────────────────────────────────────────────────────
def draw_sequence(cfg, out_path):
    scale = 2
    actors = cfg['actors']
    msgs = cfg['messages']
    title = cfg.get('title', '')
    W = cfg.get('width', 1000) * scale
    pad = 40 * scale
    top_h = 90 * scale
    # 参与者横坐标
    n = len(actors)
    xs = [pad + (W - 2 * pad) * (i + 0.5) / n for i in range(n)]
    msg_h = 95 * scale
    H = top_h + msg_h * len(msgs) + 80 * scale
    img = Image.new('RGB', (int(W), int(H)), 'white')
    d = ImageDraw.Draw(img)
    f_title = find_font(26 * scale)
    f_actor = find_font(20 * scale)
    f_msg = find_font(16 * scale)
    f_note = find_font(14 * scale)
    f_num = find_font(14 * scale)

    if title:
        d.text((W / 2, 30 * scale), title, font=f_title, fill='black', anchor='mm')

    # 参与者框与竖线
    box_w = 150 * scale
    for i, (name, x) in enumerate(zip(actors, xs)):
        y0 = top_h - 40 * scale
        d.rectangle([x - box_w / 2, y0, x + box_w / 2, y0 + 46 * scale], outline='black', width=2 * scale, fill='#eef4ff')
        d.text((x, y0 + 23 * scale), name, font=f_actor, fill='black', anchor='mm')
        d.line([x, y0 + 46 * scale, x, H - 40 * scale], fill='#888888', width=2 * scale)

    # 消息箭头
    arrow_y = top_h + 40 * scale
    for idx, m in enumerate(msgs, 1):
        y = arrow_y + (idx - 1) * msg_h
        x1, x2 = xs[m['from']], xs[m['to']]
        direction = 1 if x2 > x1 else -1
        # 序号圆
        d.ellipse([pad / 2, y - 12 * scale, pad / 2 + 24 * scale, y + 12 * scale], outline='black', width=2 * scale, fill='white')
        d.text((pad / 2 + 12 * scale, y), str(idx), font=f_num, fill='black', anchor='mm')
        # 箭头
        d.line([x1, y, x2, y], fill='black', width=2 * scale)
        d.polygon([(x2, y), (x2 - 12 * scale * direction, y - 6 * scale), (x2 - 12 * scale * direction, y + 6 * scale)], fill='black')
        # 标签
        d.text(((x1 + x2) / 2, y - 16 * scale), m['label'], font=f_msg, fill='black', anchor='mm')
        # 注释
        if m.get('note'):
            note_x = (x1 + x2) / 2 + 40 * scale
            d.text((note_x, y + 18 * scale), m['note'], font=f_note, fill='#555555', anchor='lm')
    img.save(out_path)
    print(f'OK: {out_path}（{W // scale}x{H // scale} 逻辑像素，2x 输出）')

# ── 绘制：流程图 ────────────────────────────────────────────────────────────
def draw_flow(cfg, out_path):
    scale = 2
    nodes = {nd['id']: nd for nd in cfg['nodes']}
    order = [nd['id'] for nd in cfg['nodes']]
    title = cfg.get('title', '')
    # 垂直布局：每个节点一行
    W = cfg.get('width', 760) * scale
    row_h = 110 * scale
    pad = 50 * scale
    H = 90 * scale + row_h * len(order) + 60 * scale
    img = Image.new('RGB', (int(W), int(H)), 'white')
    d = ImageDraw.Draw(img)
    f_title = find_font(26 * scale)
    f_node = find_font(16 * scale)
    f_edge = find_font(14 * scale)
    if title:
        d.text((W / 2, 30 * scale), title, font=f_title, fill='black', anchor='mm')
    # 节点坐标
    pos = {}
    for i, nid in enumerate(order):
        pos[nid] = (W / 2, 90 * scale + i * row_h)
    # 先画连线（在节点下）
    loop_track = 0  # 回环线轨道序号：每条回环用独立竖向轨道，避免重叠
    for e in cfg.get('edges', []):
        x1, y1 = pos[e['from']]
        x2, y2 = pos[e['to']]
        if abs(y2 - y1) <= row_h + 1:  # 相邻/向前：垂直直线
            d.line([x1, y1 + 32 * scale, x2, y2 - 32 * scale], fill='black', width=2 * scale)
            d.polygon([(x2, y2 - 32 * scale), (x2 - 7 * scale, y2 - 46 * scale), (x2 + 7 * scale, y2 - 46 * scale)], fill='black')
            if e.get('label'):
                # 标签放箭头右侧，避免压线
                d.text((x1 + 26 * scale, (y1 + y2) / 2), e['label'], font=f_edge, fill='#333333', anchor='lm')
        else:  # 回环（如 否 → 重新抓包 → 回到前面步骤）：走右侧独立轨道
            rx = W - pad - 60 * scale - loop_track * 46 * scale
            loop_track += 1
            d.line([x1 + 160 * scale, y1, rx, y1], fill='black', width=2 * scale)
            d.line([rx, y1, rx, y2], fill='black', width=2 * scale)
            d.line([rx, y2, x2 + 160 * scale, y2], fill='black', width=2 * scale)
            d.polygon([(x2 + 160 * scale, y2), (x2 + 174 * scale, y2 - 7 * scale), (x2 + 174 * scale, y2 + 7 * scale)], fill='black')
            if e.get('label'):
                # 标签贴在源节点高度、轨道内侧，语义更清楚（如「是」贴着判断节点）
                d.text((rx - 12 * scale, y1), e['label'], font=f_edge, fill='#333333', anchor='rm')
    # 节点
    for nid in order:
        x, y = pos[nid]
        nd = nodes[nid]
        typ = nd.get('type', 'process')
        text = nd.get('text', '')
        lines = text.split('\\n')
        box_w = 320 * scale if typ != 'decision' else 300 * scale
        box_h = (30 + 22 * len(lines)) * scale
        if typ in ('start', 'end'):
            d.rounded_rectangle([x - box_w / 2, y - box_h / 2, x + box_w / 2, y + box_h / 2], radius=box_h / 2, outline='black', fill='#eaf7ea' if typ == 'start' else '#fdeaea', width=2 * scale)
        elif typ == 'decision':
            d.polygon([(x, y - box_h / 2 - 6 * scale), (x + box_w / 2, y), (x, y + box_h / 2 + 6 * scale), (x - box_w / 2, y)], outline='black', fill='#fff6e0', width=2 * scale)
        else:
            d.rectangle([x - box_w / 2, y - box_h / 2, x + box_w / 2, y + box_h / 2], outline='black', fill='#f4f6fa', width=2 * scale)
        for li, ln in enumerate(lines):
            d.text((x, y - (len(lines) - 1) * 11 * scale + li * 22 * scale), ln, font=f_node, fill='black', anchor='mm')
    img.save(out_path)
    print(f'OK: {out_path}（{W // scale}x{H // scale} 逻辑像素，2x 输出）')

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='程序化生成示意图（时序图/流程图）')
    ap.add_argument('--preset', help='内置预设：tcp-handshake / tcp-close / experiment-flow')
    ap.add_argument('--config', help='JSON 配置路径')
    ap.add_argument('--out', required=False, default='diagram.png', help='输出 PNG 路径')
    ap.add_argument('--list', action='store_true', help='列出内置预设')
    args = ap.parse_args()

    if args.list:
        for name, cfg in PRESETS.items():
            print(f'{name}: {cfg.get("title")}（{cfg["type"]}）')
        sys.exit(0)

    if args.preset:
        if args.preset not in PRESETS:
            print(f'未知预设：{args.preset}。可用：{", ".join(PRESETS)}')
            sys.exit(1)
        cfg = PRESETS[args.preset]
    elif args.config:
        cfg = json.load(open(args.config, encoding='utf-8'))
    else:
        print('请指定 --preset 或 --config（--list 查看内置预设）')
        sys.exit(1)

    t = cfg.get('type')
    if t == 'sequence':
        draw_sequence(cfg, args.out)
    elif t == 'flow':
        draw_flow(cfg, args.out)
    else:
        print(f'未知图型：{t}（支持 sequence / flow）')
        sys.exit(1)
