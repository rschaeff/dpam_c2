import os, sys

if not os.path.exists('step2'):
    os.system('mkdir step2/')
dataset = sys.argv[1]
if not os.path.exists('step2/' + dataset):
    os.system('mkdir step2/' + dataset)

if os.path.exists('step2_' + dataset + '.job'):
    os.system('rm step2_' + dataset + '.job')
if os.path.exists('step2_' + dataset + '.cmds'):
    os.system('rm step2_' + dataset + '.cmds')
if os.path.exists('step2_' + dataset + '.out'):
    os.system('rm step2_' + dataset + '.out')

fp = open(dataset + '_cif.list', 'r')
cases = []
for line in fp:
    words = line.split()
    cases.append([words[0], words[1]])
fp.close()

cmds = []
for case in cases:
    fasta_length = 0
    if os.path.exists('step1/' + dataset + '/' + case[0] + '.fa'):
        fp = open('step1/' + dataset + '/' + case[0] + '.fa', 'r')
        for line in fp:
            if line[0] != '>':
                fasta_length = len(line[:-1])
        fp.close()

    pdb_resids = set([])
    if os.path.exists('step2/' + dataset + '/' + case[0] + '.pdb'):
        fp = open('step2/' + dataset + '/' + case[0] + '.pdb', 'r')
        for line in fp:
            if len(line) >= 50:
                if line[:4] == 'ATOM':
                    resid = int(line[22:26])
                    pdb_resids.add(resid)
        fp.close()
    pdb_length = len(pdb_resids)

    if fasta_length == pdb_length:
        if fasta_length:
            pass
        else:
            if os.path.exists('step2/' + dataset + '/' + case[0] + '.pdb'):
                os.system('rm step2/' + dataset + '/' + case[0] + '.pdb')
            cmds.append('python step2_get_AFDB_pdbs.py ' + dataset + ' ' + case[0] + ' ' + case[1] + '\n')
    else:
        if os.path.exists('step2/' + dataset + '/' + case[0] + '.pdb'):
            os.system('rm step2/' + dataset + '/' + case[0] + '.pdb')
        cmds.append('python step2_get_AFDB_pdbs.py ' + dataset + ' ' + case[0] + ' ' + case[1] + '\n')

if cmds:
    rp = open('step2_' + dataset + '.cmds', 'w')
    for cmd in cmds:
        rp.write(cmd)
    rp.close()
    rp = open('step2_' + dataset + '.job', 'w')
    rp.write('#!/bin/bash\n')
    #rp.write('#SBATCH --exclude=compute-0-5\n')
    rp.write('#SBATCH --mem=250GB\n')
    rp.write('#SBATCH -p 256GB\n')
    rp.write('#SBATCH -N 1\n')
    rp.write('#SBATCH -n 32\n')
    rp.write('#SBATCH -o step2_' + dataset + '.out\n\n')
    rp.write('python batch_run.py step2_' + dataset + '.cmds 32\n')
    rp.close()
