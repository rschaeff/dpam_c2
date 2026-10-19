import os, sys

if not os.path.exists('step15a'):
    os.system('mkdir step15a/')
dataset = sys.argv[1]
if os.path.exists('step15a_' + dataset + '.job'):
    os.system('rm step15a_' + dataset + '.job')
if os.path.exists('step15a_' + dataset + '.cmds'):
    os.system('rm step15a_' + dataset + '.cmds')
if os.path.exists('step15a_' + dataset + '.out'):
    os.system('rm step15a_' + dataset + '.out')
if os.path.exists('step15a_' + dataset + '.log'):
    os.system('rm step15a_' + dataset + '.log')

fp = open(dataset + '_json.list', 'r')
prots = []
for line in fp:
    words = line.split()
    prots.append(words[0])
fp.close()

need_prots = []
for prot in prots:
    if os.path.exists('step15a/' + dataset + '/' + prot + '.data'):
        word_counts = set([])
        fp = open('step15a/' + dataset + '/' + prot + '.data', 'r')
        for line in fp:
            words = line.split()
            word_counts.add(len(words))
        fp.close()
        if len(word_counts) == 1 and 27 in word_counts:
            pass
        else:
            os.system('rm step15a/' + dataset + '/' + prot + '.data')
            need_prots.append(prot)
    else:
        if os.path.exists('step15a/' + dataset + '/' + prot + '.done'):
            pass
        else:
            need_prots.append(prot)

if need_prots:
    rp = open('step15a_' + dataset + '.cmds', 'w')
    for prot in need_prots:
        rp.write('python step15a_prepare_domass.py ' + dataset + ' ' + prot + '\n')
    rp.close()
    rp = open('step15a_' + dataset + '.job', 'w')
    rp.write('#!/bin/bash\n')
    #rp.write('#SBATCH --exclude=compute-0-5\n')
    rp.write('#SBATCH --mem=250GB\n')
    rp.write('#SBATCH -p 256GB\n')
    rp.write('#SBATCH -N 1\n')
    rp.write('#SBATCH -n 32\n')
    rp.write('#SBATCH -o step15a_' + dataset + '.out\n\n')
    rp.write('mkdir /scratch/' + dataset + '\n')
    rp.write('cp ECOD_maps.tar /scratch/\n')
    rp.write('tar -xf /scratch/ECOD_maps.tar -C /scratch/\n')
    rp.write('cp ecod.latest.domains /scratch/\n')
    rp.write('python batch_run.py step15a_' + dataset + '.cmds 32\n')
    rp.write('cp -r /scratch/' + dataset + ' step15a/\n')
    rp.close()
