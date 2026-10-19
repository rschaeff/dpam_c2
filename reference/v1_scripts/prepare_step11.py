import os, sys

if not os.path.exists('step11'):
    os.system('mkdir step11/')
dataset = sys.argv[1]
if not os.path.exists('step11/' + dataset):
    os.system('mkdir step11/' + dataset)

if os.path.exists('step11_' + dataset + '.job'):
    os.system('rm step11_' + dataset + '.job')
if os.path.exists('step11_' + dataset + '.cmds'):
    os.system('rm step11_' + dataset + '.cmds')
if os.path.exists('step11_' + dataset + '.out'):
    os.system('rm step11_' + dataset + '.out')
if os.path.exists('step11_' + dataset + '.log'):
    os.system('rm step11_' + dataset + '.log')

fp = open(dataset + '_cif.list', 'r')
prots = []
for line in fp:
    words = line.split()
    prots.append(words[0])
fp.close()

need_prots = []
for prot in prots:
    if os.path.exists('step11/' + dataset + '/' + prot + '.goodDomains'):
        fp = open('step11/' + dataset + '/' + prot + '.goodDomains','r')
        seq_word_counts = set([])
        str_word_counts = set([])
        for line in fp:
            words = line.split()
            if words[0] == 'sequence':
                seq_word_counts.add(len(words))
            elif words[0] == 'structure':
                str_word_counts.add(len(words))
        fp.close()

        bad_seq = 0
        bad_str = 0
        if seq_word_counts:
            if len(seq_word_counts) == 1 and 10 in seq_word_counts:
                pass
            else:
                bad_seq = 1
        if str_word_counts:
            if len(str_word_counts) == 1 and 16 in str_word_counts:
                pass
            else:
                bad_str = 1

        if bad_seq or bad_str:
            os.system('rm step11/' + dataset + '/' + prot + '.goodDomains')
            need_prots.append(prot)
    elif os.path.exists('step11/' + dataset + '/' + prot + '.done'):
        pass
    else:
        need_prots.append(prot)


if need_prots:
    rp = open('step11_' + dataset + '.cmds', 'w')
    for prot in need_prots:
        rp.write('python step11_get_good_domains.py ' + dataset + ' ' + prot + '\n')
    rp.close()
    rp = open('step11_' + dataset + '.job', 'w')
    rp.write('#!/bin/bash\n')
    #rp.write('#SBATCH --exclude=compute-0-5\n')
    rp.write('#SBATCH --mem=250GB\n')
    rp.write('#SBATCH -p 256GB\n')
    rp.write('#SBATCH -N 1\n')
    rp.write('#SBATCH -n 32\n')
    rp.write('#SBATCH -o step11_' + dataset + '.out\n\n')
    rp.write('python batch_run.py step11_' + dataset + '.cmds 32\n')
    rp.close()
