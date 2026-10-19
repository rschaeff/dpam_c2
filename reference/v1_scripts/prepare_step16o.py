import os, sys

if not os.path.exists('step16'):
    os.system('mkdir step16/')
dataset = sys.argv[1]
if not os.path.exists('step16/' + dataset):
    os.system('mkdir step16/' + dataset)

if os.path.exists('step16_' + dataset + '.job'):
    os.system('rm step16_' + dataset + '.job')
if os.path.exists('step16_' + dataset + '.cmds'):
    os.system('rm step16_' + dataset + '.cmds')
if os.path.exists('step16_' + dataset + '.out'):
    os.system('rm step16_' + dataset + '.out')
if os.path.exists('step16_' + dataset + '.log'):
    os.system('rm step16_' + dataset + '.log')

fp = open(dataset + '_json.list', 'r')
prots = []
for line in fp:
    words = line.split()
    prots.append(words[0])
fp.close()

need_prots = []
for prot in prots:
    if os.path.exists('step16/' + dataset + '/' + prot + '.result'):
        word_counts = set([])
        fp = open('step16/' + dataset + '/' + prot + '.result', 'r')
        for line in fp:
            words = line.split()
            word_counts.add(len(words))
        fp.close()
        if len(word_counts) == 1 and 21 in word_counts:
            pass
        else:
            os.system('rm step16/' + dataset + '/' + prot + '.result')
            need_prots.append(prot)
    elif os.path.exists('step16/' + dataset + '/' + prot + '.done'):
        pass
    else:
        need_prots.append(prot)


if need_prots:
    batch_size = len(need_prots) // 8 + 1
    get_batches = []
    for i in range(8):
        batch_prots = need_prots[i * batch_size: i * batch_size + batch_size]
        if batch_prots:
            get_batches.append(i)
            rp = open('step16_' + dataset + '_' + str(i) + '.list', 'w')
            for prot in batch_prots:
                rp.write(prot + '\n')
            rp.close()

    fp = os.popen('squeue')
    T4_busy = 0
    RTX_busy = 0
    for line in fp:
        words = line.split()
        if words[1] == 'T4' and words[4] == 'R':
            T4_busy = 1
        if words[1] == 'RTX8000' and words[4] == 'R':
            RTX_busy = 1
    fp.close()
    
    rp = open('step16_' + dataset + '.job', 'w')
    rp.write('#!/bin/bash\n')
    #rp.write('#SBATCH --exclude=compute-0-5\n')
    rp.write('#SBATCH --mem=250GB\n')
    if not T4_busy:
        rp.write('#SBATCH -p T4\n')
    elif not RTX_busy:
        rp.write('#SBATCH -p RTX8000\n')
    else:
        rp.write('#SBATCH -p T4\n')

    rp.write('#SBATCH -N 1\n')
    rp.write('#SBATCH -n 32\n')
    rp.write('#SBATCH -o step16_' + dataset + '.out\n\n')
    rp.write('export PATH=/home/qcong/.local/usr/local/bin/:/home/jzhan6/software/hhsuite/bin:/home/jzhan6/software/hhsuite/scripts:/home/jzhan6/software/quickmerge:/home/jzhan6/software/mummer-4.0.0rc1:/home/jzhan6/alphafold:/home/jzhan6/alphafold/alphafold:/share/apps/cuda/10.2.89/bin:/home/jzhan6/structure_pipeline/structureHarvester:/home/jzhan6/software/ncbi-blast-2.11.0+/bin:/home/jzhan6/software/sratoolkit.2.11.0/bin:/home/jzhan6/software:/home/jzhan6/software/jre1.8.0_281/bin:/home/jzhan6/software/vim/bin:/home/qcong/software/anaconda3/bin:/home/jzhan6/perl5/lib/perl5:/home/jzhan6/structure_pipeline/CLUMPAK:/home/jzhan6/.local/bin:/home/jzhan6/bin:/home/jzhan6/software/NECAT/Linux-amd64/bin:/home/jzhan6/software/anaconda3/bin:/home/jzhan6/software/anaconda3/condabin:/home/jzhan6/perl5/bin:/opt/openmpi/bin:/usr/lib64/qt-3.3/bin:/usr/local/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/opt/dell/srvadmin/sbin:/opt/ganglia/bin:/opt/ganglia/sbin:/opt/pdsh/bin:/opt/rocks/bin:/opt/rocks/sbin:/opt/dell/srvadmin/sbin\n')
    rp.write('source activate dpamAI\n')
    rp.write('module add gcc/7.3.0 cuda/10.0.130 cudnn/7.4.2\n')
    for i in get_batches:
        rp.write('python step16_run_domass.py ' + dataset + ' ' + str(i) + ' &\n')
        rp.write('sleep 10\n')
    rp.write('wait\n')
    rp.write('rm step16_' + dataset + '_*.list\n')
    rp.close()
