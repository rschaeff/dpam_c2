import os, sys

dataset = sys.argv[1]
part = sys.argv[2]
foldseek_path = '/data/data1/conglab/qcong/for/domain_parser/model_organisms/foldseek/'

if not os.path.exists('/scratch/' + dataset + '_' + part + '_tmp'):
    os.system('mkdir /scratch/' + dataset + '_' + part + '_tmp')

fp = open('step4_' + dataset + '_' + part + '.list', 'r')
prots = []
for line in fp:
    words = line.split()
    prots.append(words[0])
fp.close()

for prot in prots:
    os.system(foldseek_path + 'bin/foldseek easy-search step2/' + dataset + '/' + prot + '.pdb /scratch/ECOD_foldseek_DB step4/' + dataset + '/' + prot + '.foldseek /scratch/' + dataset + '_' + part + '_tmp -e 1000 --max-seqs 1000000 >> /scratch/step4_' + dataset + '_' + part + '.log')
    fp = open('step4/' + dataset + '/' + prot + '.foldseek', 'r')
    countline = 0
    for line in fp:
        countline += 1
    fp.close()
    if not countline:
        os.system('echo \'done\' > step4/' + dataset + '/' + prot + '.done')
os.system('rm -rf /scratch/' + dataset + '_' + part + '_tmp')
os.system('mv /scratch/step4_' + dataset + '_' + part + '.log ./')
