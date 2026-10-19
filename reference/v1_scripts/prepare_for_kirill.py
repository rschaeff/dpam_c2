import sys
from multiprocessing import Pool

def get_stats(prot):
    mytotal = 0
    mydiso = set([])
    res2plddt = {}

    fp = open('step13/' + dataset + '/' + prot + '.diso','r')
    for line in fp:
        words = line.split()
        mydiso.add(int(words[0]))
    fp.close()

    fp = open('step2/' + dataset + '/' + prot + '.pdb','r')
    for line in fp:
        resid = int(line[22:26])
        plddt = float(line[60:66])
        res2plddt[resid] = plddt
    fp.close()
    return [prot, mydiso, res2plddt]


dataset = sys.argv[1]
fp = open(dataset + '_cif.list','r')
prots = []
for line in fp:
    words = line.split()
    prots.append(words[0])
fp.close()


prot2Gdoms = {}
prot2Odoms = {}
fp = open(dataset + '_domains','r')
for countl, line in enumerate(fp):
    words = line.split()
    if countl:
        prot = words[0]
        resids = set([])
        segments = words[2].split(',')
        for segment in segments:
            if '-' in segment:
                start = int(segment.split('-')[0])
                end = int(segment.split('-')[1])
                for resid in range(start, end + 1):
                    resids.add(resid)
            else:
                resids.add(int(segment))
        if words[10] == 'good_domain':
            try:
                prot2Gdoms[prot] = prot2Gdoms[prot].union(resids)
            except KeyError:
                prot2Gdoms[prot] = resids
        else:
            try:
                prot2Odoms[prot] = prot2Odoms[prot].union(resids)
            except KeyError:
                prot2Odoms[prot] = resids
fp.close()


prot2diso = {}
prot2plddt = {}
pool = Pool(processes = 32)
result = []
for prot in prots:
    try:
        prot2Gdoms[prot]
    except KeyError:
        prot2Gdoms[prot] = set([])
    try:
        prot2Odoms[prot]
    except KeyError:
        prot2Odoms[prot] = set([])
    process = pool.apply_async(get_stats, [prot])
    result.append(process)
for process in result:
    [prot, mydiso, res2plddt] = process.get()
    prot2diso[prot] = mydiso
    prot2plddt[prot] = res2plddt


for prot in prots:
    resids = list(prot2plddt[prot])
    resids.sort()
    rp = open('for_kirill/' + prot + '.result','w')
    for resid in resids:
        if resid in prot2Gdoms[prot]:
            judge = 'good_domain'
        elif resid in prot2Odoms[prot]:
            judge = 'other_domain'
        elif resid in prot2diso[prot]:
            judge = 'disorder'
        else:
            judge = 'non_domain'
        rp.write(str(resid) + '\t' + str(prot2plddt[prot][resid]) + '\t' + judge + '\n')
    rp.close()
