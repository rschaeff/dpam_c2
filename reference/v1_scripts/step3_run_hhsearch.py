import os, sys

dataset = sys.argv[1]
prot = sys.argv[2]
cpu = sys.argv[3]
hhsuite_path = '/home/qcong/software/anaconda3/envs/hhsuite/bin/' # should use mine, not yours.

if os.path.exists('step3/' + dataset + '/' + prot + '.hhsearch'):
    pass
else:
    if os.path.exists('/scratch/done'):
        if os.path.exists('step3/' + dataset + '/' + prot + '.hmm'):
            os.system(hhsuite_path + 'hhsearch -cpu ' + cpu + ' -Z 100000 -B 100000 -i step3/' + dataset + '/' + prot + '.hmm -d /scratch/pdb70/pdb70 -o step3/' + dataset + '/' + prot + '.hhsearch')
        elif os.path.exists('step3/' + dataset + '/' + prot + '.hhm'):
            os.system('mv step3/' + dataset + '/' + prot + '.hhm step3/' + dataset + '/' + prot + '.hmm')
            os.system(hhsuite_path + 'hhsearch -cpu ' + cpu + ' -Z 100000 -B 100000 -i step3/' + dataset + '/' + prot + '.hmm -d /scratch/pdb70/pdb70 -o step3/' + dataset + '/' + prot + '.hhsearch')
        else:
            os.system(hhsuite_path + 'hhblits -cpu ' + cpu + ' -i step1/' + dataset + '/' + prot + '.fa -d /scratch/UniRef30_2022_02/UniRef30_2022_02 -oa3m step3/' + dataset + '/' + prot + '.a3m')
            os.system(hhsuite_path + 'addss.pl step3/' + dataset + '/' + prot + '.a3m step3/' + dataset + '/' + prot + '.a3m.ss -a3m')
            os.system('mv step3/' + dataset + '/' + prot + '.a3m.ss step3/' + dataset + '/' + prot + '.a3m')
            os.system(hhsuite_path + 'hhmake -i step3/' + dataset + '/' + prot + '.a3m -o step3/' + dataset + '/' + prot + '.hmm')
            os.system(hhsuite_path + 'hhsearch -cpu ' + cpu + ' -Z 100000 -B 100000 -i step3/' + dataset + '/' + prot + '.hmm -d /scratch/pdb70/pdb70 -o step3/' + dataset + '/' + prot + '.hhsearch')
    else:
        if os.path.exists('step3/' + dataset + '/' + prot + '.hmm'):
            os.system(hhsuite_path + 'hhsearch -cpu ' + cpu + ' -Z 100000 -B 100000 -i step3/' + dataset + '/' + prot + '.hmm -d /data/data1/conglab/qcong/for/domain_parser/model_organisms/pdb70/pdb70 -o step3/' + dataset + '/' + prot + '.hhsearch')
        elif os.path.exists('step3/' + dataset + '/' + prot + '.hhm'):
            os.system('mv step3/' + dataset + '/' + prot + '.hhm step3/' + dataset + '/' + prot + '.hmm')
            os.system(hhsuite_path + 'hhsearch -cpu ' + cpu + ' -Z 100000 -B 100000 -i step3/' + dataset + '/' + prot + '.hmm -d /data/data1/conglab/qcong/for/domain_parser/model_organisms/pdb70/pdb70 -o step3/' + dataset + '/' + prot + '.hhsearch')
        else:
            os.system(hhsuite_path + 'hhblits -cpu ' + cpu + ' -i step1/' + dataset + '/' + prot + '.fa -d /data/data1/conglab/jzhan6/databases/UniRef30_2022_02/UniRef30_2022_02 -oa3m step3/' + dataset + '/' + prot + '.a3m')
            os.system(hhsuite_path + 'addss.pl step3/' + dataset + '/' + prot + '.a3m step3/' + dataset + '/' + prot + '.a3m.ss -a3m')
            os.system('mv step3/' + dataset + '/' + prot + '.a3m.ss step3/' + dataset + '/' + prot + '.a3m')
            os.system(hhsuite_path + 'hhmake -i step3/' + dataset + '/' + prot + '.a3m -o step3/' + dataset + '/' + prot + '.hmm')
            os.system(hhsuite_path + 'hhsearch -cpu ' + cpu + ' -Z 100000 -B 100000 -i step3/' + dataset + '/' + prot + '.hmm -d /data/data1/conglab/qcong/for/domain_parser/model_organisms/pdb70/pdb70 -o step3/' + dataset + '/' + prot + '.hhsearch')
