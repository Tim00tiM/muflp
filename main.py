import random
import scipy.stats as sps
import itertools as it
import copy
import os
import concurrent
import math
import heapq

clients_count = random.randint(1, 10000)
facilities_count = random.randint(1, 10)

class Client:
    def __init__(self, x, y, idx):
        self.x = x
        self.y = y
        self.place = (x, y)
        self.idx = idx
        self.distances = dict()  
        self.tight_edges = set()
        self.tight_events = dict()
        self.connected = None

class Facility:
    def __init__(self, x, y, cost, idx):
        self.x = x
        self.y = y
        self.place = (x, y)
        self.idx = idx
        self.cost = cost       
        self.open_time: float = None   
        self.tight_edges = set() 
        self.open_event: Event = None
        self.witness : int = None
        self.witness_time : float = None

df = random.randint(1, 100)

rv = sps.uniform(0, 1000)

def dist(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

clients = {i: Client(*rv.rvs([2]), i) for i in range(clients_count)}
facilities = {j: Facility(*rv.rvs([2]), float(rv.rvs(1)), j) for j in range(facilities_count)}

for j, fac in facilities.items():
    for i, cl in clients.items():
        c = dist(fac.place, cl.place)
        fac.distances = fac.distances if hasattr(fac, 'distances') else dict()
        fac.distances[i] = c
        cl.distances[j] = c

# Печать входа
print("Клиенты (индекс: x, y):")
for i, cl in clients.items():
    print(f"{i}: {cl.x:.2f}, {cl.y:.2f}")

print("\nПредприятия (индекс: x, y, f_j):")
for j, f in facilities.items():
    print(f"{j}: {f.x:.2f}, {f.y:.2f}, cost={f.cost:.2f}")

# считаем приближение

class Event:
    def __init__(self, event_type, payload):
        self.type = event_type # tight или open
        self.payload = payload # (i, j) или (j, k, remain_time, timestamp) - k - количество активных

event_heap = []                         
entry_finder = {}               
REMOVED = '<removed-task>'      
counter = it.count()     

# код украден с документации питона
def add_task(task, priority=0):
    'Add a new task or update the priority of an existing task'
    if task in entry_finder:
        remove_task(task)
    count = next(counter)
    entry = [priority, count, task]
    entry_finder[task] = entry
    heapq.heappush(event_heap, entry)

def remove_task(task):
    'Mark an existing task as REMOVED.  Raise KeyError if not found.'
    if task in entry_finder:
        entry = entry_finder.pop(task)
        entry[-1] = REMOVED

def pop_task():
    'Remove and return the lowest priority task. Raise KeyError if empty.'
    while event_heap:
        priority, count, task = heapq.heappop(event_heap)
        if task is not REMOVED:
            del entry_finder[task]
            return priority, task
    raise KeyError('pop from an empty priority queue')

class State:
    def __init__(self):
        pass

# init
for j, fac in facilities.items():
    for i, cl in clients.items():
        c = dist(fac.place, cl.place)
        add_task(Event("tight", (i, j)), c)

event = None
curr_time = 0
while True:
    try:
        end_time, event = pop_task()
    except:
        break
    

    curr_time = end_time
    if event.type == "tight":
        i, j = event.payload
        if clients[i].connected is not None:
            continue

        clients[i].tight_edges.add(j)
        facilities[j].tight_edges.add(i)
        if facilities[j].open_time is not None:
            clients[i].connected = j
            continue

        open_event = facilities[j].open_event
        if open_event is not None:
            j2, k, remain_time, timestamp = open_event.payload
            remain_time = remain_time - (timestamp - curr_time) * k
            open_event.payload = (j2, k + 1, remain_time, curr_time) 
            add_task(event, curr_time + remain_time / (k + 1))
        else:
            new_event = Event("open", (j, 1, facilities[j].cost, curr_time))
            facilities[j].open_event = new_event
            clients[i].tight_events[j] = new_event
            add_task(new_event, curr_time + facilities[j].cost)

    if event.type == "open":
        j, k, remain_time, timestamp = event.payload
        if k == 0:
            raise("k == 0")
        for client in facilities[j].tight_edges:
            if clients[client].connected is not None:
                continue
            clients[client].connected = j

            for tight_edge in clients[client].tight_edges:
                if tight_edge == j:
                    continue

                edit_event = facilities[tight_edge].open_event
                j2, k, remain_time, timestamp = edit_event.payload
                remain_time = remain_time - (timestamp - curr_time) * k
                edit_event.payload = (j2, k - 1, remain_time, curr_time)
                if k - 1 == 0:
                    remove_task(edit_event)
                else:
                    add_task(event, curr_time + remain_time / (k - 1))

        facilities[j].open_time = curr_time

for i, cl in clients.items():
    print(f"i: {i}, con: {cl.connected}, tight: {cl.tight_edges}")


F_t = []
for j, fc in facilities.items():
    if fc.open_time is not None:
        F_t.append([fc.open_time, j, fc])

F_t.sort(key=lambda x: x[0])
print([fc.open_time for j, fc in facilities.items()])

fc : Facility = None
H = set()
for item in F_t:
    _, j, fc = item
    for tight_to_client in fc.tight_edges:
        common = H.intersection(clients[tight_to_client].tight_edges)
        if len(common) > 0:
            for j2 in common:
                if fc.witness_time is None or facilities[j2].open_time < fc.witness_time:
                    fc.witness_time = facilities[j2].open_time
                    fc.witness = j2

    if fc.witness is None:
        H.add(j)

j = None
for i, cl in clients.items():
    intersect = H.intersection(cl.tight_edges)
    if len(intersect) > 0:
        cl.connected = intersect.pop()
        continue

    while True: 
        j = cl.tight_edges.pop()
        if facilities[j].open_time is not None:
            break
    cl.connected = facilities[j].witness

print()
print(H)
print()


for i, cl in clients.items():
    print(f"i: {i}, con: {cl.connected}, tight: {cl.tight_edges}")

total_cost = 0
powered = set()
for i, cl in clients.items():
    total_cost += dist(cl.place, facilities[cl.connected].place)
    powered.add(cl.connected)

for j in powered:
    total_cost += facilities[j].cost

print(total_cost)

print("Лучший результат")
# total_cost = 1e1000
# min_way = []

# def calculate_min(first_place):
#     possible_variants = it.product(range(facilities_count), repeat=clients_count - 1)
#     local_min_way = []
#     local_total_cost = 1e1000
#     for i in possible_variants:
#         i = [first_place] + list(i)
#         current_cost = 0
#         unique_facilities = set(i)
#         for j in unique_facilities:
#             current_cost += facilities[j].cost
        
#         for j in range(len(i)):
#             current_cost += clients[j].distances[i[j]]

#         if current_cost < local_total_cost:
#             local_total_cost = current_cost
#             local_min_way = copy.copy(i)

#     return local_total_cost, local_min_way

# with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
#     tasks = {executor.submit(calculate_min, i) for i in range(facilities_count)}
#     for future in concurrent.futures.as_completed(tasks):
#         current_cost, current_min_way = future.result()
#         if current_cost < total_cost:
#             total_cost = current_cost
#             min_way = current_min_way

def calculate_min_cool_way():
    possible_variants = it.product(range(2), repeat = facilities_count)
    total_cost = 1e10000
    min_facs = []
    for i in possible_variants:
        possible_cost = 0
        unique_facilities = [j for j in range(len(i)) if i[j] == 1]
        for j in unique_facilities:
            possible_cost += facilities[j].cost
        for j in clients:
            client_min = 1e10000
            for z in unique_facilities:
                client_min = min(client_min, clients[j].distances[z])
            possible_cost += client_min
        if total_cost > possible_cost:
            min_facs = copy.copy(unique_facilities)
            total_cost = possible_cost
    return total_cost, min_facs

# print(total_cost, min_way)
total_cost2, min_facs = calculate_min_cool_way()
print(total_cost2, min_facs)
print(total_cost / total_cost2)