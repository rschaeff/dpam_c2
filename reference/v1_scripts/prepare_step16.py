import os, sys

if not os.path.exists('step16'):
    os.system('mkdir step16/')
dataset = sys.argv[1]
if not os.path.exists('step16/' + dataset):
    os.system('mkdir step16/' + dataset)

if os.path.exists('step16_' + dataset + '.job'):
    os.system('rm step16_' + dataset + '.job')
if os.path.exists('step16_' + dataset + '.cmds'):
    os.system('rm step16_' + dataset + '.cmds')
if os.path.exists('step16_' + dataset + '.out'):
    os.system('rm step16_' + dataset + '.out')
if os.path.exists('step16_' + dataset + '.log'):
    os.system('rm step16_' + dataset + '.log')

fp = open(dataset + '_json.list', 'r')
prots = []
for line in fp:
    words = line.split()
    prots.append(words[0])
fp.close()

need_prots = []
for prot in prots:
    if os.path.exists('step16/' + dataset + '/' + prot + '.result'):
        word_counts = set([])
        fp = open('step16/' + dataset + '/' + prot + '.result', 'r')
        for line in fp:
            words = line.split()
            word_counts.add(len(words))
        fp.close()
        if len(word_counts) == 1 and 21 in word_counts:
            pass
        else:
            os.system('rm step16/' + dataset + '/' + prot + '.result')
            need_prots.append(prot)
    elif os.path.exists('step16/' + dataset + '/' + prot + '.done'):
        pass
    else:
        need_prots.append(prot)


if need_prots:
    batch_size = len(need_prots) // 16 + 1
    get_batches = []
    for i in range(16):
        batch_prots = need_prots[i * batch_size: i * batch_size + batch_size]
        if batch_prots:
            get_batches.append(i)
            rp = open('step16_' + dataset + '_' + str(i).rjust(2,'0') + '.list', 'w')
            for prot in batch_prots:
                rp.write(prot + '\n')
            rp.close()

    rp = open('step16_' + dataset + '.job', 'w')
    rp.write('#!/bin/bash\n')
    rp.write('#SBATCH --mem=250GB\n')
    rp.write('#SBATCH -p 256GB\n')
    rp.write('#SBATCH -N 1\n')
    rp.write('#SBATCH -n 32\n')
    rp.write('#SBATCH -o step16_' + dataset + '.out\n\n')
    rp.write('source activate dpamCPU\n')
    #rp.write('module add gcc/7.3.0\n')
    for i in get_batches:
        rp.write('python step16_run_domass.py ' + dataset + ' ' + str(i).rjust(2,'0') + ' &\n')
    rp.write('wait\n')
    rp.write('rm step16_' + dataset + '_*.list\n')
    rp.close()
