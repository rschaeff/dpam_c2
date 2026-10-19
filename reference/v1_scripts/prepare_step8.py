import os, sys

if not os.path.exists('step8'):
    os.system('mkdir step8/')
dataset = sys.argv[1]
if not os.path.exists('step8/' + dataset):
    os.system('mkdir step8/' + dataset)
joblimit = int(sys.argv[2])

for i in range(joblimit):
    if os.path.exists('step8_' + dataset + '_' + str(i) + '.job'):
        os.system('rm step8_' + dataset + '_' + str(i) + '.job')
    if os.path.exists('step8_' + dataset + '_' + str(i) + '.cmds'):
        os.system('rm step8_' + dataset + '_' + str(i) + '.cmds')
    if os.path.exists('step8_' + dataset + '_' + str(i) + '.out'):
        os.system('rm step8_' + dataset + '_' + str(i) + '.out')
    if os.path.exists('step8_' + dataset + '_' + str(i) + '.log'):
        os.system('rm step8_' + dataset + '_' + str(i) + '.log')

fp = open(dataset + '_cif.list', 'r')
prots = []
for line in fp:
    words = line.split()
    prots.append(words[0])
fp.close()

need_prots = []
for prot in prots:
    if os.path.exists('step8/' + dataset + '/' + prot + '_hits'):
        hit_count = 0
        fp = open('step8/' + dataset + '/' + prot + '_hits', 'r')
        hit_lines = []
        hit_line_count = 0
        bad = 0
        for line in fp:
            if line[0] == '>':
                hit_count += 1
                if hit_line_count:
                    if hit_line_count + 4 != len(hit_lines):
                        bad = 1
                        break
                words = line.split()
                hit_line_count = int(words[2])
                hit_lines = []
            else:
                hit_lines.append(line)
        fp.close()
        if hit_line_count:
            if hit_line_count + 4 != len(hit_lines):
                bad = 1
        if bad:
            os.system('rm step8/' + dataset + '/' + prot + '_hits')
            need_prots.append(prot)
        elif hit_count:
            pass
        else:
            if os.path.exists('step8/' + dataset + '/' + prot + '.done'):
                pass
            else:
                os.system('rm step8/' + dataset + '/' + prot + '_hits')
                need_prots.append(prot)
    else:
        if os.path.exists('step8/' + dataset + '/' + prot + '.done'):
            pass
        else:
            need_prots.append(prot)

if need_prots:
    batch_size = len(need_prots) // joblimit + 1
    for i in range(joblimit):
        batch_prots = need_prots[i * batch_size: i * batch_size + batch_size]
        if batch_prots:
            rp = open('step8_' + dataset + '_' + str(i) + '.job', 'w')
            rp.write('#!/bin/bash\n')
            #rp.write('#SBATCH --exclude=compute-0-5\n')
            rp.write('#SBATCH --mem=250GB\n')
            rp.write('#SBATCH -p 256GB\n')
            rp.write('#SBATCH -N 1\n')
            rp.write('#SBATCH -n 32\n')
            rp.write('#SBATCH -o step8_' + dataset + '_' + str(i) + '.out\n\n')
            rp.write('rm -rf /scratch/*\n')
            rp.write('mkdir /scratch/ECOD_pdbs\n')
            for prot in batch_prots:
                rp.write('python step8_iterative_dali.py ' + dataset + ' ' + prot + '\n')
            rp.write('rm -rf /scratch/*\n')
            rp.close()
