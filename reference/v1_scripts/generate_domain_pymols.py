import os, sys

fp = open('pfam_need_pse','r')
need_pses = set([])
for line in fp:
    words = line.split()
    need_pses.add((words[0], words[1]))
fp.close()

dataset = sys.argv[1]
os.system('mkdir ' + dataset + '_pses')
fp = open(dataset + '_domains','r')
rp = open(dataset + '.pml','w')
for countl, line in enumerate(fp):
    if countl:
        words = line.split()
        prot = words[0]
        dname = words[1]
        if (prot, dname) in need_pses:
            drange = '+'.join(words[2].split(','))
            rp.write('load step2/' + dataset + '/' + prot + '.pdb, ' + prot + '\n')
            rp.write('color grey, ' + prot + '\n')
            rp.write('select ' + prot + '_' + dname + ', resi ' + drange + ' & ' + prot + '\n')
            rp.write('spectrum count, rainbow, ' + prot + '_' + dname + '\n')
            rp.write('delete selection ' + prot + '_' + dname + '\n')
            rp.write('save ' + dataset + '_pses/' + prot + '_' + dname + '.pse\n')
            rp.write('delete ' + prot + '\n')
rp.close()
os.system('pymol -c ' + dataset + '.pml >& pml_log')
