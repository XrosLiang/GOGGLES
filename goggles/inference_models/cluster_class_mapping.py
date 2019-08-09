import numpy as np
from scipy.optimize import linear_sum_assignment


def construct_D(y_cluster,y_class):
    K = len(set(y_class))
    D = np.zeros(shape=(K,K))
    for i in range(K):
        for j in range(K):
            D[i][j] = -np.sum((y_cluster==i)&(y_class==j))
    return D


def solve_mapping(y_cluster,y_class):
    D = construct_D(y_cluster,y_class)
    row_ind, col_ind = linear_sum_assignment(D)
    return col_ind