import os, sys

dataset = sys.argv[1]

check0 = 0
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
        check0 = 1
        print ('There are ' + str(len(cif_cases)) + ' proteins to be classified from ' + dataset)
    else:
        print ('The number of cif (V4) files does not match the number of json (V4) files for ' + dataset + ', please check!')
else:
    print ('There is no directory for ' + dataset)



if check0:
    checkp = open(dataset + '_check', 'w')
    fp = open(dataset + '_cif.list', 'r')
    prots = []
    for line in fp:
        words = line.split()
        prots.append(words[0])
    fp.close()

    for count, prot in enumerate(prots):
        if count % 1000 == 0:
            print (count)
        check1 = 0
        if os.path.exists('step1/' + dataset + '/' + prot + '.fa'):
            fp = open('step1/' + dataset + '/' + prot + '.fa', 'r')
            check_header = 0
            check_seq = 0
            check_length = 0
            for line in fp:
                check_length += 1
                if line[0] == '>':
                    if line[1:-1] == prot:
                        check_header = 1
                else:
                    if len(line) > 10:
                        check_seq = 1
            fp.close()
            if check_header and check_seq and check_length == 2:
                check1 = 1


        check2 = 0
        fasta_length = 0
        if os.path.exists('step1/' + dataset + '/' + prot + '.fa'):
            fp = open('step1/' + dataset + '/' + prot + '.fa', 'r')
            for line in fp:
                if line[0] != '>':
                    fasta_length = len(line[:-1])
            fp.close()

        pdb_resids = set([])
        if os.path.exists('step2/' + dataset + '/' + prot + '.pdb'):
            fp = open('step2/' + dataset + '/' + prot + '.pdb', 'r')
            for line in fp:
                if len(line) >= 50:
                    if line[:4] == 'ATOM':
                        resid = int(line[22:26])
                        pdb_resids.add(resid)
            fp.close()
        pdb_length = len(pdb_resids)

        if fasta_length == pdb_length:
            if fasta_length:
                check2 = 1


        check3 = 0
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
                check3 = 1


        check4 = 0
        if os.path.exists('step4/' + dataset + '/' + prot + '.foldseek'):
            fp = open('step4/' + dataset + '/' + prot + '.foldseek','r')
            word_counts = set([])
            for line in fp:
                words = line.split()
                word_counts.add(len(words))
            fp.close()
            if len(word_counts) == 1 and 12 in word_counts:
                check4 = 1
            elif os.path.exists('step4/' + dataset + '/' + prot + '.done'):
                check4 = 1
        checkp.write(prot + '\t' + str(check1) + '\t' + str(check2) + '\t' + str(check3) + '\t' + str(check4) + '\n')
    checkp.close()
