import os, sys

if not os.path.exists('step10'):
    os.system('mkdir step10/')
dataset = sys.argv[1]
if not os.path.exists('step10/' + dataset):
    os.system('mkdir step10/' + dataset)

if os.path.exists('step10_' + dataset + '.job'):
    os.system('rm step10_' + dataset + '.job')
if os.path.exists('step10_' + dataset + '.cmds'):
    os.system('rm step10_' + dataset + '.cmds')
if os.path.exists('step10_' + dataset + '.out'):
    os.system('rm step10_' + dataset + '.out')
if os.path.exists('step10_' + dataset + '.log'):
    os.system('rm step10_' + dataset + '.log')

fp = open(dataset + '_cif.list', 'r')
prots = []
for line in fp:
    words = line.split()
    prots.append(words[0])
fp.close()

need_prots = set([])
for prot in prots:
    get_seq = 0
    if os.path.exists('step10/' + dataset + '/' + prot + '_sequence.result'):
        fp = open('step10/' + dataset + '/' + prot + '_sequence.result','r')
        word_counts = set([])
        for line in fp:
            words = line.split()
            word_counts.add(len(words))
        fp.close()
        if len(word_counts) == 1 and 8 in word_counts:
            get_seq = 1
        else:
            os.system('rm step10/' + dataset + '/' + prot + '_sequence.result')
            need_prots.add(prot)

    get_str = 0
    if os.path.exists('step10/' + dataset + '/' + prot + '_structure.result'):
        fp = open('step10/' + dataset + '/' + prot + '_structure.result','r')
        word_counts = set([])
        for line in fp:
            words = line.split()
            word_counts.add(len(words))
        fp.close()
        if len(word_counts) == 1 and 12 in word_counts:
            get_str = 1
        else:
            os.system('rm step10/' + dataset + '/' + prot + '_structure.result')
            need_prots.add(prot)

    if get_seq and get_str:
        pass
    elif os.path.exists('step10/' + dataset + '/' + prot + '.done'):
        pass
    else:
        need_prots.add(prot)


if need_prots:
    rp = open('step10_' + dataset + '.cmds', 'w')
    for prot in need_prots:
        rp.write('python step10_get_support.py ' + dataset + ' ' + prot + '\n')
    rp.close()
    rp = open('step10_' + dataset + '.job', 'w')
    rp.write('#!/bin/bash\n')
    #rp.write('#SBATCH --exclude=compute-0-5\n')
    rp.write('#SBATCH --mem=250GB\n')
    rp.write('#SBATCH -p 256GB\n')
    rp.write('#SBATCH -N 1\n')
    rp.write('#SBATCH -n 32\n')
    rp.write('#SBATCH -o step10_' + dataset + '.out\n\n')
    rp.write('python batch_run.py step10_' + dataset + '.cmds 32\n')
    rp.close()
