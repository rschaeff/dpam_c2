import os, sys

fp = open('step3_redo_prots','r')
redo_prots = set([])
for line in fp:
    words = line.split()
    redo_prots.add(words[0])
fp.close()

hhsuite_dir = '/home/qcong/software/anaconda3/envs/hhsuite/bin/'
if not os.path.exists('step3'):
    os.system('mkdir step3/')
dataset = sys.argv[1]
if not os.path.exists('step3/' + dataset):
    os.system('mkdir step3/' + dataset)
joblimit = int(sys.argv[2])

for i in range(100):
    if os.path.exists('step3_' + dataset + '_' + str(i) + '.job'):
        os.system('rm step3_' + dataset + '_' + str(i) + '.job')
    if os.path.exists('step3_' + dataset + '_' + str(i) + '.cmds'):
        os.system('rm step3_' + dataset + '_' + str(i) + '.cmds')
    if os.path.exists('step3_' + dataset + '_' + str(i) + '.out'):
        os.system('rm step3_' + dataset + '_' + str(i) + '.out')

fp = open(dataset + '_cif.list', 'r')
prots = []
for line in fp:
    words = line.split()
    if words[0] in redo_prots:
        prots.append(words[0])
fp.close()

cmds = []
for prot in prots:
    if os.path.exists('step3/' + dataset + '/' + prot + '.hmm') and os.path.exists('step3/' + dataset + '/' + prot + '.hhsearch'):
        fp = open('step3/' + dataset + '/' + prot + '.hmm', 'r')
        get_sspred = 0
        get_ssconf = 0
        for line in fp:
            if len(line) >= 10:
                if line[0] == '>' and line[1:8] == 'ss_pred':
                    get_sspred = 1
                elif line[0] == '>' and line[1:8] == 'ss_conf':
                    get_ssconf = 1
            if get_sspred and get_ssconf:
                break
        fp.close()

        if get_sspred and get_ssconf:
            pass
        elif os.path.exists('step3/' + dataset + '/' + prot + '.a3m'):
            fp = open('step3/' + dataset + '/' + prot + '.a3m', 'r')
            count_line = 0
            for line in fp:
                count_line += 1
            fp.close()
            if count_line == 2:
                get_sspred = 1
                get_ssconf = 1

        fp = open('step3/' + dataset + '/' + prot + '.hhsearch', 'r')
        start = 0
        end = 0
        hitsA = set([])
        hitsB = set([])
        for line in fp:
            words = line.split()
            if len(words) >= 2:
                if words[0] == 'No' and words[1] == 'Hit':
                    start = 1
                elif words[0] == 'No' and words[1] == '1':
                    hitsB.add(int(words[1]))
                    end = 1
                elif start and not end:
                    hitsA.add(int(words[0]))
                elif end:
                    if words[0] == 'No':
                        hitsB.add(int(words[1]))
        fp.close()
        last_words = line.split()
        
        if get_sspred and get_ssconf and hitsA == hitsB and not last_words:
            pass
        else:
            os.system('rm step1/' + dataset + '/' + prot + '.hhr')
            os.system('rm step3/' + dataset + '/' + prot + '.a3m')
            os.system('rm step3/' + dataset + '/' + prot + '.hmm')
            os.system('rm step3/' + dataset + '/' + prot + '.hhsearch')
            cmds.append('python step3_run_hhsearch.py ' + dataset + ' ' + prot + ' 4 \n')
    else:
        if os.path.exists('step1/' + dataset + '/' + prot + '.hhr'):
            os.system('rm step1/' + dataset + '/' + prot + '.hhr')
        if os.path.exists('step3/' + dataset + '/' + prot + '.a3m'):
            os.system('rm step3/' + dataset + '/' + prot + '.a3m')
        if os.path.exists('step3/' + dataset + '/' + prot + '.hmm'):
            os.system('rm step3/' + dataset + '/' + prot + '.hmm')
        if os.path.exists('step3/' + dataset + '/' + prot + '.hhsearch'):
            os.system('rm step3/' + dataset + '/' + prot + '.hhsearch')
        cmds.append('python step3_run_hhsearch.py ' + dataset + ' ' + prot + ' 4 \n')

if cmds:
    jobnum = len(cmds) // 40 + 1
    if jobnum > joblimit:
        jobnum = joblimit
    batch_size = len(cmds) // jobnum + 1

    for i in range(jobnum):
        batch_cmds = cmds[i * batch_size: i * batch_size + batch_size]
        rp = open('step3_' + dataset + '_' + str(i) + '.cmds', 'w')
        for cmd in batch_cmds:
            rp.write(cmd)
        rp.close()

        rp = open('step3_' + dataset + '_' + str(i) + '.job', 'w')
        rp.write('#!/bin/bash\n')
        #rp.write('#SBATCH --exclude=compute-0-5\n')
        rp.write('#SBATCH --mem=250GB\n')
        rp.write('#SBATCH -p 256GB\n')
        rp.write('#SBATCH -N 1\n')
        rp.write('#SBATCH -n 32\n')
        rp.write('#SBATCH -o step3_' + dataset + '_' + str(i) + '.out\n\n')
        rp.write('export PERL5LIB=/home/jzhan6/software/hhsuite/scripts/\n')
        rp.write('export PATH=' + hhsuite_dir + ':$PATH\n')
        rp.write('rm -rf /scratch/*\n')
        rp.write('python copy_hhdb.py\n')
        rp.write('python batch_run.py step3_' + dataset + '_' + str(i) + '.cmds 8\n')
        rp.write('rm -rf /scratch/*\n')
        rp.close()
