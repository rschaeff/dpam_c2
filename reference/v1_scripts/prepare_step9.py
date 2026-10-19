import os, sys

if not os.path.exists('step9'):
    os.system('mkdir step9/')
dataset = sys.argv[1]
if not os.path.exists('step9/' + dataset):
    os.system('mkdir step9/' + dataset)

if os.path.exists('step9_' + dataset + '.job'):
    os.system('rm step9_' + dataset + '.job')
if os.path.exists('step9_' + dataset + '.cmds'):
    os.system('rm step9_' + dataset + '.cmds')
if os.path.exists('step9_' + dataset + '.out'):
    os.system('rm step9_' + dataset + '.out')
if os.path.exists('step9_' + dataset + '.log'):
    os.system('rm step9_' + dataset + '.log')

fp = open(dataset + '_cif.list', 'r')
prots = []
for line in fp:
    words = line.split()
    prots.append(words[0])
fp.close()

need_prots = []
for prot in prots:
    if os.path.exists('step9/' + dataset + '/' + prot + '_good_hits'):
        fp = open('step9/' + dataset + '/' + prot + '_good_hits','r')
        word_counts = set([])
        for line in fp:
            words = line.split()
            word_counts.add(len(words))
        fp.close()
        if len(word_counts) == 1 and 15 in word_counts:
            pass
        else:
            os.system('rm step9/' + dataset + '/' + prot + '_good_hits')
            need_prots.append(prot)
    else:
        if os.path.exists('step9/' + dataset + '/' + prot + '.done'):
            pass
        else:
            need_prots.append(prot)

if need_prots:
    rp = open('step9_' + dataset + '.cmds', 'w')
    for prot in need_prots:
        rp.write('python step9_analyze_dali.py ' + dataset + ' ' + prot + '\n')
    rp.close()
    rp = open('step9_' + dataset + '.job', 'w')
    rp.write('#!/bin/bash\n')
    #rp.write('#SBATCH --exclude=compute-0-5\n')
    rp.write('#SBATCH --mem=250GB\n')
    rp.write('#SBATCH -p 256GB\n')
    rp.write('#SBATCH -N 1\n')
    rp.write('#SBATCH -n 32\n')
    rp.write('#SBATCH -o step9_' + dataset + '.out\n\n')
    rp.write('python batch_run.py step9_' + dataset + '.cmds 32\n')
    rp.close()
