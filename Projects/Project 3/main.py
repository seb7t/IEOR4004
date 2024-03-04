from LP import MaxFlow
import sys
import gurobipy as gp
from gurobipy import GRB
import networkx as nx
from tqdm import tqdm

def main():
    if len(sys.argv) != 2:
        sys.exit('usage: main.py capacity\n')
    
    capacity = float(sys.argv[1])
    mf = MaxFlow(capacity)
    branches_at_capacity = mf.get_branches_at_capacity()
    print(f'The lines at capacity are {branches_at_capacity}\n')
    paths = mf.flow_decomposition()
    print('----Flow Decomposition---\n')
    for path, path_flow in paths:
        print(f'path: {path}, flow at this path: {path_flow}')

if __name__ == '__main__':
    main()
