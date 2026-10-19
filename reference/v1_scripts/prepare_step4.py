import os, sys

if not os.path.exists('step4'):
    os.system('mkdir step4/')
dataset = sys.argv[1]
threads = int(sys.argv[2])
if not os.path.exists('step4/' + dataset):
    os.system('mkdir step4/' + dataset)

parts = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P']
for i in range(100):
    for part in parts:
        if os.path.exists('step4_' + dataset + '_' + str(i) + part + '.list'):
            os.system('rm step4_' + dataset + '_' + str(i) + part + '.list')
    if os.path.exists('step4_' + dataset + '_' + str(i) + '.job'):
        os.system('rm step4_' + dataset + '_' + str(i) + '.job')
    if os.path.exists('step4_' + dataset + '_' + str(i) + '.cmds'):
        os.system('rm step4_' + dataset + '_' + str(i) + '.cmds')
    if os.path.exists('step4_' + dataset + '_' + str(i) + '.out'):
        os.system('rm step4_' + dataset + '_' + str(i) + '.out')
    if os.path.exists('step4_' + dataset + '_' + str(i) + '.log'):
        os.system('rm step4_' + dataset + '_' + str(i) + '.log')

fp = open(dataset + '_cif.list', 'r')
prots = []
for line in fp:
    words = line.split()
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
    batch_num = threads * len(parts)
    batch_size = len(need_prots) // batch_num + 1
    for i in range(threads):
        for j in range(len(parts)):
            k = i * len(parts) + j
            part = parts[j]
            batch_prots = need_prots[k * batch_size: k * batch_size + batch_size]
            if batch_prots:
                listp = open('step4_' + dataset + '_' + str(i) + part + '.list', 'w')
                for prot in batch_prots:
                    listp.write(prot + '\n')
                listp.close()

    for i in range(threads):
        rp = open('step4_' + dataset + '_' + str(i) + '.job', 'w')
        rp.write('#!/bin/bash\n')
        #rp.write('#SBATCH --exclude=compute-0-5\n')
        rp.write('#SBATCH --mem=250GB\n')
        rp.write('#SBATCH -p 256GB\n')
        rp.write('#SBATCH -N 1\n')
        rp.write('#SBATCH -n 32\n')
        rp.write('#SBATCH -o step4_' + dataset + '_' + str(i) + '.out\n\n')
        rp.write('rm -rf /scratch/*\n')
        rp.write('cp -r /data/data1/conglab/qcong/for/domain_parser/model_organisms/ECOD_foldseek_DB* /scratch/\n')
        for part in parts:
            rp.write('python step4_run_foldseek.py ' + dataset + ' ' + str(i) + part + ' &\n')
        rp.write('wait\n')
        rp.write('cat step4_' + dataset + '_' + str(i) + '?.log >> step4_' + dataset + '_' + str(i) + '.log\n')
        rp.write('rm -rf /scratch/*\n')
        rp.write('rm step4_' + dataset + '_' + str(i) + '?.list\n')
        rp.write('rm step4_' + dataset + '_' + str(i) + '?.log\n')
        rp.close()
