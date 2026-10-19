import os, sys

if not os.path.exists('step7'):
    os.system('mkdir step7/')
dataset = sys.argv[1]
if not os.path.exists('step7/' + dataset):
    os.system('mkdir step7/' + dataset)

if os.path.exists('step7_' + dataset + '.job'):
    os.system('rm step7_' + dataset + '.job')
if os.path.exists('step7_' + dataset + '.cmds'):
    os.system('rm step7_' + dataset + '.cmds')
if os.path.exists('step7_' + dataset + '.out'):
    os.system('rm step7_' + dataset + '.out')
if os.path.exists('step7_' + dataset + '.log'):
    os.system('rm step7_' + dataset + '.log')

fp = open(dataset + '_cif.list', 'r')
prots = []
for line in fp:
    words = line.split()
    prots.append(words[0])
fp.close()

need_prots = []
for prot in prots:
    if os.path.exists('step7/' + dataset + '/' + prot + '_hits'):
        pass
    elif os.path.exists('step7/' + dataset + '/' + prot + '.done'):
        pass
    else:
        need_prots.append(prot)

if need_prots:
    rp = open('step7_' + dataset + '.cmds', 'w')
    for prot in need_prots:
        rp.write('python step7_prepare_dali.py ' + dataset + ' ' + prot + '\n')
    rp.close()
    rp = open('step7_' + dataset + '.job', 'w')
    rp.write('#!/bin/bash\n')
    #rp.write('#SBATCH --exclude=compute-0-5\n')
    rp.write('#SBATCH --mem=250GB\n')
    rp.write('#SBATCH -p 256GB\n')
    rp.write('#SBATCH -N 1\n')
    rp.write('#SBATCH -n 32\n')
    rp.write('#SBATCH -o step7_' + dataset + '.out\n\n')
    rp.write('python batch_run.py step7_' + dataset + '.cmds 32\n')
    rp.close()
