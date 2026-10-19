import os, sys

if not os.path.exists('step1'):
    os.system('mkdir step1/')
dataset = sys.argv[1]
if not os.path.exists('step1/' + dataset):
    os.system('mkdir step1/' + dataset)

if os.path.exists('step1_' + dataset + '.job'):
    os.system('rm step1_' + dataset + '.job')
if os.path.exists('step1_' + dataset + '.cmds'):
    os.system('rm step1_' + dataset + '.cmds')
if os.path.exists('step1_' + dataset + '.out'):
    os.system('rm step1_' + dataset + '.out')

fp = open(dataset + '_cif.list', 'r')
cases = []
for line in fp:
    words = line.split()
    accession = words[0]
    version = words[1]
    cases.append([accession, version])
fp.close()

cmds = []
for case in cases:
    if os.path.exists('step1/' + dataset + '/' + case[0] + '.fa'):
        fp = open('step1/' + dataset + '/' + case[0] + '.fa', 'r')
        check_header = 0
        check_seq = 0
        check_length = 0
        for line in fp:
            check_length += 1
            if line[0] == '>':
                if line[1:-1] == case[0]:
                    check_header = 1
            else:
                if len(line) > 10:
                    check_seq = 1
        fp.close()
        if check_header and check_seq and check_length == 2:
            pass
        else:
            os.system('rm step1/' + dataset + '/' + case[0] + '.fa')
            cmds.append('python step1_get_AFDB_seqs.py ' + dataset + ' ' + case[0] + ' ' + case[1] + '\n')
    else:
        cmds.append('python step1_get_AFDB_seqs.py ' + dataset + ' ' + case[0] + ' ' + case[1] + '\n')

if cmds:
    rp = open('step1_' + dataset + '.cmds', 'w')
    for cmd in cmds:
        rp.write(cmd)
    rp.close()
    rp = open('step1_' + dataset + '.job', 'w')
    rp.write('#!/bin/bash\n')
    #rp.write('#SBATCH --exclude=compute-0-5\n')
    rp.write('#SBATCH --mem=250GB\n')
    rp.write('#SBATCH -p 256GB\n')
    rp.write('#SBATCH -N 1\n')
    rp.write('#SBATCH -n 32\n')
    rp.write('#SBATCH -o step1_' + dataset + '.out\n\n')
    rp.write('python batch_run.py step1_' + dataset + '.cmds 32\n')
    rp.close()
