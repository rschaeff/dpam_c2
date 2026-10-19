import os, sys

dataset = sys.argv[1]
if not os.path.exists('step21'):
    os.system('mkdir step21')
for i in range(30):
    if os.path.exists('step21_' + dataset + '_' + str(i) + '.list'):
        os.system('rm step21_' + dataset + '_' + str(i) + '.list')
if os.path.exists('step21_' + dataset + '.job'):
    os.system('rm step21_' + dataset + '.job')
if os.path.exists('step21_' + dataset + '.cmds'):
    os.system('rm step21_' + dataset + '.cmds')
if os.path.exists('step21_' + dataset + '.out'):
    os.system('rm step21_' + dataset + '.out')
if os.path.exists('step21_' + dataset + '.log'):
    os.system('rm step21_' + dataset + '.log')

fp = os.popen('ls -1 step19/' + dataset + '/*.result')
prots = []
for line in fp:
    prot = line.split('/')[2].split('.')[0]
    prots.append(prot)
fp.close()

cases = []
all_cases = set([])
for prot in prots:
    fp = open('step19/' + dataset + '/' + prot + '.result', 'r')
    for line in fp:
        words = line.split()
        domain1 = words[0]
        resids1 = words[1]
        domain2 = words[2]
        resids2 = words[3]
        cases.append([prot, domain1, resids1, domain2, resids2])
        all_cases.add(prot + '_' + domain1 + '_' + domain2)
    fp.close()

get_cases = set([])
if os.path.exists('step21/' + dataset + '.result'):
    fp = open('step21/' + dataset + '.result','r')
    for line in fp:
        words = line.split()
        get_cases.add(words[0] + '_' + words[1] + '_' + words[2])
    fp.close()

if all_cases == get_cases:
    pass
else:
    cmdp = open('step21_' + dataset + '.job', 'w')
    cmdp.write('#!/bin/bash\n')
    #cmdp.write('#SBATCH --exclude=compute-0-5\n')
    cmdp.write('#SBATCH --mem=250GB\n')
    cmdp.write('#SBATCH -p 256GB\n')
    cmdp.write('#SBATCH -N 1\n')
    cmdp.write('#SBATCH -n 32\n')
    cmdp.write('#SBATCH -o step21_' + dataset + '.out\n\n')

    total = len(cases)
    batchsize = total // 30 + 1
    for i in range(30):
        rp = open('step21_' + dataset + '_' + str(i) + '.list', 'w')
        for case in cases[batchsize * i : batchsize * i + batchsize]:
            rp.write(case[0] + '\t' + case[1] + '\t' + case[2] + '\t' + case[3] + '\t' + case[4] + '\n')
        rp.close()
        cmdp.write('python step21_compare_domains.py ' + dataset + ' ' + str(i) + ' &\n')
    cmdp.write('wait\n')
    cmdp.write('cat step21_' + dataset + '_*.result > step21/' + dataset + '.result\n')
    cmdp.write('rm step21_' + dataset + '_*.list\n')
    cmdp.write('rm step21_' + dataset + '_*.result\n')
    cmdp.close()
