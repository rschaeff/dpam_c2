import os, sys

if not os.path.exists('step13'):
    os.system('mkdir step13/')
dataset = sys.argv[1]
if not os.path.exists('step13/' + dataset):
    os.system('mkdir step13/' + dataset)

if os.path.exists('step13_' + dataset + '.job'):
    os.system('rm step13_' + dataset + '.job')
if os.path.exists('step13_' + dataset + '.cmds'):
    os.system('rm step13_' + dataset + '.cmds')
if os.path.exists('step13_' + dataset + '.out'):
    os.system('rm step13_' + dataset + '.out')
if os.path.exists('step13_' + dataset + '.log'):
    os.system('rm step13_' + dataset + '.log')

fp = open(dataset + '_json.list', 'r')
cases = []
for line in fp:
    words = line.split()
    cases.append([words[0], words[1]])
fp.close()

need_cases = []
for case in cases:
    prot = case[0]
    if os.path.exists('step13/' + dataset + '/' + prot + '.diso'):
        pass
    else:
        need_cases.append(case)

if need_cases:
    rp = open('step13_' + dataset + '.cmds', 'w')
    for case in need_cases:
        rp.write('python step13_get_diso.py ' + dataset + ' ' + case[0] + ' ' + case[1] + '\n')
    rp.close()
    rp = open('step13_' + dataset + '.job', 'w')
    rp.write('#!/bin/bash\n')
    #rp.write('#SBATCH --exclude=compute-0-5\n')
    rp.write('#SBATCH --mem=250GB\n')
    rp.write('#SBATCH -p 256GB\n')
    rp.write('#SBATCH -N 1\n')
    rp.write('#SBATCH -n 32\n')
    rp.write('#SBATCH -o step13_' + dataset + '.out\n\n')
    rp.write('python batch_run.py step13_' + dataset + '.cmds 32\n')
    rp.close()
