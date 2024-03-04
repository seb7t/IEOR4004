import numpy as np
import pandas as pd
from tqdm import tqdm
import networkx as nx
from copy import deepcopy

def dataReader(data_dir):
    # Read Data from csv files
    buses = pd.read_csv(data_dir+'nyisobuses.csv', skiprows=1, index_col=[0])
    branches = pd.read_csv(data_dir+'nyisobranches.csv')
    return buses, branches

def dataPreprocess(buses_original, branches_original):
    # Deepcopy the dfs
    buses = buses_original.copy(deep = True)
    branches = branches_original.copy(deep = True)

    """BUS"""
    # Get nan_indices_buses and duplicate_indices_buses
    # nan_indices_buses: the indices in buses where 'Gen MW' and 'Load MW' are both nan's
    nan_indices_buses = buses.index[buses['Gen MW'].isna() & buses['Load MW'].isna()].to_list()
    # duplicate_indices_buses: the indices in buses where 'Name' are duplicates
    duplicate_indices_buses = buses.index[buses.duplicated(subset = ['Name'], keep = False)].to_list()

    # # *************** NOT SURE IF WE SHOULD DO THE FOLLOWING STEP **************
    # # Drop the rows where 'Gen MW' and 'Load MW' are both nan's
    # buses.dropna(index = nan_indices_buses, inplace = True)

    # Get the Dictionary dup_dict_buses and not_first_dup_buses
    # dup_dict_buses:
    #     keys: the names of the duplicates bus
    #     values: list of indices sharing the same name, numerially ordered
    # not_first_dup_buses
    #     keys: the indices of buses after their respective first appearance
    #     values: the corresponding first appearance
    dup_dict_buses = {}
    not_first_dup_buses = {}
    for index in duplicate_indices_buses:
        name = buses.loc[index, 'Name']
        if name not in dup_dict_buses.keys():
            dup_dict_buses[name] = [index]
        else:
            dup_dict_buses[name].append(index)
            not_first_dup_buses[index] = dup_dict_buses[name][0]
    
    # For each duplicated bus, modify the 'Gen MW' and 'Load MW' of the first appearence
    # Fill in mean while omitting the nan and 0.0; if all are nan's then fill in 0.0
    for name in dup_dict_buses.keys():
        dup_list = dup_dict_buses[name]
        gen_mw = buses.loc[dup_list, 'Gen MW'].replace(0.0, np.nan).mean(skipna = True)
        buses.loc[dup_list[0], 'Gen MW'] = gen_mw if gen_mw != np.nan else 0.0
        load_mw = buses.loc[dup_list, 'Load MW'].replace(0.0, np.nan).mean(skipna = True)
        buses.loc[dup_list[0], 'Load MW'] = load_mw if load_mw != np.nan else 0.0
    
    # Drop all duplicates except the first appearance in buses
    buses.drop(index = list(not_first_dup_buses.keys()), inplace = True)

    # Fill 0.0 in all nans under 'Gen MW' and 'Load MW'
    buses.fillna({'Gen MW': 0.0, 'Load MW': 0.0}, inplace = True)

    """BRANCHES"""
    # During exploratory analysis, no nan is found in branches

    # For each branch, check if any of the bus numbers are duplicates found previously
    # If so, replace them with the indices of their first appearance
    for index in branches.index:
        b1 = branches.loc[index, ' first bus number'].astype('int64')
        b2 = branches.loc[index, ' second bus number'].astype('int64')
        if b1 in not_first_dup_buses.keys():
            branches.loc[index, ' first bus number'] = not_first_dup_buses[b1]
        if b2 in not_first_dup_buses.keys():
            branches.loc[index, ' second bus number'] = not_first_dup_buses[b2]
        # # *************** NOT SURE IF WE SHOULD DO THE FOLLOWING STEP **************
        # if (b1 in nan_indices_buses) or (b2 in nan_indices_buses):
        #     branches.drop(index = index, inplace = True)
    
    # Drop the duplicates in branches
    branches.drop_duplicates(subset = [' first bus number', ' second bus number'], keep = 'first', inplace = True)

    """Completion Check"""
    # Check every bus appearing in branches is in buses
    # & Check every bus in buses is in branches
    a = set(branches[[' first bus number', ' second bus number']].values.flatten().tolist())
    b = set(buses.index.to_list())
    assert a == b, "buses in Dataframe(buses) and buses in Dataframe(branches) don't match."

    return buses, branches

def dataLoader(data_dir, c):
    print('----Reading network files from' + data_dir + '----\n')
    buses_orig, branches_orig = dataReader(data_dir)
    print('----Preprocessing network files----\n')
    buses, branches = dataPreprocess(buses_orig, branches_orig)

    print('----Generating graph----\n')
    G = nx.DiGraph()
    source_nodes = []
    target_nodes = []
    G.add_node('_s', balance = 0)
    G.add_node('_t', balance = 0)
    for index in tqdm(branches.index):
        b1 = branches.loc[index, ' first bus number'].astype('int64')
        b2 = branches.loc[index, ' second bus number'].astype('int64')
        f1 = buses.loc[b1, 'Gen MW'] - buses.loc[b1, 'Load MW']
        f2 = buses.loc[b2, 'Gen MW'] - buses.loc[b2, 'Load MW']
        G.add_node(b1, balance = 0)
        G.add_node(b2, balance = 0)
        G.add_edge(b1, b2, capacity = c)
        G.add_edge(b2, b1, capacity = c)
        if (f1 > 0) and (b1 not in source_nodes):
            source_nodes.append(b1)
            G.add_edge('_s', b1, capacity = f1)
        elif (f1 < 0) and (b1 not in target_nodes):
            target_nodes.append(b1)
            G.add_edge(b1, '_t', capacity = -f1)
        if (f2 > 0) and (b2 not in source_nodes):
            source_nodes.append(b2)
            G.add_edge('_s', b2, capacity = f2)
        elif (f2 < 0) and (b2 not in target_nodes):
            target_nodes.append(b2)
            G.add_edge(b2, '_t', capacity = -f2)
    print('----Successfully generated graph----\n')
    return G, source_nodes, target_nodes
