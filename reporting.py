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


def render(kind: str, payload: dict) -> dict:
    """统一入口，按动作分派。"""
    if kind == 'single':
        return render_single(payload)
    raise ValueError('暂不支持的报告类型: %s' % kind)
