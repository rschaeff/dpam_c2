import os, sys
import numpy as np

dataset = sys.argv[1]
prots = []
fp = open(dataset + '_cif.list','r')
for line in fp:
    words = line.split()
    prots.append(words[0])
fp.close()

get_prots = set([])
prot2resids = {}
fp = open(dataset + '_domains','r')
for countl, line in enumerate(fp):
    if countl:
        words = line.split()
        prot = words[0]
        get_prots.add(prot)
        name = words[1]
        resids = set([])
        for seg in words[2].split(','):
            if '-' in seg:
                start = int(seg.split('-')[0])
                end = int(seg.split('-')[1])
                for res in range(start, end + 1):
                    resids.add(res)
            else:
                resids.add(int(seg))
        try:
            prot2resids[prot]
        except KeyError:
            prot2resids[prot] = {}
        prot2resids[prot][name] = resids
fp.close()


rp = open(dataset + '_daliz','w')
for prot in prots:
    allhits = []
    if os.path.exists('step16/' + dataset + '/' + prot + '.result'):
        fp = open('step16/' + dataset + '/' + prot + '.result','r')
        for countl, line in enumerate(fp):
            if countl:
                words = line.split()
                resids = set([])
                for seg in words[1].split(','):
                    if '-' in seg:
                        start = int(seg.split('-')[0])
                        end = int(seg.split('-')[1])
                        for res in range(start, end + 1):
                            resids.add(res)
                    else:
                        resids.add(int(seg))
                tgroup = words[2]
                DALIzscore = round(float(words[8]) * 10, 1)
                allhits.append([resids, tgroup, DALIzscore])
        fp.close()

    if allhits and prot in get_prots:
        for name in prot2resids[prot].keys():
            hits = []
            domain_resids = prot2resids[prot][name]
            for counti, item in enumerate(allhits):
                if item[0].issubset(domain_resids):
                    hits.append(item)
            if hits:
                hits.sort(key = lambda x:x[2], reverse = True)
                besthit = hits[0]
                rp.write(prot + '\t' + name + '\t' + besthit[1] + '\t' + str(besthit[2]) + '\n')
rp.close()
