import os, sys

fp = os.popen('df /scratch')
size = 0
for countl, line in enumerate(fp):
    if countl:
        words = line.split()
        size = int(words[3])
        break
fp.close()

if size >= 350000000:
    os.system('cp -r /data/data1/conglab/jzhan6/databases/UniRef30_2022_02/ /scratch/')
    os.system('cp -r /data/data1/conglab/qcong/for/domain_parser/model_organisms/pdb70/ /scratch/')
    os.system('echo \'done\' > /scratch/done')
