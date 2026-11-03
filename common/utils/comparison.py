from decimal import Decimal


def calculate_amount_comparison(current_amount, previous_amount):
    """
    计算金额变化、方向和百分比。

    规则：
    1. 任一金额缺失时返回unknown，不用零代替缺失历史；
    2. 上期金额为零或负数时不计算百分比；
    3. 上期为零且本期大于零时标记new；
    4. 方向按原始差额判断，百分比保留两位小数。
    """
    if current_amount is None or previous_amount is None:
        return {"change_amount": None, "change_rate": None, "trend": "unknown"}

    difference = current_amount - previous_amount

    if difference == 0:
        trend = "unchanged"
    elif previous_amount == 0 and current_amount > 0:
        trend = "new"
    elif difference > 0:
        trend = "up"
    else:
        trend = "down"

    rate = None
    if previous_amount > 0:
        rate = (difference / previous_amount * Decimal("100")).quantize(
            Decimal("0.01")
        )
        # 避免很小的负变化四舍五入后显示为-0.00。
        if rate == 0:
            rate = Decimal("0.00")

    return {"change_amount": difference, "change_rate": rate, "trend": trend}
