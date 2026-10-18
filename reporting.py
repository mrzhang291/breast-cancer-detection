"""报告渲染：把 agent 的结论变成可下载的产物（PDF / CSV）。

设计约束：
- 中文字体必须随仓库走（服务器没有中文字体）
- 图表用 matplotlib 出 PNG，再嵌进 PDF
- 所有产物落在 reports/<user_id>/ 下，文件名带参数哈希，天然幂等
- 渲染失败抛异常，由调用方决定降级
"""
import hashlib
import io
import os
import time

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from fpdf import FPDF  # noqa: E402

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, 'static', 'fonts', 'NotoSansSC-Regular.otf')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')

INK = (15, 23, 42)
MUTED = (100, 116, 139)
BRAND = (79, 70, 229)
GOOD = (5, 150, 105)
BAD = (220, 38, 38)

_FONT_READY = False
MAX_ROWS = 30


def _ensure_font():
    """把中文字体注册进 matplotlib（只做一次）。"""
    global _FONT_READY
    if _FONT_READY:
        return
    if os.path.exists(FONT_PATH):
        font_manager.fontManager.addfont(FONT_PATH)
        name = font_manager.FontProperties(fname=FONT_PATH).get_name()
        plt.rcParams['font.family'] = name
        plt.rcParams['axes.unicode_minus'] = False
    _FONT_READY = True


def _png(fig) -> bytes:
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                facecolor='white')
    plt.close(fig)
    buffer.seek(0)
    return buffer.read()


def chart_confidence(confidence: float, raw: float) -> bytes:
    """置信度刻度条：一条水平刻度 + 校准值/原始值标记。"""
    _ensure_font()
    fig, ax = plt.subplots(figsize=(6.4, 1.5))
    ax.barh([0], [confidence], height=0.34, color='#4f46e5', zorder=2)
    ax.barh([0], [1.0], height=0.34, color='#eef2ff', zorder=1)
    ax.plot([raw, raw], [-0.26, 0.26], color='#94a3b8', lw=1.4, ls='--', zorder=3)
    ax.text(confidence - 0.02, 0.30, '校准后 %.1f%%' % (confidence * 100),
            ha='right', va='bottom', fontsize=10, color='#4f46e5')
    ax.text(raw, -0.34, '原始 %.1f%%' % (raw * 100), ha='center', va='top',
            fontsize=8.5, color='#64748b')
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.7, 0.7)
    ax.set_yticks([])
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(['0', '25%', '50%', '75%', '100%'], fontsize=8, color='#94a3b8')
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color('#e2e8f0')
    ax.tick_params(axis='x', length=0)
    return _png(fig)


def chart_features(items) -> bytes:
    """Top-N 特征贡献横向条形图。items: [{'name': str, 'value': float}]"""
    _ensure_font()
    items = list(items)[:8][::-1]
    names = [it['name'] for it in items]
    values = [float(it['value']) for it in items]
    colors = ['#4f46e5' if v >= 0 else '#f87171' for v in values]

    fig, ax = plt.subplots(figsize=(6.4, 0.42 * len(items) + 1.0))
    ax.barh(range(len(items)), values, color=colors, height=0.6)
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels(names, fontsize=9, color='#334155')
    ax.axvline(0, color='#cbd5e1', lw=0.8)
    for idx, value in enumerate(values):
        offset = 0.01 * (max(values + [0.01]) - min(values + [0.0])) or 0.01
        ax.text(value + (offset if value >= 0 else -offset), idx,
                '%.3f' % value, va='center',
                ha='left' if value >= 0 else 'right',
                fontsize=8, color='#64748b')
    ax.set_xlabel('对恶性判断的贡献（正=推向恶性）', fontsize=8.5, color='#94a3b8')
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color('#e2e8f0')
    ax.tick_params(axis='y', length=0)
    ax.tick_params(axis='x', length=0, labelsize=8, colors='#94a3b8')
    return _png(fig)


class Report(FPDF):
    def __init__(self):
        super().__init__(format='A4')
        self.set_auto_page_break(auto=True, margin=18)
        self.font_ok = False
        if os.path.exists(FONT_PATH):
            try:
                self.add_font('Noto', '', FONT_PATH)
                self.font_ok = True
            except Exception:  # noqa: BLE001
                self.font_ok = False

    def use(self, size=10, style=''):
        if self.font_ok:
            self.set_font('Noto', style, size)
        else:
            self.set_font('Helvetica', style, size)

    def header_block(self, title, subtitle, footer_note=''):
        self.add_page()
        self.set_fill_color(*BRAND)
        self.rect(0, 0, 210, 4, style='F')

        self.set_xy(15, 16)
        self.use(16)
        self.set_text_color(*INK)
        self.cell(0, 9, title, ln=1)

        self.set_x(15)
        self.use(9)
        self.set_text_color(*MUTED)
        self.cell(0, 6, subtitle, ln=1)
        self.ln(2)

    def section(self, title):
        self.ln(3)
        self.use(11)
        self.set_text_color(*INK)
        self.cell(0, 7, title, ln=1)
        self.set_draw_color(226, 232, 240)
        y = self.get_y()
        self.line(15, y, 195, y)
        self.ln(3)

    def para(self, text, size=9.5):
        self.use(size)
        self.set_text_color(*INK)
        self.multi_cell(0, 5.6, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def kv_table(self, rows):
        self.use(9)
        for key, value in rows:
            self.set_text_color(*MUTED)
            self.cell(38, 6.5, str(key))
            self.set_text_color(*INK)
            self.multi_cell(0, 6.5, str(value), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def footer_note(self, text):
        self.set_y(-24)
        self.set_draw_color(226, 232, 240)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(2)
        self.use(7.5)
        self.set_text_color(*MUTED)
        self.multi_cell(0, 4.4, text, new_x="LMARGIN", new_y="NEXT")


def _stamp():
    return time.strftime('%Y-%m-%d %H:%M')


def _save(pdf: Report, user_id, run_id, kind, params_key) -> dict:
    digest = hashlib.sha1(('%s|%s|%s' % (kind, run_id, params_key)).encode()).hexdigest()[:10]
    folder = os.path.join(REPORTS_DIR, str(user_id))
    os.makedirs(folder, exist_ok=True)
    filename = '%s-%s-%s.pdf' % (kind, str(run_id)[:8], digest)
    path = os.path.join(folder, filename)
    pdf.output(path)
    return {
        'kind': 'pdf',
        'filename': filename,
        'path': path,
        'size': os.path.getsize(path),
        'mime': 'application/pdf',
        'created_at': int(time.time()),
    }


def render_single(payload: dict) -> dict:
    """① 单次预测报告。"""
    pred = payload.get('prediction') or {}
    out = pred.get('output') or '未知'
    conf = float(pred.get('confidence') or 0)
    raw = float(pred.get('raw_confidence') or conf)
    user = payload.get('username') or payload.get('user_id')
    record_no = payload.get('record_id') or '—'
    created = payload.get('created_at') or _stamp()

    features = payload.get('top_features') or []
    narrative = payload.get('narrative') or ''
    citations = payload.get('citations') or []

    pdf = Report()
    pdf.header_block('乳腺癌辅助分析报告',
                     '生成时间 %s · 记录号 %s · 用户 %s' % (_stamp(), record_no, user))

    pdf.section('预测结论')
    pdf.kv_table([
        ('结果', out),
        ('置信度（校准后）', '%.2f%%' % (conf * 100)),
        ('模型原始输出', '%.2f%%' % (raw * 100)),
        ('预测耗时', '%.3f 秒' % float(pred.get('time') or 0)),
    ])
    try:
        pdf.image(io.BytesIO(chart_confidence(conf, raw)), w=170)
    except Exception:  # noqa: BLE001
        pass

    if features:
        pdf.section('主要依据（特征贡献）')
        try:
            pdf.image(io.BytesIO(chart_features(features)), w=170)
        except Exception:  # noqa: BLE001
            pass

    if narrative:
        pdf.section('解读')
        pdf.para(narrative)

    if citations:
        pdf.section('引用条款')
        pdf.para('、'.join(citations[:12]))

    pdf.footer_note('本报告由系统自动生成，仅供教学演示，不用于临床诊断。'
                    '数据来源：%s' % created)
    return _save(pdf, payload.get('user_id'), payload.get('run_id'), 'single',
                 '%s|%s' % (out, conf))


def chart_diff(items) -> bytes:
    """两次记录的特征变化（百分比），正负分色。"""
    _ensure_font()
    items = list(items)[:8][::-1]
    names = ['%s' % it['name'] for it in items]
    values = [float(it['change_pct']) for it in items]
    colors = ['#4f46e5' if v >= 0 else '#f87171' for v in values]

    fig, ax = plt.subplots(figsize=(6.4, 0.42 * len(items) + 1.0))
    ax.barh(range(len(items)), values, color=colors, height=0.6)
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels(names, fontsize=9, color='#334155')
    ax.axvline(0, color='#cbd5e1', lw=0.8)
    span = max(abs(min(values)), abs(max(values))) or 1
    for idx, value in enumerate(values):
        offset = span * 0.03
        ax.text(value + (offset if value >= 0 else -offset), idx,
                '%+.0f%%' % value, va='center',
                ha='left' if value >= 0 else 'right',
                fontsize=8, color='#64748b')
    ax.set_xlim(-span * 1.35, span * 1.35)
    ax.set_xlabel('相对上一条记录的变化幅度', fontsize=8.5, color='#94a3b8')
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color('#e2e8f0')
    ax.tick_params(axis='y', length=0)
    ax.tick_params(axis='x', length=0, labelsize=8, colors='#94a3b8')
    return _png(fig)


def render_compare(payload: dict) -> dict:
    """② 两次记录对比报告。"""
    compare = payload.get('compare') or {}
    top = compare.get('top') or []
    changed = int(compare.get('changed_count') or 0)
    rising = int(compare.get('rising') or 0)
    falling = int(compare.get('falling') or 0)
    pred = payload.get('prediction') or {}
    user = payload.get('username') or payload.get('user_id')

    pdf = Report()
    pdf.header_block('乳腺癌预测对比报告',
                     '生成时间 %s · 用户 %s' % (_stamp(), user))

    pdf.section('对比摘要')
    pdf.kv_table([
        ('对比对象', '本次输入 vs 上一条记录'),
        ('本次结果', pred.get('output') or '未知'),
        ('变化项', '%d 项变化超过 5%%（上升 %d / 下降 %d）' % (changed, rising, falling)),
        ('最大差异', (top[0]['name_zh'] + ' %+.0f%%' % top[0]['change_pct']) if top else '—'),
    ])

    if top:
        pdf.section('特征变化')
        try:
            pdf.image(io.BytesIO(chart_diff(top)), w=170)
        except Exception:  # noqa: BLE001
            pass

        pdf.section('变化明细')
        pdf.use(9)
        pdf.set_text_color(*MUTED)
        pdf.cell(58, 6, '特征', ln=0)
        pdf.cell(32, 6, '上一条', ln=0, align='R')
        pdf.cell(32, 6, '本次', ln=0, align='R')
        pdf.cell(0, 6, '变化', ln=1, align='R')
        for item in top[:10]:
            pdf.set_text_color(*INK)
            pdf.cell(58, 6, item['name_zh'], ln=0)
            pdf.set_text_color(*MUTED)
            pdf.cell(32, 6, '%.2f' % item['previous'], ln=0, align='R')
            pdf.cell(32, 6, '%.2f' % item['current'], ln=0, align='R')
            color = BAD if item['change_pct'] > 0 else GOOD
            pdf.set_text_color(*color)
            pdf.cell(0, 6, '%+.0f%%' % item['change_pct'], ln=1, align='R')

    pdf.footer_note('本报告由系统自动生成，仅供教学演示，不用于临床诊断。'
                    '数值为两次输入之间的直接比较，不代表病情变化。')
    return _save(pdf, payload.get('user_id'), payload.get('run_id'), 'compare',
                 '|'.join('%s:%+.1f' % (i['name_zh'], i['change_pct']) for i in top[:6]))

def chart_trend(series) -> bytes:
    """置信度随时间的变化。series: [{'at','confidence','result'}]"""
    _ensure_font()
    labels = [s['at'][5:10] for s in series][::-1]
    values = [float(s['confidence']) for s in series][::-1]
    colors = ['#dc2626' if s['result'] in ('恶性', 'Malignant') else '#059669'
              for s in series][::-1]

    fig, ax = plt.subplots(figsize=(6.6, 2.2))
    ax.plot(range(len(values)), values, color='#c7d2fe', lw=1.6, zorder=1)
    ax.scatter(range(len(values)), values, c=colors, s=26, zorder=2)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=7.5, color='#94a3b8', rotation=0)
    ax.set_ylim(0, 1.05)
    ax.set_yticks([0, 0.5, 1.0])
    ax.set_yticklabels(['0', '50%', '100%'], fontsize=7.5, color='#94a3b8')
    ax.grid(axis='y', color='#eef2f8', lw=0.8)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color('#e2e8f0')
    ax.tick_params(length=0)
    ax.set_title('置信度变化（红=恶性 绿=良性）', fontsize=9, color='#64748b', pad=8)
    return _png(fig)


def chart_donut(benign: int, malignant: int) -> bytes:
    _ensure_font()
    fig, ax = plt.subplots(figsize=(2.6, 2.6))
    total = benign + malignant
    if total == 0:
        benign, malignant, total = 1, 0, 1
    ax.pie([benign, malignant], colors=['#34d399', '#f87171'],
           startangle=90, counterclock=False,
           wedgeprops={'width': 0.36, 'edgecolor': 'white', 'linewidth': 2})
    ax.text(0, 0.08, str(total), ha='center', va='center', fontsize=17, color='#0f172a')
    ax.text(0, -0.18, '总记录', ha='center', va='center', fontsize=8, color='#94a3b8')
    return _png(fig)


def render_range(payload: dict) -> dict:
    """③ 时间区间小结。"""
    stats = payload.get('stats') or {}
    series = payload.get('series') or []
    window = payload.get('window') or {}
    user = payload.get('username') or payload.get('user_id')

    mode = window.get('mode')
    n = window.get('n')
    if mode == 'days':
        win_text = '最近 %d 天' % n
    elif mode == 'limit':
        win_text = '最近 %d 条记录' % n
    else:
        win_text = '全部记录'

    pdf = Report()
    pdf.header_block('乳腺癌预测区间小结',
                     '生成时间 %s · 用户 %s · 范围：%s' % (_stamp(), user, win_text))

    pdf.section('概览')
    pdf.kv_table([
        ('记录数', stats.get('total', 0)),
        ('良性 / 恶性', '%d / %d' % (stats.get('benign', 0), stats.get('malignant', 0))),
        ('平均置信度', '%.2f%%' % (float(stats.get('avg_conf') or 0) * 100)),
        ('最高 / 最低', '%.2f%% / %.2f%%' % (float(stats.get('max_conf') or 0) * 100,
                                            float(stats.get('min_conf') or 0) * 100)),
    ])

    if series:
        pdf.section('置信度趋势')
        try:
            pdf.image(io.BytesIO(chart_trend(series)), w=170)
        except Exception:  # noqa: BLE001
            pass
        try:
            pdf.image(io.BytesIO(chart_donut(stats.get('benign', 0),
                                             stats.get('malignant', 0))), w=52)
        except Exception:  # noqa: BLE001
            pass

    pdf.section('记录明细')
    pdf.use(8.5)
    pdf.set_text_color(*MUTED)
    pdf.cell(20, 6, 'ID', ln=0)
    pdf.cell(38, 6, '时间', ln=0)
    pdf.cell(24, 6, '结果', ln=0)
    pdf.cell(0, 6, '置信度', ln=1, align='R')
    for row in series[:MAX_ROWS]:
        pdf.set_text_color(*INK)
        pdf.cell(20, 5.6, str(row.get('id', '')), ln=0)
        pdf.set_text_color(*MUTED)
        pdf.cell(38, 5.6, str(row.get('at', ''))[:16], ln=0)
        pdf.set_text_color(*(BAD if row.get('result') in ('恶性', 'Malignant') else GOOD))
        pdf.cell(24, 5.6, str(row.get('result', ''))[:4], ln=0)
        pdf.set_text_color(*INK)
        pdf.cell(0, 5.6, '%.2f%%' % (float(row.get('confidence') or 0) * 100), ln=1, align='R')

    if len(series) > MAX_ROWS:
        pdf.ln(2)
        pdf.use(8)
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 5, '仅展示最近 %d 条，共 %d 条。' % (MAX_ROWS, len(series)), ln=1)

    pdf.footer_note('本报告由系统自动生成，仅供教学演示，不用于临床诊断。'
                    '统计口径为当前账号的预测记录。')
    return _save(pdf, payload.get('user_id'), payload.get('run_id'), 'range',
                 '%s-%s-%s' % (mode, n, stats.get('total')))

def render_csv(payload: dict) -> dict:
    """⑤ 原始记录导出（CSV，带 BOM 以便 Excel 正确识别中文）。"""
    import csv

    rows = payload.get('series') or []
    folder = os.path.join(REPORTS_DIR, str(payload.get('user_id')))
    os.makedirs(folder, exist_ok=True)

    digest = hashlib.sha1(('csv|%s|%s' % (payload.get('run_id'), len(rows))).encode()).hexdigest()[:10]
    filename = 'records-%s-%s.csv' % (str(payload.get('run_id'))[:8], digest)
    path = os.path.join(folder, filename)

    with io.open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.writer(fh)
        writer.writerow(['记录号', '时间', '结果', '置信度'] + list(payload.get('feature_names') or []))
        for row in rows:
            writer.writerow([row.get('id'), row.get('at'), row.get('result'),
                             row.get('confidence')] + list(row.get('features') or []))

    return {
        'kind': 'csv',
        'filename': filename,
        'path': path,
        'size': os.path.getsize(path),
        'mime': 'text/csv',
        'created_at': int(time.time()),
    }

def render(kind: str, payload: dict) -> dict:
    """统一入口，按动作分派。"""
    if kind == 'single':
        return render_single(payload)
    if kind == 'compare':
        return render_compare(payload)
    if kind == 'range':
        return render_range(payload)
    if kind == 'csv':
        return render_csv(payload)
    raise ValueError('暂不支持的报告类型: %s' % kind)
