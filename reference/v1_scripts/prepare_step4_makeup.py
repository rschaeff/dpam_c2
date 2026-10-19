import os, sys

fp = open('step4_redo_prots','r')
redo_prots = set([])
for line in fp:
    words = line.split()
    redo_prots.add(words[0])
fp.close()

if not os.path.exists('step4'):
    os.system('mkdir step4/')
dataset = sys.argv[1]
if not os.path.exists('step4/' + dataset):
    os.system('mkdir step4/' + dataset)

if os.path.exists('step4_' + dataset + '.job'):
    os.system('rm step4_' + dataset + '.job')
if os.path.exists('step4_' + dataset + '.cmds'):
    os.system('rm step4_' + dataset + '.cmds')
if os.path.exists('step4_' + dataset + '.out'):
    os.system('rm step4_' + dataset + '.out')
if os.path.exists('step4_' + dataset + '.log'):
    os.system('rm step4_' + dataset + '.log')

fp = open(dataset + '_cif.list', 'r')
prots = []
for line in fp:
    words = line.split()
    if words[0] in redo_prots:
        prots.append(words[0])
fp.close()

need_prots = []
for prot in prots:
    if os.path.exists('step4/' + dataset + '/' + prot + '.foldseek'):
        fp = open('step4/' + dataset + '/' + prot + '.foldseek','r')
        word_counts = set([])
        for line in fp:
            words = line.split()
            word_counts.add(len(words))
        fp.close()
        if len(word_counts) == 1 and 12 in word_counts:
            pass
        elif os.path.exists('step4/' + dataset + '/' + prot + '.done'):
            pass
        else:
            os.system('rm step4/' + dataset + '/' + prot + '.foldseek')
            need_prots.append(prot)
    else:
        need_prots.append(prot)


if need_prots:
    rp = open('step4_' + dataset + '.job', 'w')
    rp.write('#!/bin/bash\n')
    #rp.write('#SBATCH --exclude=compute-0-5\n')
    rp.write('#SBATCH --mem=250GB\n')
    rp.write('#SBATCH -p 256GB\n')
    rp.write('#SBATCH -N 1\n')
    rp.write('#SBATCH -n 32\n')
    rp.write('#SBATCH -o step4_' + dataset + '.out\n\n')
    rp.write('rm -rf /scratch/*\n')
    rp.write('cp -r /data/data1/conglab/qcong/for/domain_parser/model_organisms/ECOD_foldseek_DB* /scratch/\n')

    batch_size = len(need_prots) // 30 + 1
    for i in range(30):
        batch_prots = need_prots[i * batch_size: i * batch_size + batch_size]
        if batch_prots:
            listp = open('step4_' + dataset + '_' + str(i) + '.list', 'w')
            for prot in batch_prots:
                listp.write(prot + '\n')
            listp.close()
            rp.write('python step4_run_foldseek.py ' + dataset + ' ' + str(i) + ' &\n')
    rp.write('wait\n')
    rp.write('cat step4_' + dataset + '_*.log > step4_' + dataset + '.log\n')
    rp.write('rm -rf /scratch/*\n')
    rp.write('rm step4_' + dataset + '_*.list\n')
    rp.write('rm step4_' + dataset + '_*.log\n')
    rp.close()
