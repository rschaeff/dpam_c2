import os, sys

fp = open('step8_redo_prots','r')
redo_prots = set([])
for line in fp:
    words = line.split()
    redo_prots.add(words[0])
fp.close()

if not os.path.exists('step8'):
    os.system('mkdir step8/')
dataset = sys.argv[1]
if not os.path.exists('step8/' + dataset):
    os.system('mkdir step8/' + dataset)

for i in range(10000):
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
for count, prot in enumerate(prots):
    if prot in redo_prots:
        if count % 1000 == 0:
            print (count)
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
    #jobnum = len(need_prots) // 5 + 1
    #batch_size = len(need_prots) // jobnum + 1
    jobnum = len(need_prots)
    batch_size = 1
    for i in range(jobnum):
        batch_prots = need_prots[i * batch_size: i * batch_size + batch_size]
        if batch_prots:
            rp = open('step8_' + dataset + '_' + str(i) + '.job', 'w')
            rp.write('#!/bin/bash\n')
            rp.write('#SBATCH --job-name=ccmpred\n')
            rp.write('#SBATCH --account=baker-ckpt\n')
            rp.write('#SBATCH --partition=ckpt\n')
            rp.write('#SBATCH --nodes=1\n')
            rp.write('#SBATCH --ntasks-per-node=28\n')
            rp.write('#SBATCH --time=4:00:00\n')
            rp.write('#SBATCH --mem=120G\n')
            rp.write('#SBATCH --chdir=/gscratch/scrubbed/congq/DPAM/\n\n')
            rp.write('rm -rf /tmp/*\n')
            rp.write('mkdir /tmp/ECOD_pdbs\n')
            for prot in batch_prots:
                rp.write('python step8_iterative_dali.py ' + dataset + ' ' + prot + '\n')
            rp.write('rm -rf /tmp/*\n')
            rp.close()
