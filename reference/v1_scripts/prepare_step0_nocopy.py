import os, sys

dataset = sys.argv[1]

os.system('ulimit -s 100000')
if os.path.exists(dataset + '/'):
    fp = os.popen('ls -1 ' + dataset + '/AF-*-F1-model_v4.cif')
    rp = open(dataset + '_cif.list', 'w')
    cif_cases = []
    for line in fp:
        words = line[:-1].split('/')
        accession = words[1].split('-')[1]
        version = words[1].split('.')[0].split('_')[-1]
        rp.write(accession + '\t' + version + '\n')
        cif_cases.append([accession, version])
    fp.close()
    rp.close()

    fp = os.popen('ls -1 ' + dataset + '/AF-*-F1-predicted_aligned_error_v4.json')
    rp = open(dataset + '_json.list', 'w')
    json_cases = []
    for line in fp:
        words = line[:-1].split('/')
        accession = words[1].split('-')[1]
        version = words[1].split('.')[0].split('_')[-1]
        rp.write(accession + '\t' + version + '\n')
        json_cases.append([accession, version])
    fp.close()
    rp.close()

    if len(cif_cases) == len(json_cases):
        print ('There are ' + str(len(cif_cases)) + ' proteins to be classified from ' + dataset)
    else:
        print ('The number of cif (V4) files does not match the number of json (V4) files for ' + dataset + ', please check!')
else:
    print ('There is no directory for ' + dataset)

