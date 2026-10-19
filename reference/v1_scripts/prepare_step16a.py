import os, sys

if not os.path.exists('step16a'):
    os.system('mkdir step16a/')
dataset = sys.argv[1]
if not os.path.exists('step16a/' + dataset):
    os.system('mkdir step16a/' + dataset)

if os.path.exists('step16a_' + dataset + '.job'):
    os.system('rm step16a_' + dataset + '.job')
if os.path.exists('step16a_' + dataset + '.cmds'):
    os.system('rm step16a_' + dataset + '.cmds')
if os.path.exists('step16a_' + dataset + '.out'):
    os.system('rm step16a_' + dataset + '.out')
if os.path.exists('step16a_' + dataset + '.log'):
    os.system('rm step16a_' + dataset + '.log')

fp = open(dataset + '_json.list', 'r')
prots = []
for line in fp:
    words = line.split()
    prots.append(words[0])
fp.close()

need_prots = []
for prot in prots:
    if os.path.exists('step16a/' + dataset + '/' + prot + '.result'):
        word_counts = set([])
        fp = open('step16a/' + dataset + '/' + prot + '.result', 'r')
        for line in fp:
            words = line.split()
            word_counts.add(len(words))
        fp.close()
        if len(word_counts) == 1 and 21 in word_counts:
            pass
        else:
            os.system('rm step16a/' + dataset + '/' + prot + '.result')
            need_prots.append(prot)
    elif os.path.exists('step16a/' + dataset + '/' + prot + '.done'):
        pass
    else:
        need_prots.append(prot)


if need_prots:
    batch_size = len(need_prots) // 8 + 1
    get_batches = []
    for i in range(8):
        batch_prots = need_prots[i * batch_size: i * batch_size + batch_size]
        if batch_prots:
            get_batches.append(i)
            rp = open('step16a_' + dataset + '_' + str(i) + '.list', 'w')
            for prot in batch_prots:
                rp.write(prot + '\n')
            rp.close()

    rp = open('step16a_' + dataset + '.job', 'w')
    rp.write('#!/bin/bash\n')
    #rp.write('#SBATCH --exclude=compute-0-5\n')
    rp.write('#SBATCH --mem=250GB\n')
    rp.write('#SBATCH -p 256GB\n')
    rp.write('#SBATCH -N 1\n')
    rp.write('#SBATCH -n 32\n')
    rp.write('#SBATCH -o step16a_' + dataset + '.out\n\n')
    for i in get_batches:
        rp.write('python step16a_get_data.py ' + dataset + ' ' + str(i) + ' &\n')
    rp.write('wait\n')
    rp.write('rm step16a_' + dataset + '_*.list\n')
    rp.close()
