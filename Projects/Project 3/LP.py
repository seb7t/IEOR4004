import DataLoader
import gurobipy as gp
from gurobipy import GRB
import networkx as nx
from tqdm import tqdm
from copy import deepcopy

class MaxFlow():
    def __init__(self, capacity):
        self.data_dir = './NewYorkElectricGrid/'
        self.capacity = capacity
        self.graph, self.source_nodes, self.target_nodes = DataLoader.dataLoader(self.data_dir, self.capacity)
        self.model, self.flowvar, self.flowamountvar = self.lpcreator('NewYorkElectricGrid')
    
    def lpcreator(self, name):
        print(f'----Creating model {name} with transmission capacity {self.capacity}----\n')
        m = gp.Model(name)
        flowvar = {}

        print(f'**** Adding Variables ****\n')
        for u, v, cap in tqdm(self.graph.edges.data('capacity')):
            flowvar[(u,v)] = m.addVar(name = f'f{u},{v}', ub = cap)
        flowamountvar = m.addVar(name = 'flow')

        print(f'**** Setting Objective ****\n')
        m.setObjective(flowamountvar, GRB.MAXIMIZE)

        print(f'**** Adding Constraints ****\n')
        for node in self.graph.nodes:
            expr = gp.LinExpr()
            for successor in self.graph.successors(node):
                expr += flowvar[(node, successor)]
            for predecessor in self.graph.predecessors(node):
                expr -= flowvar[(predecessor, node)]
            if node == '_s':
                m.addConstr(expr - flowamountvar == 0, name = f'Balance{node}')
            elif node == '_t':
                m.addConstr(expr + flowamountvar == 0, name = f'Balance{node}')
            else:
                m.addConstr(expr == 0, name = f'Balance{node}')
        m.update()
        m.write(f'{name}_{self.capacity}.lp')
        print(f'----Successfully created model {name} with transmission capacity {self.capacity}----\n')
        m.optimize()
        print(f'----Successfully optimized model {name} with transmission capacity {self.capacity}----\n')
        return m, flowvar, flowamountvar
    
    def get_branches_at_capacity(self):
        lst = []
        for u, v, cap in tqdm(self.graph.edges.data('capacity')):
          if abs(self.flowvar[(u, v)].x - cap) < 1e-6:
              lst.append((u, v))
              # print(f'The branch {(u, v)} is at capacity')
        return lst

    def flow_decomposition(self):
        G = deepcopy(self.graph)
        for u, v in G.edges:
            flow = self.flowvar[(u, v)].x
            if flow <= 1e-6:
                G.remove_edge(u, v)
            else:
                G[u][v]['flow'] = flow

        s = '_s'
        t = '_t'
        total = self.flowamountvar.x
        paths = []
        print('\n*** Flow Decomposition***\n')
        while total > 1e-6:
            path = [s]
            path_flow = float('inf')
            while path[-1] != t:
                curr_node = path[-1]
                next_nodes = [v for v in G.successors(curr_node) if G[curr_node][v]['flow'] > 1e-6]
                next_node = min(next_nodes, key = lambda x: nx.shortest_path_length(G, x, t))
                path.append(next_node)
                path_flow = min(path_flow, G[curr_node][next_node]['flow'])
            
            total -= path_flow
            paths.append((path, path_flow))
            print(f'path: {path}, path flow: {path_flow}\n')
            for i in range(1, len(path)):
                G[path[i-1]][path[i]]['flow'] -= path_flow
                if G[path[i-1]][path[i]]['flow'] <= 1e-6:
                    G.remove_edge(path[i-1], path[i])
        
        return paths
