import os, sys

if not os.path.exists('step12'):
    os.system('mkdir step12/')
dataset = sys.argv[1]
if not os.path.exists('step12/' + dataset):
    os.system('mkdir step12/' + dataset)

if os.path.exists('step12_' + dataset + '.job'):
    os.system('rm step12_' + dataset + '.job')
if os.path.exists('step12_' + dataset + '.cmds'):
    os.system('rm step12_' + dataset + '.cmds')
if os.path.exists('step12_' + dataset + '.out'):
    os.system('rm step12_' + dataset + '.out')
if os.path.exists('step12_' + dataset + '.log'):
    os.system('rm step12_' + dataset + '.log')

fp = open(dataset + '_cif.list', 'r')
prots = []
for line in fp:
    words = line.split()
    prots.append(words[0])
fp.close()

need_prots = []
for prot in prots:
    if os.path.exists('step12/' + dataset + '/' + prot + '.sse'):
        fp = open('step12/' + dataset + '/' + prot + '.sse', 'r')
        word_counts = set([])
        for line in fp:
            words = line.split()
            word_counts.add(len(words))
        fp.close()
        if len(word_counts) == 1 and 4 in word_counts:
            pass
        else:
            os.system('rm step12/' + dataset + '/' + prot + '.sse')
            need_prots.append(prot)
    else:
        need_prots.append(prot)

if need_prots:
    rp = open('step12_' + dataset + '.cmds', 'w')
    for prot in need_prots:
        rp.write('python step12_get_sse.py ' + dataset + ' ' + prot + '\n')
    rp.close()
    rp = open('step12_' + dataset + '.job', 'w')
    rp.write('#!/bin/bash\n')
    #rp.write('#SBATCH --exclude=compute-0-5\n')
    rp.write('#SBATCH --mem=250GB\n')
    rp.write('#SBATCH -p 256GB\n')
    rp.write('#SBATCH -N 1\n')
    rp.write('#SBATCH -n 32\n')
    rp.write('#SBATCH -o step12_' + dataset + '.out\n\n')
    rp.write('python batch_run.py step12_' + dataset + '.cmds 32\n')
    rp.close()
