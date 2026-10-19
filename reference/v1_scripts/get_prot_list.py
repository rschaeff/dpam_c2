fp = open('list','r')
sps = []
for line in fp:
    words = line.split()
    sps.append(words[0])
fp.close()

rp = open('all_prots','w')
for sp in sps:
    fp = open(sp + '_cif.list','r')
    for line in fp:
        words = line.split()
        rp.write(sp + '\t' + words[0] + '\t' + words[1] + '\n')
    fp.close()
rp.close()
