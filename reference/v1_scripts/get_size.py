import os, sys

dataset = sys.argv[1]
fp = open(dataset + '_cif.list', 'r')
prots = []
for line in fp:
    words = line.split()
    accession = words[0]
    version = words[1]
    prots.append(accession)
fp.close()

rp = open(dataset + '.size', 'w')
for prot in prots:
    fp = open('step1/' + dataset + '/' + prot + '.fa', 'r')
    seq = ''
    for line in fp:
        if line[0] == '>':
            pass
        else:
            seq += line[:-1]
    fp.close()
    rp.write(prot + '\t' + str(len(seq)) + '\n')
rp.close()
