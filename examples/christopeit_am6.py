def calculate_watt(rpm, level=15):
    watt = ((3e-05 * (rpm-113.37718) ** 2) + 0.04069) * (level + 20.41185)

    if watt < 2.0:
        return 2.0
    elif watt > 566.0:
        return 566.0
    else:
        return watt
