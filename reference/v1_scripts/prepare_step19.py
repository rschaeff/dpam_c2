import os, sys

if not os.path.exists('step19'):
    os.system('mkdir step19/')
dataset = sys.argv[1]
if not os.path.exists('step19/' + dataset):
    os.system('mkdir step19/' + dataset)

if os.path.exists('step19_' + dataset + '.job'):
    os.system('rm step19_' + dataset + '.job')
if os.path.exists('step19_' + dataset + '.cmds'):
    os.system('rm step19_' + dataset + '.cmds')
if os.path.exists('step19_' + dataset + '.out'):
    os.system('rm step19_' + dataset + '.out')
if os.path.exists('step19_' + dataset + '.log'):
    os.system('rm step19_' + dataset + '.log')

fp = open(dataset + '_json.list', 'r')
prots = []
for line in fp:
    words = line.split()
    prots.append(words[0])
fp.close()

need_prots = set([])
for prot in prots:
    check_info = 0
    if os.path.exists('step19/' + dataset + '/' + prot + '.info'):
        word_counts = set([])
        fp = open('step19/' + dataset + '/' + prot + '.info', 'r')
        for line in fp:
            words = line.split()
            word_counts.add(len(words))
        fp.close()
        if len(word_counts) == 1 and 2 in word_counts:
            check_info = 1
        else:
            os.system('rm step19/' + dataset + '/' + prot + '.info')
            need_prots.add(prot)

    check_result = 0
    if os.path.exists('step19/' + dataset + '/' + prot + '.result'):
        word_counts = set([])
        fp = open('step19/' + dataset + '/' + prot + '.result', 'r')
        for line in fp:
            words = line.split()
            word_counts.add(len(words))
        fp.close()
        if len(word_counts) == 1 and 4 in word_counts:
            check_result = 1
        else:
            os.system('rm step19/' + dataset + '/' + prot + '.result')
            need_prots.add(prot)

    if check_info and check_result:
        pass
    elif os.path.exists('step19/' + dataset + '/' + prot + '.done'):
        pass
    else:
        need_prots.add(prot)

if need_prots:
    rp = open('step19_' + dataset + '.cmds', 'w')
    for prot in need_prots:
        rp.write('python step19_get_merge_candidates.py ' + dataset + ' ' + prot + '\n')
    rp.close()
    rp = open('step19_' + dataset + '.job', 'w')
    rp.write('#!/bin/bash\n')
    #rp.write('#SBATCH --exclude=compute-0-5\n')
    rp.write('#SBATCH --mem=250GB\n')
    rp.write('#SBATCH -p 256GB\n')
    rp.write('#SBATCH -N 1\n')
    rp.write('#SBATCH -n 32\n')
    rp.write('#SBATCH -o step19_' + dataset + '.out\n\n')
    rp.write('python batch_run.py step19_' + dataset + '.cmds 32\n')
    rp.close()
