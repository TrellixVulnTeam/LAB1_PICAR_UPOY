import math
import sys
import threading
import time
from unittest import case

import cv2
import matplotlib.pyplot as plt
import numpy as np

size = 30  # size of local map
unit = 5  # cm/grid
car_width = 16  # cm
car_length = 23.5
half_lg = int(car_length/unit / 2)  # 2
half_wg = int(car_width/unit/2)  # 1
half_size = int(size/2)
real_obs = []  # [y,x]
fake_obs = []
multiple = 3

polar_map = []
cart_map = np.zeros((size, size+1), dtype=int)  # local map
global_map = np.zeros((size*multiple+1, size*multiple+1),
                      dtype=int)  # local map
init_y = int(size*multiple/4)
init_x = int(size*multiple/2)
curr_y = int(size*multiple/4)
curr_x = int(size*multiple/2)
target_y = 0
target_x = 0
# Direction:0:screen down(0), 1:screen right(left90), 2:screen up(180), 3:screen left(right 90)
curr_dir = 0
curr_status = 0
stutas_list = []  # 0:routing 1:reach
movement_list = []
# map mark: 0:blank 1:real obs 2:fake obs 3:car center 4:car, 5:target
# assume car w: 3 grids,l: 5 grids
cv_detected = 0


def polar_mapping(step=18):
    global polar_map
    polar_map = []
    for angle in range(-90, 91, step):
        fc.get_distance_at(angle)
        polar_map.append(fc.angle_distance)
    return


def polar_to_cartesian():
    global cart_map, real_obs
    cart_map = np.zeros((size, size+1), dtype=int)
    real_obs = []
    for i in polar_map:
        if i[1] >= 0 and i[1] < size*unit/2:
            x = int(i[1]*math.sin(i[0]/180*math.pi)/unit)+half_size
            y = int(i[1]*math.cos(i[0]/180*math.pi)/unit)
            real_obs.append([y, x])
            cart_map[y][x] = 1

    return


def bound(base_x, base_y):
    base_x = max(0, base_x)
    base_x = min(size*multiple, base_x)
    base_y = max(0, base_y)
    base_y = min(size*multiple, base_y)
    return base_x, base_y


def mark_car():
    global cart_map, real_obs, global_map, fake_obs, curr_x, curr_y
    curr_x, curr_y = bound(curr_x, curr_y)
    if global_map[curr_y][curr_x] == 5:
        curr_status = 1
    else:
        curr_status = 0
    stutas_list.append(curr_status)
    global_map[curr_y][curr_x] = 3
    for i in range(-half_wg, half_wg+1):
        for j in range(-half_lg, half_lg+1):
            if curr_dir % 2 == 0:
                y = curr_y+j
                x = curr_x+i
            else:
                y = curr_y+i
                x = curr_x+j
            x, y = bound(x, y)
            if global_map[y][x] != 3:
                global_map[y][x] = 4
    return


def mark_obs():
    r2 = half_lg**2
    for obs in real_obs:
        if curr_dir == 0:
            base_y = curr_y+obs[0] + (half_lg+1)
            base_x = curr_x+obs[1]-half_size
        elif curr_dir == 1:
            base_y = curr_y-obs[1]+half_size
            base_x = curr_x+obs[0]+(half_lg+1)
        elif curr_dir == 2:
            base_y = curr_y-obs[0] - (half_lg+1)
            base_x = curr_x-obs[1]+half_size
        else:
            base_y = curr_y+obs[1] - half_size
            base_x = curr_x-obs[0]-(half_lg+1)
        base_x, base_y = bound(base_x, base_y)
        global_map[base_y][base_x] = 1
        # padding
        for i in range(-half_lg, half_lg+1):
            for j in range(-half_lg, half_lg + 1):
                if i**2+j**2 <= r2 and global_map[base_y+i][base_x+j] == 0:
                    global_map[base_y+i][base_x+j] = 2
    return


def update_map():
    # global cart_map, real_obs, global_map, fake_obs
    polar_to_cartesian()
    mark_obs()
    mark_car()
    return


def move_forward():
    global curr_y, curr_x, curr_dir
    if curr_dir == 0:
        curr_y += 1
    elif curr_dir == 1:
        curr_x += 1
    elif curr_dir == 2:
        curr_y -= 1
    else:
        curr_x -= 1
    mark_car()
    return


def move_backward():
    global curr_y, curr_x
    if curr_dir == 0:
        curr_y -= 1
    elif curr_dir == 1:
        curr_x -= 1
    elif curr_dir == 2:
        curr_y += 1
    else:
        curr_x += 1
    mark_car()
    return


def turn_left():
    global curr_dir, curr_y, curr_x
    curr_dir = (curr_dir+1) % 4


def move_left():
    turn_left()
    move_forward()
    mark_car()

    return


def turn_right():
    global curr_dir, curr_y, curr_x
    curr_dir = (curr_dir-1) % 4


def move_right():
    turn_right()
    move_forward()
    mark_car()

    return


def plot():
    plt.figure()
    plt.imshow(global_map)
    plt.show()


def set_target(rel_y=50, rel_x=50):  # relative position(cm) to car
    global curr_status, global_map, target_y, target_x
    curr_status = 0
    y = int(rel_y/unit)+curr_y
    x = int(rel_x/unit)+curr_x
    target_x, target_y = bound(x, y)
    global_map[y][x] = 5
    return


def route(steps=5):
    for i in range(steps):
        if curr_status == 0 and cv_detected == 0:
            opreation = 0  # should be a* function
            movement = (opreation-curr_dir) % 4
            movement_list.append(movement)
            if movement == 0:
                move_forward()
            elif movement == 1:
                move_left()
            elif movement == 2:
                move_backward()
            elif movement == 3:
                move_right()
    return


def self_driving():  # self driving until reach target
    set_target()
    while curr_status == 0:
        update_map()
        route()
        if cv2.waitKey(1) == 27:  # press esc
            break
    plot()
    return


def main():
    cv_thread = threading.Thread(target=detect, name='cvThread', daemon=True)
    cv_thread.start()

    for i in range(2):
        self_driving()
        print(cv_thread.name+' is alive ', cv_thread.isAlive())
    return


def test():
    return


def main():
    step_angle = 18
    global cart_map, global_map, curr_dir
    np.set_printoptions(threshold=10000, linewidth=1000)

    polar_map = [[i, 65-0.1*i]
                 for i in range(-3*step_angle, 3*step_angle+1, step_angle)]
    update_map()
    move_left()
    for i in range(20):
        move_forward()
    polar_map = [[i, 50-0.1*i]
                 for i in range(-1*step_angle, 5*step_angle+1, step_angle)]
    update_map()
    move_right()
    for i in range(20):
        move_forward()
    polar_map = [[i, 35-0.1*i]
                 for i in range(-2*step_angle, 5*step_angle+1, step_angle)]
    update_map()
    move_right()
    for i in range(20):
        move_forward()
    polar_map = [[i, 30-0.1*i]
                 for i in range(-5*step_angle, 5*step_angle+1, step_angle)]
    update_map()
    for i in range(10):
        move_backward()
    polar_map = [[i, 30]
                 for i in range(-5*step_angle, 5*step_angle+1, step_angle)]
    move_left()
    for i in range(20):
        move_forward()
    update_map()
    plot()
    return


if __name__ == "__main__":
    main()
