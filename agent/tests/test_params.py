"""参数解析的强校验测试：畸形输入必须被夹住或转澄清。"""
from agent import params


def test_limit_parsed():
    result = params.parse_rules('把最近三次整理成报告')
    assert result['ok'] and result['mode'] == 'limit' and result['n'] == 3


def test_days_parsed():
    result = params.parse_rules('最近 30 天的报告')
    assert result['ok'] and result['mode'] == 'days' and result['n'] == 30


def test_week_converted():
    result = params.parse_rules('最近两周的记录')
    assert result['ok'] and result['mode'] == 'days' and result['n'] == 14


def test_all():
    result = params.parse_rules('全部记录的汇总')
    assert result['ok'] and result['mode'] == 'all'


def test_limit_capped():
    result = params.parse_rules('最近 999 次')
    assert result['ok'] and result['n'] == params.MAX_LIMIT and result['capped']


def test_days_capped():
    result = params.parse_rules('最近 9999 天')
    assert result['ok'] and result['n'] == params.MAX_DAYS and result['capped']


def test_zero_rejected():
    result = params.parse_rules('最近 0 次')
    assert not result['ok']


def test_negative_rejected():
    result = params.parse_range('最近 -3 次')
    assert result.get('ok') is False and result.get('needs_clarify')


def test_garbage_clarify():
    result = params.parse_range('上个月最后那几次的东西')
    assert result['ok'] is False and result.get('needs_clarify')


def test_unknown_mode():
    result = params._clean('weird', 3)
    assert not result['ok'] and result['reason'] == 'unknown_mode'


def test_missing_n():
    result = params._clean('limit', None)
    assert not result['ok'] and result['reason'] == 'missing_n'


def test_wants_range():
    assert params.wants_range('把最近三次整理成报告')
    assert not params.wants_range('面积最大值是什么意思')
