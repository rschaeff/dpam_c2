import os, sys

if not os.path.exists('step14'):
    os.system('mkdir step14/')
dataset = sys.argv[1]
if not os.path.exists('step14/' + dataset):
    os.system('mkdir step14/' + dataset)
joblimit = int(sys.argv[2])

for i in range(joblimit):
    if os.path.exists('step14_' + dataset + '_' + str(i) + '.job'):
        os.system('rm step14_' + dataset + '_' + str(i) + '.job')
    if os.path.exists('step14_' + dataset + '_' + str(i) + '.cmds'):
        os.system('rm step14_' + dataset + '_' + str(i) + '.cmds')
    if os.path.exists('step14_' + dataset + '_' + str(i) + '.out'):
        os.system('rm step14_' + dataset + '_' + str(i) + '.out')
    if os.path.exists('step14_' + dataset + '_' + str(i) + '.log'):
        os.system('rm step14_' + dataset + '_' + str(i) + '.log')

fp = open(dataset + '_json.list', 'r')
cases = []
for line in fp:
    words = line.split()
    cases.append([words[0], words[1]])
fp.close()

need_cases = []
for case in cases:
    prot = case[0]
    if os.path.exists('step14/' + dataset + '/' + prot + '.domains'):
        word_counts = set([])
        fp = open('step14/' + dataset + '/' + prot + '.domains', 'r')
        for line in fp:
            words = line.split()
            word_counts.add(len(words))
        fp.close()
        if len(word_counts) == 1 and 2 in word_counts:
            pass
        else:
            os.system('rm step14/' + dataset + '/' + prot + '.domains')
            need_cases.append(case)
    elif os.path.exists('step14/' + dataset + '/' + prot + '.done'):
        pass
    else:
        need_cases.append(case)

if need_cases:
    batch_num = len(need_cases) // 1000 + 1
    if batch_num > joblimit:
        batch_num = joblimit
    batch_size = len(need_cases) // batch_num + 1
    for i in range(batch_num):
        batch_cases = need_cases[i * batch_size : i * batch_size + batch_size]
        if batch_cases:
            rp = open('step14_' + dataset + '_' + str(i) + '.cmds', 'w')
            for case in batch_cases:
                rp.write('python step14_parse_domains.py ' + dataset + ' ' + case[0] + ' ' + case[1] + '\n')
            rp.close()
            rp = open('step14_' + dataset + '_' + str(i) + '.job', 'w')
            rp.write('#!/bin/bash\n')
            #rp.write('#SBATCH --exclude=compute-0-5\n')
            rp.write('#SBATCH --mem=250GB\n')
            rp.write('#SBATCH -p 256GB\n')
            rp.write('#SBATCH -N 1\n')
            rp.write('#SBATCH -n 32\n')
            rp.write('#SBATCH -o step14_' + dataset + '_' + str(i) + '.out\n\n')
            rp.write('python batch_run.py step14_' + dataset + '_' + str(i) + '.cmds 32\n')
            rp.close()
