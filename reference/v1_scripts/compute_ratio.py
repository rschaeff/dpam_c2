import sys
from multiprocessing import Pool

def get_stats(prot):
    mytotal = 0
    mydiso = set([])
    mylow = set([])
    fp = open('step1/' + dataset + '/' + prot + '.fa','r')
    for line in fp:
        if line[0] == '>':
            pass
        else:
            mytotal += len(line[:-1])
    fp.close()

    fp = open('step13/' + dataset + '/' + prot + '.diso','r')
    for line in fp:
        words = line.split()
        mydiso.add(int(words[0]))
    fp.close()

    fp = open('step2/' + dataset + '/' + prot + '.pdb','r')
    for line in fp:
        resid = int(line[22:26])
        plddt = float(line[60:66])
        if plddt <= 70:
            mylow.add(resid)
    fp.close()
    return [prot, mytotal, mydiso, mylow]


dataset = sys.argv[1]
fp = open(dataset + '_cif.list','r')
prots = []
for line in fp:
    words = line.split()
    prots.append(words[0])
fp.close()

good_domain = 0
simple_topology = 0
low_confidence = 0
partial_domain = 0
prot2domain = {}
fp = open(dataset + '_domains','r')
for countl, line in enumerate(fp):
    words = line.split()
    if countl:
        resids = []
        segments = words[2].split(',')
        for segment in segments:
            if '-' in segment:
                start = int(segment.split('-')[0])
                end = int(segment.split('-')[1])
                for resid in range(start, end + 1):
                    resids.append(resid)
            else:
                resids.append(int(segment))
        if words[10] == 'good_domain':
            good_domain += len(resids)
        elif words[10] == 'low_confidence':
            low_confidence += len(resids)
        elif words[10] == 'simple_topology':
            simple_topology += len(resids)
        elif words[10] == 'partial_domain':
            partial_domain += len(resids)
        try:
            prot2domain[words[0]] = prot2domain[words[0]].union(set(resids))
        except KeyError:
            prot2domain[words[0]] = set(resids)
fp.close()


prot2total = {}
prot2diso = {}
prot2low = {}
pool = Pool(processes = 32)
result = []
for prot in prots:
    try:
        prot2domain[prot]
    except KeyError:
        prot2domain[prot] = set([])
    process = pool.apply_async(get_stats, [prot])
    result.append(process)
for process in result:
    [prot, mytotal, mydiso, mylow] = process.get()
    prot2total[prot] = mytotal
    prot2diso[prot] = mydiso
    prot2low[prot] = mylow

total_len = 0
total_diso = 0
total_low = 0
rp = open(dataset + '_result', 'w')
for prot in prots:
    prot_len = prot2total[prot]
    domain_len = len(prot2domain[prot])
    diso_len = len(prot2diso[prot].difference(prot2domain[prot]))
    low_len = len(prot2low[prot].difference(prot2diso[prot]).difference(prot2domain[prot]))
    total_len += prot_len
    total_diso += diso_len
    total_low += low_len
    rp.write(prot + '\t' + str(prot_len) + '\t' + str(domain_len) + '\t' + str(diso_len) + '\t' + str(low_len) + '\t' + str(round(float(domain_len + diso_len + low_len)/prot_len, 2)) + '\n')
rp.write(dataset + '\t' + str(total_len) + '\t' + str(total_low) + '\t' + str(total_diso) + '\t' + str(good_domain) + '\t' + str(low_confidence) + '\t' + str(partial_domain) + '\t' + str(simple_topology) + '\n')
rp.close()
