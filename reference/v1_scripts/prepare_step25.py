import os, sys

if not os.path.exists('step25'):
    os.system('mkdir step25/')
dataset = sys.argv[1]
os.system('mkdir step25/' + dataset)
os.system('mkdir ' + dataset + '_web/')

fp = open(dataset + '_domains','r')
prots = set([])
for countl, line in enumerate(fp):
    if countl:
        words = line.split()
        prots.add(words[0])
fp.close()

rp = open('step25_' + dataset + '.cmds', 'w')
for prot in prots:
    os.system('mkdir ' + dataset + '_web/' + prot)
    rp.write('python step25_generate_pdbs.py ' + dataset + ' ' + prot + '\n')
rp.close()

rp = open('step25_' + dataset + '.job', 'w')
rp.write('#!/bin/bash\n')
rp.write('#SBATCH -p 256GB\n')
rp.write('#SBATCH -N 1\n')
rp.write('#SBATCH -n 32\n')
rp.write('#SBATCH -o step25_' + dataset + '.out\n\n')
rp.write('source activate /data/data1/conglab/jzhan6/anacodna3/pymol\n')
rp.write('python batch_run.py step25_' + dataset + '.cmds 32\n')
rp.close()
