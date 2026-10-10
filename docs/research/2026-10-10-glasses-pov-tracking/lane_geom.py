"""Image point -> top-down lane coordinates from one per-frame lane quad of a tracks JSON.

quad = tracks['lane'][str(f)] with fl_l, fl_r (lowest visible lane row, left/right edge), pd_l, pd_r (far end),
optional pin_y (pin-deck row in that frame) and vp ([x, y] of the edge lines' intersection).
board: 1 at the RIGHT edge, 39 at the LEFT edge, linear across the row (engine board_from_lines).
ft: distance from the foul line. s = (pin_y - vp_y) / (y - vp_y) is 1 at the pin row and falls as 1/(y - vp_y) toward
the camera; ft = a * s + b with a + b = 60. Default a=60, b=0 (camera foot at the foul line); tracks carry a fitted
(a, b) in lane_top_down_model (release at the foul line + constant ball speed), see fit_ft_model.
"""
LANE_FT = 60.0
TOTAL_BOARDS = 39


def edge_x(p, q, y):
    (x1, y1), (x2, y2) = p, q
    if abs(y2 - y1) < 1e-9:
        return float(x1)
    return x1 + (x2 - x1) * (y - y1) / (y2 - y1)


def vanishing_point(quad):
    (x1, y1), (x2, y2) = quad['fl_l'], quad['pd_l']
    (x3, y3), (x4, y4) = quad['fl_r'], quad['pd_r']
    la = (x2 - x1) / (y2 - y1) if abs(y2 - y1) > 1e-9 else 0.0
    ra = (x4 - x3) / (y4 - y3) if abs(y4 - y3) > 1e-9 else 0.0
    lb, rb = x1 - la * y1, x3 - ra * y3
    if abs(la - ra) < 1e-9:
        return None
    y = (rb - lb) / (la - ra)
    return [la * y + lb, y]


def pin_row(quad):
    if quad.get('pin_y') is not None:
        return float(quad['pin_y'])
    return 0.5 * (quad['pd_l'][1] + quad['pd_r'][1])


def depth_ratio(quad, y):
    vp = quad.get('vp') or vanishing_point(quad)
    py = pin_row(quad)
    if vp is None or y <= vp[1] + 1e-6 or py <= vp[1]:
        return None
    return (py - vp[1]) / (y - vp[1])


def fit_ft_model(samples, release_frame, min_n=8, a_range=(30.0, 120.0)):
    """samples [(f, s)] on the lane between release and pin hit. Solves a*(s-1) + 60 = v*(f - release) in least
    squares (ball at the foul line at release, constant speed). Returns the model dict; pin-only on a bad fit."""
    import numpy as np
    pin_only = {'kind': 'pin_only', 'a': LANE_FT, 'b': 0.0}
    if release_frame is None or len(samples) < min_n:
        return dict(pin_only, reason=f'{len(samples)} samples')
    f = np.array([q[0] for q in samples], float) - release_frame
    s = np.array([q[1] for q in samples], float)
    (a, v), *_ = np.linalg.lstsq(np.c_[s - 1.0, -f], -LANE_FT * np.ones_like(f), rcond=None)
    if not (a_range[0] <= a <= a_range[1]) or v <= 0:
        return dict(pin_only, reason=f'fit out of range a={a:.1f} v={v:.3f}')
    rmse = float(np.sqrt(np.mean((a * s + LANE_FT - a - v * f) ** 2)))
    return {'kind': 'cv_fit', 'a': round(float(a), 3), 'b': round(float(LANE_FT - a), 3), 'v_ft_per_frame': round(float(v), 4),
            'n': int(len(f)), 'rmse_ft': round(rmse, 2), 'implied_pin_frame': round(float(release_frame + LANE_FT / v), 1)}


def lane_point(quad, x, y, a=LANE_FT, b=0.0):
    """(board, ft) of image point (x, y) on the frame the quad belongs to; ft None when the row is at/above the VP."""
    xl = edge_x(quad['fl_l'], quad['pd_l'], y)
    xr = edge_x(quad['fl_r'], quad['pd_r'], y)
    w = xl - xr
    board = None if abs(w) < 1e-6 else (x - xr) / w * (TOTAL_BOARDS - 1) + 1.0
    s = depth_ratio(quad, y)
    return board, (None if s is None else a * s + b)


def image_point(quad, board, ft, a=LANE_FT, b=0.0):
    """Inverse of lane_point: (board, ft) -> (x, y) on the frame the quad belongs to; None when ft maps behind the VP."""
    vp = quad.get('vp') or vanishing_point(quad)
    if vp is None or abs(a) < 1e-9:
        return None
    s = (ft - b) / a
    py = pin_row(quad)
    if s <= 1e-6 or py <= vp[1]:
        return None
    y = vp[1] + (py - vp[1]) / s
    xl = edge_x(quad['fl_l'], quad['pd_l'], y)
    xr = edge_x(quad['fl_r'], quad['pd_r'], y)
    return xr + (board - 1.0) / (TOTAL_BOARDS - 1) * (xl - xr), y
