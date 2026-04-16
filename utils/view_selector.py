import numpy as np

def select_views(joints_list):

    # assume video rotation
    n = len(joints_list)

    front = joints_list[0]
    side = joints_list[n//2]
    back = joints_list[-1]

    return [front, side, back]