#!/usr/bin/env python3
"""
Crane's GitHub Profile README 生成器
====================================
读取 config.yml,生成银河星系主题的 SVG 资产(旋转星系头图 + 信息小卡片)。

用法:
    python3 generator.py          # 生成全部 SVG 到 assets/generated/
    python3 generator.py --demo   # 使用内置演示配置(不改 config.yml)

原理(参考 galaxy-profile 的思路,自主实现):
    - 星系旋臂 = 对数螺线 r = a * e^(kθ),用分段 Q 曲线逼近
    - 动画:CSS keyframes(星星闪烁/流星)+ SMIL animateTransform(轨道环旋转)
            + SMIL animateMotion(粒子沿旋臂流动)
    - GitHub 渲染 SVG 时允许 CSS 动画与 SMIL,禁止 JS,故只用这两种
"""

import json
import math
import random
import sys
import os

try:
    import yaml
except ImportError:
    print("缺少依赖: pip install pyyaml")
    sys.exit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "assets", "generated")

# ---------------- 默认配置(与 config.yml 结构一致) ----------------

DEFAULT_CONFIG = {
    "username": "CraneBW",
    "profile": {
        "name": "Crane",
        "tagline": "AI Security Researcher · Photography Lover",
        "tagline_cn": "AI 安全研究者 · 摄影爱好者",
        "initial": "C",
        "philosophy": "Hacking the cosmos, one commit at a time.",
    },
    "galaxy_arms": [
        {
            "name": "AI Security",
            "color": "cyan",
            "items": ["Python", "PyTorch", "TensorFlow", "LLM"],
        },
        {
            "name": "Web Dev",
            "color": "violet",
            "items": ["Django", "Vue", "JavaScript", "SQL"],
        },
        {
            "name": "Dev Tools",
            "color": "amber",
            "items": ["Git", "Docker", "Linux", "GitHub Actions"],
        },
    ],
    "cards": [
        {
            "icon": "🎓",
            "title": "Education",
            "title_cn": "教育",
            "lines": [
                "B.Sc. CS @ Ningbo Univ.",
                "本科 · 宁波大学计算机系",
                "→ M.Sc. Cybersec @ NUAA",
                "研0 · 南京航空航天大学网络安全",
            ],
        },
        {
            "icon": "🔬",
            "title": "Research",
            "title_cn": "研究",
            "lines": [
                "AI Security",
                "AI 安全方向",
                "Adversarial ML · LLM Security",
                "对抗机器学习 · 大模型安全",
            ],
        },
        {
            "icon": "📸",
            "title": "Photography",
            "title_cn": "摄影",
            "lines": [
                "Astrophotography & Cityscapes",
                "星野银河 · 城市风光",
                "captured in /Pictures & below",
                "作品见下方摄影展区",
            ],
        },
    ],
    "theme": {
        "void": "#070b16",          # 最深的太空底色
        "nebula": "#0e1626",        # 卡片底色
        "star_dust": "#1a2332",     # 边框/分隔
        "cyan": "#22d3ee",          # 银河蓝(臂 1)
        "violet": "#a78bfa",        # 星云紫(臂 2)
        "amber": "#fbbf24",         # 流星金(臂 3)
        "text_bright": "#e2e8f0",
        "text_dim": "#94a3b8",
        "text_faint": "#64748b",
    },
    "random_seed": 42,
}

# ---------------- 工具函数 ----------------

def spiral_point(cx, cy, a, k, theta):
    """对数螺线 r = a * e^(kθ) 上一点,返回 (x, y)"""
    r = a * math.exp(k * theta)
    return (cx + r * math.cos(theta), cy + r * math.sin(theta))


def spiral_path(cx, cy, a, k, t0, t1, n=48, arm_offset=0.0):
    """生成对数螺线的分段 Q 曲线路径字符串。
    半径只按局部进度 t 增长(防止臂旋转角使半径膨胀),方向 = t + arm_offset。
    做法:密集采样,每段用 Q(控制点=上一采样点,终点=当前采样点)平滑逼近。"""
    pts = []
    for i in range(n + 1):
        t = t0 + (t1 - t0) * i / n
        r = a * math.exp(k * t)
        theta = t + arm_offset
        x, y = cx + r * math.cos(theta), cy + r * math.sin(theta)
        pts.append((x, y))
    d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"
    for j in range(1, len(pts)):
        px, py = pts[j - 1]
        cx_, cy_ = pts[j]
        d += f" Q {px:.1f} {py:.1f} {cx_:.1f} {cy_:.1f}"
    return d, pts


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------- 星系头图 ----------------

def build_header(cfg):
    T = cfg["theme"]
    p = cfg["profile"]
    W, H = 850, 300
    CX, CY = 425, 160  # 星系核心位置
    arms = cfg["galaxy_arms"]
    arm_colors = {"cyan": T["cyan"], "violet": T["violet"], "amber": T["amber"]}
    rng = random.Random(cfg.get("random_seed", 42))

    s = []
    add = s.append
    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    add("  <defs>")
    add("    <style>")
    css = """      .star-bg { animation: twinkle-slow 7s ease-in-out infinite; }
      .star-mid { animation: twinkle-mid 5s ease-in-out infinite; }
      .star-fg { animation: twinkle-fast 3s ease-in-out infinite; }
      @keyframes twinkle-slow { 0%, 100% { opacity: 0.08; } 50% { opacity: 0.3; } }
      @keyframes twinkle-mid { 0%, 100% { opacity: 0.15; } 50% { opacity: 0.5; } }
      @keyframes twinkle-fast { 0%, 100% { opacity: 0.4; } 50% { opacity: 0.85; } }
      .core-ring { animation: pulse-core 3s ease-in-out infinite; }
      .core-ring-inner { animation: pulse-core 3s ease-in-out infinite 1.5s; }
      @keyframes pulse-core {
        0%, 100% { stroke-opacity: 0.3; transform: scale(1); transform-origin: __CX__px __CY__px; }
        50% { stroke-opacity: 0.8; transform: scale(1.06); transform-origin: __CX__px __CY__px; }
      }
      .shooting-star { opacity: 0; animation: shoot linear infinite; }
      @keyframes shoot {
        0% { opacity: 0; transform: translate(0, 0); }
        5% { opacity: 0.9; }
        15% { opacity: 0.6; transform: translate(var(--tx), var(--ty)); }
        20% { opacity: 0; transform: translate(var(--tx), var(--ty)); }
        100% { opacity: 0; }
      }"""
    add(css.replace("__CX__", str(CX)).replace("__CY__", str(CY)))
    add("    </style>")

    # 滤镜:星云模糊 / 发光
    add(f'    <filter id="nebula-outer"><feGaussianBlur stdDeviation="60"/></filter>')
    add(f'    <filter id="nebula-inner"><feGaussianBlur stdDeviation="30"/></filter>')
    add(f'    <filter id="label-glow" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="1.5"/></filter>')
    add(f'    <filter id="core-bright-glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="4"/></filter>')
    for name, c in (("cyan", T["cyan"]), ("violet", T["violet"]), ("amber", T["amber"])):
        add(f'    <filter id="star-glow-{name}" x="-100%" y="-100%" width="300%" height="300%">'
            f'<feGaussianBlur stdDeviation="3"/><feFlood flood-color="{c}" flood-opacity="0.55"/>'
            f'<feComposite in2="SourceGraphic" operator="in"/></filter>')
    add(f'    <radialGradient id="core-haze" cx="50%" cy="50%" r="50%">'
        f'<stop offset="0%" stop-color="{T["cyan"]}" stop-opacity="0.5"/>'
        f'<stop offset="50%" stop-color="{T["violet"]}" stop-opacity="0.2"/>'
        f'<stop offset="100%" stop-color="{T["cyan"]}" stop-opacity="0"/></radialGradient>')
    add(f'    <radialGradient id="core-inner" cx="50%" cy="50%" r="50%">'
        f'<stop offset="0%" stop-color="#ffffff" stop-opacity="0.6"/>'
        f'<stop offset="40%" stop-color="{T["cyan"]}" stop-opacity="0.3"/>'
        f'<stop offset="100%" stop-color="{T["cyan"]}" stop-opacity="0"/></radialGradient>')
    add(f'    <linearGradient id="shoot-grad" x1="0%" y1="0%" x2="100%" y2="0%">'
        f'<stop offset="0%" stop-color="#ffffff" stop-opacity="0.85"/>'
        f'<stop offset="100%" stop-color="#ffffff" stop-opacity="0"/></linearGradient>')
    add("  </defs>")

    # 1. 背景
    add(f'  <rect x="0" y="0" width="{W}" height="{H}" rx="14" ry="14" fill="{T["void"]}"/>')

    # 2. 星云光晕
    add(f'  <circle cx="245" cy="130" r="120" fill="{T["violet"]}" opacity="0.018" filter="url(#nebula-outer)"/>')
    add(f'  <circle cx="640" cy="180" r="110" fill="{T["amber"]}" opacity="0.014" filter="url(#nebula-outer)"/>')
    add(f'  <circle cx="{CX}" cy="{CY+40}" r="150" fill="{T["cyan"]}" opacity="0.012" filter="url(#nebula-outer)"/>')

    # 3. 星场(三层,固定种子可复现)
    star_colors = ["#ffffff", T["cyan"], T["violet"], T["amber"]]
    for layer, base_op in (("star-bg", 0.2), ("star-mid", 0.35), ("star-fg", 0.55)):
        for _ in range(46):
            x = rng.uniform(6, W - 6)
            y = rng.uniform(8, H - 8)
            r = rng.uniform(0.4, 1.0)
            c = rng.choice(star_colors)
            op = rng.uniform(base_op * 0.5, base_op)
            delay = round(rng.uniform(0, 6), 1)
            add(f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="{c}" opacity="{op:.2f}" '
                f'class="{layer}" style="animation-delay: {delay}s"/>')

    # 4. 流星(3 条,角度各异)
    meteors = [
        (110, 28, 205, 80, "0.0s", 6.5),
        (660, 22, 185, 72, "2.5s", 8.5),
        (395, 268, 165, 62, "5.0s", 7.5),
    ]
    for i, (x1, y1, tx, ty, delay, dur) in enumerate(meteors):
        add(f'  <line x1="{x1}" y1="{y1}" x2="{x1+18}" y2="{y1+6}" stroke="url(#shoot-grad)" '
            f'stroke-width="1.4" stroke-linecap="round" class="shooting-star" '
            f'style="animation-delay: {delay}; --tx: {tx}px; --ty: {ty}px; animation-duration: {dur}s"/>')

    # 5. 星系旋臂(每条臂:对数螺线,由内向外 3 段,透明度递减;另有粒子沿臂流动)
    arm_cfg = {
        "cyan": dict(a=32, k=0.44, theta0=0.0, theta1=3.2),
        "violet": dict(a=32, k=0.44, theta0=0.0, theta1=3.2),
        "amber": dict(a=32, k=0.44, theta0=0.0, theta1=3.2),
    }
    for idx, arm in enumerate(arms):
        color = arm_colors[arm["color"]]
        ac = arm_cfg[arm["color"]]
        offset = idx * (2 * math.pi / 3) - 0.785  # 三条臂各旋转 120°,整体朝上偏(避免探出画布下缘)
        segs = [
            (0.0, 1.2, 2.0, 0.55, 0.40),
            (1.2, 2.4, 1.5, 0.40, 0.28),
            (2.4, 3.2, 1.1, 0.28, 0.16),
        ]
        full_pts = []
        for (t0, t1, w, op1, op2) in segs:
            d, pts = spiral_path(CX, CY, ac["a"], ac["k"],
                                 ac["theta0"] + t0, ac["theta0"] + t1,
                                 n=40, arm_offset=offset)
            # 使路径方向向外,重采样用于粒子轨迹
            if idx == 0:
                full_pts = pts
            dur = 8.0 + idx
            add(f'  <path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" '
                f'opacity="{op1}" stroke-linecap="round">'
                f'<animate attributeName="opacity" values="{op2};{op1};{op2}" '
                f'dur="{dur}s" begin="{idx}s" repeatCount="indefinite"/></path>')
        # 粒子:沿整条螺线流动(animateMotion)
        d_full, _ = spiral_path(CX, CY, ac["a"], ac["k"], ac["theta0"], ac["theta0"] + 3.2,
                                n=140, arm_offset=offset)
        for p_idx in range(2):
            add(f'  <circle r="1.6" fill="{color}" opacity="0.7">')
            add(f'    <animateMotion dur="{14 + idx * 2}s" begin="{p_idx * (6 + idx)}s" '
                f'repeatCount="indefinite" path="{d_full}"/>')
            add(f'    <animate attributeName="opacity" values="0;0.75;0.3;0" '
                f'dur="{14 + idx * 2}s" begin="{p_idx * (6 + idx)}s" repeatCount="indefinite"/>')
            add('  </circle>')

        # 6. 臂上的技术标签:圆点 + 引导虚线 + 文字(文字位置避免重叠)
        n_items = len(arm["items"])
        for j, item in enumerate(arm["items"]):
            frac = 0.25 + 0.65 * (j / max(n_items - 1, 1))  # 沿臂的分布
            t = frac * 3.2
            r = ac["a"] * math.exp(ac["k"] * t)  # 半径只按局部进度
            theta = t + offset
            x, y = CX + r * math.cos(theta), CY + r * math.sin(theta)
            # 引导线端点:沿半径方向外移
            dx, dy = x - CX, y - CY
            length = math.hypot(dx, dy)
            ux, uy = dx / length, dy / length
            lx, ly = x + ux * 22, y + uy * 12
            anchor = "start" if x > CX + 30 else "end"
            tx = lx + (4 if anchor == "start" else -4)
            add(f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="{color}" opacity="0.9">'
                f'<animate attributeName="opacity" values="0.9;1;0.9" dur="5s" '
                f'begin="{j * 0.5}s" repeatCount="indefinite"/></circle>')
            add(f'  <line x1="{x:.1f}" y1="{y:.1f}" x2="{lx:.1f}" y2="{ly:.1f}" '
                f'stroke="{color}" stroke-width="0.5" opacity="0.3" stroke-dasharray="2 3"/>')
            add(f'  <text x="{tx:.1f}" y="{ly + 3:.1f}" text-anchor="{anchor}" fill="{color}" '
                f'font-size="9.5" font-family="monospace" opacity="0.25" filter="url(#label-glow)">{esc(item)}</text>')
            add(f'  <text x="{tx:.1f}" y="{ly + 3:.1f}" text-anchor="{anchor}" fill="{color}" '
                f'font-size="9.5" font-family="monospace" opacity="0.9">{esc(item)}</text>')

    # 7. 轨道环(两圈反向旋转的虚线椭圆)
    add(f'  <ellipse cx="{CX}" cy="{CY}" rx="62" ry="20" fill="none" stroke="{T["cyan"]}" '
        f'stroke-width="0.6" opacity="0.18" stroke-dasharray="4 6">'
        f'<animateTransform attributeName="transform" type="rotate" from="0 {CX} {CY}" '
        f'to="360 {CX} {CY}" dur="20s" repeatCount="indefinite"/></ellipse>')
    add(f'  <ellipse cx="{CX}" cy="{CY}" rx="84" ry="26" fill="none" stroke="{T["violet"]}" '
        f'stroke-width="0.5" opacity="0.12" stroke-dasharray="3 8">'
        f'<animateTransform attributeName="transform" type="rotate" from="360 {CX} {CY}" '
        f'to="0 {CX} {CY}" dur="30s" repeatCount="indefinite"/></ellipse>')

    # 8. 星系核心
    add(f'  <circle cx="{CX}" cy="{CY}" r="42" fill="url(#core-haze)" opacity="0.45"/>')
    add(f'  <circle cx="{CX}" cy="{CY}" r="25" fill="url(#core-inner)" opacity="0.6"/>')
    add(f'  <ellipse cx="{CX}" cy="{CY}" rx="21" ry="19" fill="none" stroke="{T["cyan"]}" '
        f'stroke-width="1.2" opacity="0.55" stroke-dasharray="5 3" class="core-ring"/>')
    add(f'  <circle cx="{CX}" cy="{CY}" r="14" fill="none" stroke="{T["violet"]}" '
        f'stroke-width="0.8" opacity="0.4" class="core-ring-inner"/>')
    add(f'  <circle cx="{CX}" cy="{CY}" r="11" fill="{T["nebula"]}" stroke="{T["star_dust"]}" stroke-width="0.5"/>')
    add(f'  <circle cx="{CX}" cy="{CY}" r="3" fill="{T["cyan"]}" filter="url(#core-bright-glow)" opacity="0.95"/>')
    add(f'  <text x="{CX}" y="{CY + 5}" text-anchor="middle" fill="{T["cyan"]}" '
        f'font-size="13" font-weight="bold" font-family="monospace">{esc(p["initial"])}</text>')

    # 9. 顶部文字与底部座右铭
    add(f'  <text x="{CX}" y="27" text-anchor="middle" fill="{T["text_bright"]}" '
        f'font-size="21" font-weight="bold" font-family="sans-serif">{esc(p["name"])}</text>')
    add(f'  <text x="{CX}" y="46" text-anchor="middle" fill="{T["text_dim"]}" '
        f'font-size="12.5" font-family="sans-serif">{esc(p["tagline"])} · {esc(p["tagline_cn"])}</text>')
    add(f'  <text x="{CX}" y="{H - 14}" text-anchor="middle" fill="{T["text_faint"]}" '
        f'font-size="11" font-family="monospace" font-style="italic">{esc(p["philosophy"])}</text>')

    add("</svg>")
    return "\n".join(s) + "\n"


# ---------------- 信息小卡片 ----------------

def build_cards(cfg):
    T = cfg["theme"]
    cards = cfg["cards"]
    n = len(cards)
    W = 850
    H = 168
    card_w, gap = (W - (n + 1) * 12) // n, 12
    x0 = 12
    s = []
    add = s.append
    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    add("  <defs>")
    add(f'    <filter id="card-glow" x="-50%" y="-50%" width="200%" height="200%">'
        f'<feGaussianBlur stdDeviation="6"/></filter>')
    add("  </defs>")

    colors = [T["cyan"], T["violet"], T["amber"]]
    for i, card in enumerate(cards):
        cx = x0 + i * (card_w + gap)
        c = colors[i % len(colors)]
        add(f'  <rect x="{cx}" y="10" width="{card_w}" height="{H - 20}" rx="12" '
            f'fill="{T["nebula"]}" stroke="{T["star_dust"]}" stroke-width="1"/>')
        add(f'  <rect x="{cx}" y="10" width="3.5" height="{H - 20}" rx="1.5" fill="{c}" opacity="0.85"/>')
        # 顶部:图标 + 标题
        add(f'  <text x="{cx + 22}" y="40" font-size="19">{card["icon"]}</text>')
        add(f'  <text x="{cx + 50}" y="42" fill="{T["text_bright"]}" font-size="14" font-weight="bold" '
            f'font-family="sans-serif">{esc(card["title"])}</text>')
        add(f'  <text x="{cx + 50 + 8 * len(card["title"])}" y="42" fill="{T["text_faint"]}" '
            f'font-size="11" font-family="sans-serif"> {esc(card["title_cn"])}</text>')
        # 内容行
        line_y = 68
        for line in card["lines"]:
            add(f'  <text x="{cx + 22}" y="{line_y}" fill="{T["text_dim"]}" font-size="11" '
                f'font-family="sans-serif">{esc(line)}</text>')
            line_y += 18
    add("</svg>")
    return "\n".join(s) + "\n"


# ---------------- 统计卡与仓库卡(数据来自 fetch_stats.py 生成的 stats.json) ----------------

LANG_COLORS = {
    "Python": "#3776AB", "Vue": "#42B883", "JavaScript": "#F7DF1E",
    "TypeScript": "#3178C6", "HTML": "#E34F26", "CSS": "#563D7C",
    "Astro": "#FF5D01", "Shell": "#89E051", "Makefile": "#427819",
    "Jupyter Notebook": "#DA5B0B", "C": "#555555", "C++": "#f34b7d",
    "Java": "#b07219", "Go": "#00ADD8", "Rust": "#dea584", "Other": "#8b949e",
}


def build_stats_card(cfg, stats):
    T = cfg["theme"]
    W, H = 850, 150
    s = []
    add = s.append
    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    add(f'  <rect x="0" y="0" width="{W}" height="{H}" rx="14" ry="14" fill="{T["void"]}"/>')
    add(f'  <rect x="0" y="0" width="4" height="{H}" rx="2" fill="{T["cyan"]}" opacity="0.9"/>')
    # 标题
    add(f'  <text x="24" y="28" fill="{T["text_bright"]}" font-size="13" font-weight="bold" '
        f'font-family="sans-serif">GitHub Stats · 数据遥测</text>')
    add(f'  <text x="{W - 24}" y="28" text-anchor="end" fill="{T["text_faint"]}" font-size="10" '
        f'font-family="monospace">updated {stats.get("updated_at", "—")}</text>')
    # 指标行
    metrics = [
        ("⭐", stats.get("stars", 0), "Stars"),
        ("📦", stats.get("repos", 0), "Repos"),
        ("✅", stats.get("year_commits", 0), "Commits (1y)"),
        ("👥", stats.get("followers", 0), "Followers"),
        ("🍴", stats.get("forks", 0), "Forks"),
        ("📝", stats.get("gists", 0), "Gists"),
    ]
    n = len(metrics)
    box_w = (W - 48 - (n - 1) * 12) // n
    x = 24
    for icon, value, label in metrics:
        add(f'  <rect x="{x}" y="40" width="{box_w}" height="58" rx="10" fill="{T["nebula"]}" '
            f'stroke="{T["star_dust"]}" stroke-width="1"/>')
        add(f'  <text x="{x + box_w // 2}" y="63" text-anchor="middle" font-size="15">{icon}</text>')
        add(f'  <text x="{x + box_w // 2}" y="84" text-anchor="middle" fill="{T["cyan"]}" '
            f'font-size="17" font-weight="bold" font-family="sans-serif">{value:,}</text>')
        add(f'  <text x="{x + box_w // 2}" y="96" text-anchor="middle" fill="{T["text_dim"]}" '
            f'font-size="9.5" font-family="sans-serif">{label}</text>')
        x += box_w + 12
    # 语言占比条
    langs = {k: v for k, v in (stats.get("languages") or {}).items() if k in LANG_COLORS or True}
    total = sum(langs.values()) if langs else 1
    items = sorted(langs.items(), key=lambda kv: -kv[1])[:6]
    bar_w = W - 48
    x = 24
    for lang, nbytes in items:
        frac = nbytes / total
        if frac < 0.005:
            continue
        w = max(int(bar_w * frac), 4)
        color = LANG_COLORS.get(lang, "#8b949e")
        add(f'  <rect x="{x}" y="112" width="{w}" height="8" rx="4" fill="{color}"/>')
        x += w
    # 语言标签
    lx = 24
    for lang, nbytes in sorted(langs.items(), key=lambda kv: -kv[1])[:6]:
        frac = nbytes / total
        if frac < 0.005:
            continue
        label = f'{lang} {frac * 100:.0f}%'
        add(f'  <text x="{lx}" y="136" fill="{T["text_dim"]}" font-size="9.5" '
            f'font-family="monospace">{esc(label)}</text>')
        lx += 24 + len(label) * 6.2
    add("</svg>")
    return "\n".join(s) + "\n"


def build_repo_cards(cfg, stats):
    T = cfg["theme"]
    repos = stats.get("featured_repos") or []
    W, H = 850, 118
    n = max(len(repos), 1)
    card_w, gap = (W - 48 - (n - 1) * 14) // n, 14
    s = []
    add = s.append
    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    x = 24
    for r in repos:
        add(f'  <rect x="{x}" y="8" width="{card_w}" height="{H - 16}" rx="12" fill="{T["void"]}" '
            f'stroke="{T["star_dust"]}" stroke-width="1"/>')
        # 顶部语言色点 + 仓库名
        color = LANG_COLORS.get(r.get("language") or "Other", "#8b949e")
        add(f'  <circle cx="{x + 16}" cy="28" r="4" fill="{color}"/>')
        add(f'  <text x="{x + 26}" y="32" fill="{T["cyan"]}" font-size="12.5" font-weight="bold" '
            f'font-family="monospace">{esc(r.get("name", ""))}</text>')
        # 描述(截断 2 行)
        desc = r.get("description") or "No description"
        if len(desc) > 34:
            desc = desc[:33] + "…"
        add(f'  <text x="{x + 16}" y="56" fill="{T["text_dim"]}" font-size="10.5" '
            f'font-family="sans-serif">{esc(desc)}</text>')
        # 底部:语言 + star
        add(f'  <text x="{x + 16}" y="92" fill="{color}" font-size="10" font-family="monospace">'
            f'{esc(r.get("language") or "Other")}</text>')
        add(f'  <text x="{x + card_w - 16}" y="92" text-anchor="end" fill="{T["amber"]}" '
            f'font-size="10" font-family="monospace">⭐ {r.get("stars", 0)}</text>')
        x += card_w + gap
    add("</svg>")
    return "\n".join(s) + "\n"


def load_stats():
    path = os.path.join(OUT_DIR, "stats.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


# ---------------- 主入口 ----------------

def load_config():
    path = os.path.join(HERE, "config.yml")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}
        # 与默认配置合并(只覆盖存在的键)
        cfg = {**DEFAULT_CONFIG, **user_cfg}
        cfg["profile"] = {**DEFAULT_CONFIG["profile"], **(user_cfg.get("profile") or {})}
        cfg["theme"] = {**DEFAULT_CONFIG["theme"], **(user_cfg.get("theme") or {})}
        if "galaxy_arms" in user_cfg:
            cfg["galaxy_arms"] = user_cfg["galaxy_arms"]
        if "cards" in user_cfg:
            cfg["cards"] = user_cfg["cards"]
        return cfg
    return dict(DEFAULT_CONFIG)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    cfg = load_config()
    stats = load_stats()
    files = {
        "galaxy-header.svg": build_header(cfg),
        "info-cards.svg": build_cards(cfg),
        "stats-card.svg": build_stats_card(cfg, stats),
        "repo-cards.svg": build_repo_cards(cfg, stats),
    }
    for name, content in files.items():
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✓ {path} ({os.path.getsize(path)} bytes)")


if __name__ == "__main__":
    main()
